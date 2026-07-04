"""Classification service: applies llm.classify to emails and records the result.

Runs as a background task after sync (and on-demand for re-classify). Each email
is committed on its own so partial progress survives a failure mid-batch, and
calls are gently spaced to respect Groq's free-tier rate limit.
"""

from __future__ import annotations

import asyncio
import logging
import uuid

from fastapi.concurrency import run_in_threadpool
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app import llm
from app.audit import log_action
from app.db import get_sessionmaker
from app.models import Email, Settings

logger = logging.getLogger("draftline.classification")

DEFAULT_CATEGORIES = ["Sales", "Support", "Billing", "Personal", "Other"]

# Gentle spacing between model calls (Groq free tier ~30 req/min).
_INTER_CALL_DELAY_SECONDS = 0.3


async def get_user_categories(session: AsyncSession, user_id: uuid.UUID) -> list[str]:
    """The user's configured categories, or sensible defaults."""
    row = (
        await session.execute(
            select(Settings.categories).where(Settings.user_id == user_id)
        )
    ).scalar_one_or_none()
    if isinstance(row, list) and row:
        return [str(c) for c in row]
    return DEFAULT_CATEGORIES


async def classify_one(
    session: AsyncSession, email: Email, categories: list[str]
) -> llm.Classification:
    """Classify a single email and stage the update + audit entry (no commit)."""
    result = await run_in_threadpool(
        llm.classify,
        subject=email.subject,
        from_email=email.from_email,
        snippet=email.snippet,
        body_text=email.body_text,
        categories=categories,
    )
    email.category = result.category
    email.priority = result.priority
    email.classification_reason = result.reason
    email.status = "classified"

    await log_action(
        session,
        user_id=email.user_id,
        action="email_classified",
        entity_type="email",
        entity_id=email.id,
        metadata={"category": result.category, "priority": result.priority},
    )
    return result


async def fetch_unbadged_ids(
    session: AsyncSession, user_id: uuid.UUID, limit: int
) -> list[uuid.UUID]:
    """IDs of the user's emails that have no category yet."""
    rows = await session.execute(
        select(Email.id)
        .where(Email.user_id == user_id, Email.category.is_(None))
        .order_by(Email.received_at.desc().nullslast())
        .limit(limit)
    )
    return list(rows.scalars().all())


async def classify_email_ids(user_id: uuid.UUID, email_ids: list[uuid.UUID]) -> None:
    """Background task: classify each email in its OWN session so one failure
    (DB or model) can never abort the batch. Logs every item for visibility."""
    if not email_ids:
        logger.info("classify batch: nothing to do for user %s", user_id)
        return

    logger.info("classify batch start: %d email(s) for user %s", len(email_ids), user_id)

    # Fetch categories once (its own short-lived session).
    async with get_sessionmaker()() as session:
        categories = await get_user_categories(session, user_id)

    ok = 0
    failed = 0
    for email_id in email_ids:
        try:
            async with get_sessionmaker()() as session:
                email = (
                    await session.execute(
                        select(Email).where(
                            Email.id == email_id, Email.user_id == user_id
                        )
                    )
                ).scalar_one_or_none()
                if email is None:
                    logger.warning("classify skip: email %s not found", email_id)
                    continue
                result = await classify_one(session, email, categories)
                await session.commit()
            ok += 1
            logger.info(
                "classify ok: %s -> %s / %s", email_id, result.category, result.priority
            )
        except Exception as exc:
            failed += 1
            logger.exception("classify FAIL: %s: %r", email_id, exc)
        await asyncio.sleep(_INTER_CALL_DELAY_SECONDS)

    logger.info(
        "classify batch done: %d ok, %d failed of %d", ok, failed, len(email_ids)
    )
