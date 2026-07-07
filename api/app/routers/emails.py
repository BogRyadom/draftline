"""Read access to synced emails, plus on-demand (re)classification."""

from __future__ import annotations

import datetime as dt
import logging
import uuid
from typing import Literal

from fastapi import APIRouter, Depends, HTTPException, Query, status
from fastapi.concurrency import run_in_threadpool
from pydantic import BaseModel
from sqlalchemy import case, select
from sqlalchemy.ext.asyncio import AsyncSession

from app import llm
from app.audit import log_action
from app.auth import CurrentUser, get_current_user
from app.classification import classify_one, fetch_unbadged_ids, get_user_categories
from app.db import get_session
from app.knowledge import retrieve
from app.llm import LLMError
from app.models import Draft, Email, Settings
from app.schemas import DraftOut, EmailDetail

router = APIRouter(prefix="/emails", tags=["emails"])

logger = logging.getLogger("draftline.emails")

_DEFAULT_TONE = {"formality": "neutral", "length": "concise", "signature": ""}


async def _user_tone(session: AsyncSession, user_id: uuid.UUID) -> dict:
    tone = (
        await session.execute(select(Settings.tone).where(Settings.user_id == user_id))
    ).scalar_one_or_none()
    return tone if isinstance(tone, dict) and tone else _DEFAULT_TONE

# Ordering rank for priority sort (urgent first).
_PRIORITY_RANK = case(
    (Email.priority == "urgent", 0),
    (Email.priority == "high", 1),
    (Email.priority == "normal", 2),
    (Email.priority == "low", 3),
    else_=4,
)


class EmailOut(BaseModel):
    id: uuid.UUID
    account_id: uuid.UUID
    from_name: str | None
    from_email: str | None
    subject: str | None
    snippet: str | None
    received_at: dt.datetime | None
    category: str | None
    priority: str | None
    classification_reason: str | None
    status: str
    created_at: dt.datetime


@router.get("", response_model=list[EmailOut])
async def list_emails(
    user: CurrentUser = Depends(get_current_user),
    session: AsyncSession = Depends(get_session),
    limit: int = Query(default=50, ge=1, le=200),
    category: str | None = Query(default=None),
    priority: str | None = Query(default=None),
    status_: str | None = Query(default=None, alias="status"),
    sort: Literal["received", "priority"] = Query(default="received"),
) -> list[Email]:
    """List the user's emails with optional filters and sort."""
    stmt = select(Email).where(Email.user_id == uuid.UUID(user.id))
    if category:
        stmt = stmt.where(Email.category == category)
    if priority:
        stmt = stmt.where(Email.priority == priority)
    if status_:
        stmt = stmt.where(Email.status == status_)

    if sort == "priority":
        stmt = stmt.order_by(_PRIORITY_RANK, Email.received_at.desc().nullslast())
    else:
        stmt = stmt.order_by(
            Email.received_at.desc().nullslast(), Email.created_at.desc()
        )

    rows = await session.execute(stmt.limit(limit))
    return list(rows.scalars().all())


class BulkClassifyResult(BaseModel):
    total: int
    classified: int
    failed: int


@router.post("/classify-unbadged", response_model=BulkClassifyResult)
async def classify_unbadged(
    user: CurrentUser = Depends(get_current_user),
    session: AsyncSession = Depends(get_session),
    limit: int = Query(default=100, ge=1, le=500),
) -> BulkClassifyResult:
    """Reliable fallback: classify every still-unbadged email now, synchronously,
    returning counts. Each email commits on its own; failures are logged and skipped."""
    user_uuid = uuid.UUID(user.id)
    categories = await get_user_categories(session, user_uuid)
    ids = await fetch_unbadged_ids(session, user_uuid, limit)

    classified = 0
    failed = 0
    for email_id in ids:
        email = (
            await session.execute(
                select(Email).where(Email.id == email_id, Email.user_id == user_uuid)
            )
        ).scalar_one_or_none()
        if email is None:
            continue
        try:
            await classify_one(session, email, categories)
            await session.commit()
            classified += 1
        except Exception:
            await session.rollback()
            failed += 1
            logger.exception("bulk classify failed for email %s", email_id)

    logger.info(
        "bulk classify: %d classified, %d failed of %d", classified, failed, len(ids)
    )
    return BulkClassifyResult(total=len(ids), classified=classified, failed=failed)


