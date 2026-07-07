"""Audit log read access. The audit trail is a product feature (§3), surfaced
as a filterable page — connect, sync, classify, draft, save, dismiss, upload."""

from __future__ import annotations

import datetime as dt
import uuid

from fastapi import APIRouter, Depends, Query
from pydantic import BaseModel
from sqlalchemy import distinct, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.auth import CurrentUser, get_current_user
from app.db import get_session
from app.models import AuditLog

router = APIRouter(prefix="/audit", tags=["audit"])


class AuditEntry(BaseModel):
    id: uuid.UUID
    action: str
    entity_type: str | None
    entity_id: uuid.UUID | None
    metadata: dict
    created_at: dt.datetime


@router.get("/actions", response_model=list[str])
async def list_actions(
    user: CurrentUser = Depends(get_current_user),
    session: AsyncSession = Depends(get_session),
) -> list[str]:
    """Distinct actions present in the user's log, for the filter control."""
    rows = await session.execute(
        select(distinct(AuditLog.action))
        .where(AuditLog.user_id == uuid.UUID(user.id))
        .order_by(AuditLog.action)
    )
    return list(rows.scalars().all())


@router.get("", response_model=list[AuditEntry])
async def list_audit(
    user: CurrentUser = Depends(get_current_user),
    session: AsyncSession = Depends(get_session),
    action: str | None = Query(default=None),
    limit: int = Query(default=50, ge=1, le=200),
    offset: int = Query(default=0, ge=0),
) -> list[AuditEntry]:
    """The user's audit trail, newest first, optionally filtered by action."""
    stmt = select(AuditLog).where(AuditLog.user_id == uuid.UUID(user.id))
    if action:
        stmt = stmt.where(AuditLog.action == action)
    stmt = stmt.order_by(AuditLog.created_at.desc()).limit(limit).offset(offset)

    rows = (await session.execute(stmt)).scalars().all()
    return [
        AuditEntry(
            id=row.id,
            action=row.action,
            entity_type=row.entity_type,
            entity_id=row.entity_id,
            metadata=row.metadata_ or {},
            created_at=row.created_at,
        )
        for row in rows
    ]
