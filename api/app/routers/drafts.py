"""Draft review actions: edit, Save to Gmail, Dismiss.

Human-in-the-loop: a draft is only ever written to the Gmail *Drafts* folder on
explicit user action. There is no endpoint that sends email.
"""

from __future__ import annotations

import uuid

from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.concurrency import run_in_threadpool
from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app import gmail
from app.audit import log_action
from app.auth import CurrentUser, get_current_user
from app.crypto import get_cipher
from app.db import get_session
from app.models import Draft, Email, EmailAccount
from app.schemas import DraftOut

router = APIRouter(prefix="/drafts", tags=["drafts"])


class DraftUpdate(BaseModel):
    body: str


async def _get_draft(session: AsyncSession, draft_id: uuid.UUID, user_id: uuid.UUID) -> Draft:
    draft = (
        await session.execute(
            select(Draft).where(Draft.id == draft_id, Draft.user_id == user_id)
        )
    ).scalar_one_or_none()
    if draft is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Draft not found.")
    return draft


@router.get("/{draft_id}", response_model=DraftOut)
async def get_draft(
    draft_id: uuid.UUID,
    user: CurrentUser = Depends(get_current_user),
    session: AsyncSession = Depends(get_session),
) -> Draft:
    return await _get_draft(session, draft_id, uuid.UUID(user.id))


@router.patch("/{draft_id}", response_model=DraftOut)
async def edit_draft(
    draft_id: uuid.UUID,
    payload: DraftUpdate,
    user: CurrentUser = Depends(get_current_user),
    session: AsyncSession = Depends(get_session),
) -> Draft:
    """Save an in-app edit. Marks the draft `edited`."""
    user_uuid = uuid.UUID(user.id)
    draft = await _get_draft(session, draft_id, user_uuid)
    draft.body = payload.body
    draft.status = "edited"
    await log_action(
        session, user_id=user_uuid, action="draft_edited",
        entity_type="draft", entity_id=draft.id,
    )
    await session.commit()
    await session.refresh(draft)
    return draft


@router.post("/{draft_id}/dismiss", response_model=DraftOut)
async def dismiss_draft(
    draft_id: uuid.UUID,
    user: CurrentUser = Depends(get_current_user),
    session: AsyncSession = Depends(get_session),
) -> Draft:
    """Dismiss a draft. Nothing is written anywhere."""
    user_uuid = uuid.UUID(user.id)
    draft = await _get_draft(session, draft_id, user_uuid)
    draft.status = "dismissed"
    await log_action(
        session, user_id=user_uuid, action="draft_dismissed",
        entity_type="draft", entity_id=draft.id,
    )
    await session.commit()
    await session.refresh(draft)
    return draft


@router.post("/{draft_id}/save-to-gmail", response_model=DraftOut)
async def save_to_gmail(
    draft_id: uuid.UUID,
    user: CurrentUser = Depends(get_current_user),
    session: AsyncSession = Depends(get_session),
) -> Draft:
    """Write the draft to the real Gmail Drafts folder (drafts.create). No send."""
    user_uuid = uuid.UUID(user.id)
    draft = await _get_draft(session, draft_id, user_uuid)
    if not (draft.body or "").strip():
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Draft is empty.")

    email = (
        await session.execute(
            select(Email).where(Email.id == draft.email_id, Email.user_id == user_uuid)
        )
    ).scalar_one_or_none()
    if email is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Source email not found.")

    account = (
        await session.execute(
            select(EmailAccount).where(
                EmailAccount.id == email.account_id, EmailAccount.user_id == user_uuid
            )
        )
    ).scalar_one_or_none()
    if account is None or not account.oauth_refresh_token_enc:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="The email account is not connected.",
        )

    subject = email.subject or ""
    if not subject.lower().startswith("re:"):
        subject = f"Re: {subject}".strip()

    refresh_token = get_cipher().decrypt(account.oauth_refresh_token_enc)
    try:
        gmail_draft_id = await run_in_threadpool(
            gmail.create_draft,
            refresh_token,
            to=email.from_email or "",
            subject=subject,
            body=draft.body,
            thread_id=email.thread_id,
        )
    except Exception as exc:
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail="Could not save to Gmail. Please try again.",
        ) from exc

    draft.status = "saved_to_gmail"
    await log_action(
        session, user_id=user_uuid, action="draft_saved_to_gmail",
        entity_type="draft", entity_id=draft.id,
        metadata={"gmail_draft_id": gmail_draft_id},
    )
    await session.commit()
    await session.refresh(draft)
    return draft