@router.post("/{email_id}/classify", response_model=EmailOut)
async def classify_email(
    email_id: uuid.UUID,
    user: CurrentUser = Depends(get_current_user),
    session: AsyncSession = Depends(get_session),
) -> Email:
    """(Re)classify a single email now and return the updated record."""
    user_uuid = uuid.UUID(user.id)
    email = (
        await session.execute(
            select(Email).where(Email.id == email_id, Email.user_id == user_uuid)
        )
    ).scalar_one_or_none()
    if email is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Email not found.")

    categories = await get_user_categories(session, user_uuid)
    try:
        await classify_one(session, email, categories)
    except LLMError as exc:
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail="Classification failed. Please try again.",
        ) from exc

    await session.commit()
    await session.refresh(email)
    return email


async def _latest_draft(session: AsyncSession, email_id: uuid.UUID, user_id: uuid.UUID) -> Draft | None:
    return (
        await session.execute(
            select(Draft)
            .where(Draft.email_id == email_id, Draft.user_id == user_id)
            .order_by(Draft.created_at.desc())
            .limit(1)
        )
    ).scalar_one_or_none()


@router.get("/{email_id}", response_model=EmailDetail)
async def get_email(
    email_id: uuid.UUID,
    user: CurrentUser = Depends(get_current_user),
    session: AsyncSession = Depends(get_session),
) -> EmailDetail:
    """Full email (with body) plus its latest draft, for the review surface."""
    user_uuid = uuid.UUID(user.id)
    email = (
        await session.execute(
            select(Email).where(Email.id == email_id, Email.user_id == user_uuid)
        )
    ).scalar_one_or_none()
    if email is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Email not found.")

    draft = await _latest_draft(session, email_id, user_uuid)
    detail = EmailDetail.model_validate(email)
    detail.draft = DraftOut.model_validate(draft) if draft is not None else None
    return detail


@router.post("/{email_id}/draft", response_model=DraftOut)
async def generate_draft(
    email_id: uuid.UUID,
    user: CurrentUser = Depends(get_current_user),
    session: AsyncSession = Depends(get_session),
) -> Draft:
    """Generate a grounded reply draft: retrieve KB context, call the 70B model,
    persist as `pending`. Never sends — the draft is saved in-app for review."""
    user_uuid = uuid.UUID(user.id)
    email = (
        await session.execute(
            select(Email).where(Email.id == email_id, Email.user_id == user_uuid)
        )
    ).scalar_one_or_none()
    if email is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Email not found.")

    query = " ".join(
        part for part in (email.subject, email.body_text or email.snippet) if part
    ).strip()[:2000]
    chunks = await retrieve(session, user_uuid, query, k=5) if query else []
    tone = await _user_tone(session, user_uuid)

    source = {
        "from_name": email.from_name,
        "from_email": email.from_email,
        "subject": email.subject,
        "body_text": email.body_text,
        "snippet": email.snippet,
    }
    try:
        result = await run_in_threadpool(
            llm.draft,
            source_email=source,
            chunks=chunks,
            tone=tone,
            language=email.language,
        )
    except LLMError as exc:
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail="Draft generation failed. Please try again.",
        ) from exc

    # Signature is applied in code (not by the model): strip any model sign-off,
    # then append the configured signature so it never doubles up.
    body = llm.apply_signature(result.body, tone.get("signature", ""))

    draft = Draft(
        user_id=user_uuid,
        email_id=email.id,
        body=body,
        model=result.model,
        prompt_tokens=result.prompt_tokens,
        completion_tokens=result.completion_tokens,
        citations=[c.model_dump() for c in result.citations],
        confidence=result.confidence,
        status="pending",
    )
    session.add(draft)
    email.status = "drafted"
    await session.flush()

    await log_action(
        session,
        user_id=user_uuid,
        action="draft_generated",
        entity_type="draft",
        entity_id=draft.id,
        metadata={
            "email_id": str(email.id),
            "confidence": result.confidence,
            "citations": len(result.citations),
        },
    )
    await session.commit()
    await session.refresh(draft)
    return draft
