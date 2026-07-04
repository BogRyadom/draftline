"""Read access to user settings (categories, tone, poll flags).

Phase 2 needs the category list for filtering; editing arrives in Phase 5.
Falls back to defaults when the user has no settings row yet.
"""

from __future__ import annotations

import uuid

from fastapi import APIRouter, Depends
from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.auth import CurrentUser, get_current_user
from app.classification import DEFAULT_CATEGORIES
from app.db import get_session
from app.models import Settings

router = APIRouter(prefix="/settings", tags=["settings"])

DEFAULT_TONE = {"formality": "neutral", "length": "concise", "signature": ""}


class SettingsOut(BaseModel):
    categories: list[str]
    tone: dict
    poll_enabled: bool
    poll_interval_minutes: int
    auto_push_drafts: bool


@router.get("", response_model=SettingsOut)
async def read_settings(
    user: CurrentUser = Depends(get_current_user),
    session: AsyncSession = Depends(get_session),
) -> SettingsOut:
    """Return the user's effective settings, using defaults where unset."""
    row = (
        await session.execute(
            select(Settings).where(Settings.user_id == uuid.UUID(user.id))
        )
    ).scalar_one_or_none()

    if row is None:
        return SettingsOut(
            categories=DEFAULT_CATEGORIES,
            tone=DEFAULT_TONE,
            poll_enabled=False,
            poll_interval_minutes=15,
            auto_push_drafts=False,
        )

    return SettingsOut(
        categories=[str(c) for c in row.categories] if row.categories else DEFAULT_CATEGORIES,
        tone=row.tone or DEFAULT_TONE,
        poll_enabled=row.poll_enabled,
        poll_interval_minutes=row.poll_interval_minutes,
        auto_push_drafts=row.auto_push_drafts,
    )
