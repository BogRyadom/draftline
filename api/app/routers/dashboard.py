"""Dashboard stats: aggregate counts and recent activity from real data.

Read-only overview for the app landing — email/draft/document counts, a
category and priority breakdown, and the tail of the audit log.
"""

from __future__ import annotations

import datetime as dt
import uuid

from fastapi import APIRouter, Depends, Query
from pydantic import BaseModel
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.auth import CurrentUser, get_current_user
from app.db import get_session
from app.models import AuditLog, Document, Draft, Email

router = APIRouter(prefix="/dashboard", tags=["dashboard"])

# Drafts still awaiting the user's decision (not yet saved or dismissed).
_PENDING_DRAFT_STATUSES = ("pending", "edited")


class CountItem(BaseModel):
    label: str
    count: int


class ActivityItem(BaseModel):
    action: str
    entity_type: str | None
    entity_id: uuid.UUID | None
    metadata: dict
    created_at: dt.datetime


class DashboardStats(BaseModel):
    emails_total: int
    emails_classified: int
    emails_unclassified: int
    by_category: list[CountItem]
    by_priority: list[CountItem]
    drafts_pending: int
    drafts_saved: int
    drafts_dismissed: int
    documents_total: int
    documents_ready: int
    recent_activity: list[ActivityItem]


async def _group_counts(session: AsyncSession, column, where) -> list[CountItem]:
    """Count non-null values of `column` for the user, most frequent first."""
    rows = await session.execute(
        select(column, func.count())
        .where(where, column.is_not(None))
        .group_by(column)
        .order_by(func.count().desc())
    )
    return [CountItem(label=str(label), count=count) for label, count in rows.all()]


@router.get("/stats", response_model=DashboardStats)
async def read_stats(
    user: CurrentUser = Depends(get_current_user),
    session: AsyncSession = Depends(get_session),
    activity_limit: int = Query(default=8, ge=1, le=50),
) -> DashboardStats:
    """Return aggregate counts plus the most recent audit-log activity."""
    user_uuid = uuid.UUID(user.id)
    email_owned = Email.user_id == user_uuid

    emails_total = (
        await session.execute(select(func.count()).select_from(Email).where(email_owned))
    ).scalar_one()
    emails_classified = (
        await session.execute(
            select(func.count())
            .select_from(Email)
            .where(email_owned, Email.category.is_not(None))
        )
    ).scalar_one()

    by_category = await _group_counts(session, Email.category, email_owned)
    by_priority = await _group_counts(session, Email.priority, email_owned)

    # One grouped pass over drafts, then fold statuses into the buckets we show.
    draft_rows = (
        await session.execute(
            select(Draft.status, func.count())
            .where(Draft.user_id == user_uuid)
            .group_by(Draft.status)
        )
    ).all()
    draft_counts = {status: count for status, count in draft_rows}
    drafts_pending = sum(draft_counts.get(s, 0) for s in _PENDING_DRAFT_STATUSES)

    documents_total = (
        await session.execute(
            select(func.count()).select_from(Document).where(Document.user_id == user_uuid)
        )
    ).scalar_one()
    documents_ready = (
        await session.execute(
            select(func.count())
            .select_from(Document)
            .where(Document.user_id == user_uuid, Document.status == "ready")
        )
    ).scalar_one()

    activity_rows = (
        await session.execute(
            select(AuditLog)
            .where(AuditLog.user_id == user_uuid)
            .order_by(AuditLog.created_at.desc())
            .limit(activity_limit)
        )
    ).scalars().all()
    recent_activity = [
        ActivityItem(
            action=row.action,
            entity_type=row.entity_type,
            entity_id=row.entity_id,
            metadata=row.metadata_ or {},
            created_at=row.created_at,
        )
        for row in activity_rows
    ]

    return DashboardStats(
        emails_total=emails_total,
        emails_classified=emails_classified,
        emails_unclassified=emails_total - emails_classified,
        by_category=by_category,
        by_priority=by_priority,
        drafts_pending=drafts_pending,
        drafts_saved=draft_counts.get("saved_to_gmail", 0),
        drafts_dismissed=draft_counts.get("dismissed", 0),
        documents_total=documents_total,
        documents_ready=documents_ready,
        recent_activity=recent_activity,
    )
