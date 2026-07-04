"""Read access to synced emails."""

from __future__ import annotations

import datetime as dt
import uuid

from fastapi import APIRouter, Depends, Query
from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.auth import CurrentUser, get_current_user
from app.db import get_session
from app.models import Email

router = APIRouter(prefix="/emails", tags=["emails"])


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
    status: str
    created_at: dt.datetime


@router.get("", response_model=list[EmailOut])
async def list_emails(
    user: CurrentUser = Depends(get_current_user),
    session: AsyncSession = Depends(get_session),
    limit: int = Query(default=50, ge=1, le=200),
) -> list[Email]:
    """List the current user's emails, newest first."""
    rows = await session.execute(
        select(Email)
        .where(Email.user_id == uuid.UUID(user.id))
        .order_by(Email.received_at.desc().nullslast(), Email.created_at.desc())
        .limit(limit)
    )
    return list(rows.scalars().all())
