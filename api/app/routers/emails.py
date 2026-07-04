"""Read access to synced emails, plus on-demand (re)classification."""

from __future__ import annotations

import datetime as dt
import uuid
from typing import Literal

from fastapi import APIRouter, Depends, HTTPException, Query, status
from pydantic import BaseModel
from sqlalchemy import case, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.auth import CurrentUser, get_current_user
from app.classification import classify_one, get_user_categories
from app.db import get_session
from app.llm import LLMError
from app.models import Email

router = APIRouter(prefix="/emails", tags=["emails"])

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
