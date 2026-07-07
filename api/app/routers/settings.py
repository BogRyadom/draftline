"""User settings: read and edit categories, tone/signature, and poll flags.

Falls back to defaults when the user has no settings row yet; the write path
upserts a single row keyed by user_id.
"""

from __future__ import annotations

import uuid
from typing import Literal

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, Field, field_validator
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.auth import CurrentUser, get_current_user
from app.classification import DEFAULT_CATEGORIES
from app.db import get_session
from app.models import Settings

router = APIRouter(prefix="/settings", tags=["settings"])

DEFAULT_TONE = {"formality": "neutral", "length": "concise", "signature": ""}

MAX_CATEGORIES = 20
MAX_CATEGORY_LEN = 40
MAX_SIGNATURE_LEN = 500


class Tone(BaseModel):
    formality: Literal["casual", "neutral", "formal"] = "neutral"
    length: Literal["brief", "concise", "detailed"] = "concise"
    signature: str = Field(default="", max_length=MAX_SIGNATURE_LEN)


class SettingsOut(BaseModel):
    categories: list[str]
    tone: dict
    poll_enabled: bool
    poll_interval_minutes: int
    auto_push_drafts: bool


class SettingsIn(BaseModel):
    categories: list[str]
    tone: Tone
    poll_enabled: bool = False
    poll_interval_minutes: int = Field(default=15, ge=5, le=1440)
    auto_push_drafts: bool = False

    @field_validator("categories")
    @classmethod
    def _clean_categories(cls, value: list[str]) -> list[str]:
        """Trim, drop blanks, dedupe (case-insensitive), and bound the list."""
        seen: set[str] = set()
        cleaned: list[str] = []
        for raw in value:
            name = raw.strip()[:MAX_CATEGORY_LEN]
            key = name.lower()
            if name and key not in seen:
                seen.add(key)
                cleaned.append(name)
        if not cleaned:
            raise ValueError("At least one category is required.")
        if len(cleaned) > MAX_CATEGORIES:
            raise ValueError(f"At most {MAX_CATEGORIES} categories are allowed.")
        return cleaned


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


@router.put("", response_model=SettingsOut)
async def update_settings(
    payload: SettingsIn,
    user: CurrentUser = Depends(get_current_user),
    session: AsyncSession = Depends(get_session),
) -> SettingsOut:
    """Upsert the user's settings and return the saved values."""
    user_uuid = uuid.UUID(user.id)
    row = (
        await session.execute(select(Settings).where(Settings.user_id == user_uuid))
    ).scalar_one_or_none()

    tone = payload.tone.model_dump()
    if row is None:
        row = Settings(user_id=user_uuid)
        session.add(row)

    row.categories = payload.categories
    row.tone = tone
    row.poll_enabled = payload.poll_enabled
    row.poll_interval_minutes = payload.poll_interval_minutes
    row.auto_push_drafts = payload.auto_push_drafts

    try:
        await session.commit()
    except Exception as exc:  # unique/constraint or connection issue
        await session.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Could not save settings. Please try again.",
        ) from exc

    return SettingsOut(
        categories=payload.categories,
        tone=tone,
        poll_enabled=payload.poll_enabled,
        poll_interval_minutes=payload.poll_interval_minutes,
        auto_push_drafts=payload.auto_push_drafts,
    )
