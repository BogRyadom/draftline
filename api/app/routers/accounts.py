"""Email account connection (Gmail OAuth) and listing."""

from __future__ import annotations

import datetime as dt
import uuid

from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.concurrency import run_in_threadpool
from fastapi.responses import RedirectResponse
from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app import gmail
from app.audit import log_action
from app.auth import CurrentUser, get_current_user
from app.config import get_settings
from app.crypto import get_cipher
from app.db import get_session
from app.models import Email, EmailAccount
from app.oauth_state import StateError, create_state, verify_state

router = APIRouter(prefix="/accounts", tags=["accounts"])


class AccountOut(BaseModel):
    id: uuid.UUID
    provider: str
    email_address: str
    status: str
    last_synced_at: dt.datetime | None
    created_at: dt.datetime


class SyncResult(BaseModel):
    account_id: uuid.UUID
    fetched: int
    new: int


def _frontend_origin() -> str:
    origins = get_settings().cors_origins
    return origins[0] if origins else "http://localhost:3000"


def _require_google_config() -> None:
    s = get_settings()
    if not (s.google_client_id and s.google_client_secret and s.google_oauth_redirect_uri):
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Gmail OAuth is not configured on the server.",
        )


@router.get("", response_model=list[AccountOut])
async def list_accounts(
    user: CurrentUser = Depends(get_current_user),
    session: AsyncSession = Depends(get_session),
) -> list[EmailAccount]:
    """List the current user's connected email accounts."""
    rows = await session.execute(
        select(EmailAccount)
        .where(EmailAccount.user_id == uuid.UUID(user.id))
        .order_by(EmailAccount.created_at)
    )
    return list(rows.scalars().all())


@router.post("/gmail/connect")
async def connect_gmail(
    user: CurrentUser = Depends(get_current_user),
) -> dict[str, str]:
    """Start the Gmail OAuth flow; returns the Google consent URL to visit."""
    _require_google_config()
    state = create_state(user.id)
    return {"authorization_url": gmail.build_authorization_url(state)}


@router.get("/gmail/callback")
async def gmail_callback(
    code: str | None = None,
    state: str | None = None,
    error: str | None = None,
    session: AsyncSession = Depends(get_session),
) -> RedirectResponse:
    """Google redirects here after consent. Exchange, store, and return to the app."""
    app_url = f"{_frontend_origin()}/app"

    if error or not code or not state:
        return RedirectResponse(f"{app_url}?gmail=error")

    try:
        user_id = uuid.UUID(verify_state(state))
    except (StateError, ValueError):
        return RedirectResponse(f"{app_url}?gmail=error")

    try:
        result = await run_in_threadpool(gmail.exchange_code, code)
    except Exception:
        return RedirectResponse(f"{app_url}?gmail=error")

    refresh_token = result.get("refresh_token")
    email_address = result.get("email")
    if not refresh_token or not email_address:
        # A refresh token is only returned on first consent; prompt=consent forces it.
        return RedirectResponse(f"{app_url}?gmail=error&reason=norefresh")

    encrypted = get_cipher().encrypt(refresh_token)

    existing = (
        await session.execute(
            select(EmailAccount).where(
                EmailAccount.user_id == user_id,
                EmailAccount.provider == "gmail",
                EmailAccount.email_address == email_address,
            )
        )
    ).scalar_one_or_none()

    if existing:
        existing.oauth_refresh_token_enc = encrypted
        existing.status = "connected"
        account_id = existing.id
    else:
        account = EmailAccount(
            user_id=user_id,
            provider="gmail",
            email_address=email_address,
            oauth_refresh_token_enc=encrypted,
            status="connected",
        )
        session.add(account)
        await session.flush()
        account_id = account.id

    await log_action(
        session,
        user_id=user_id,
        action="account_connected",
        entity_type="email_account",
        entity_id=account_id,
        metadata={"email": email_address},
    )
    await session.commit()

    return RedirectResponse(f"{app_url}?gmail=connected")


@router.post("/{account_id}/sync", response_model=SyncResult)
async def sync_account(
    account_id: uuid.UUID,
    user: CurrentUser = Depends(get_current_user),
    session: AsyncSession = Depends(get_session),
) -> SyncResult:
    """Pull the latest unread mail for an account into `emails` (dedup by message id)."""
    user_uuid = uuid.UUID(user.id)
    account = (
        await session.execute(
            select(EmailAccount).where(
                EmailAccount.id == account_id,
                EmailAccount.user_id == user_uuid,
            )
        )
    ).scalar_one_or_none()

    if account is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Account not found.")
    if not account.oauth_refresh_token_enc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Account has no stored token.")

    refresh_token = get_cipher().decrypt(account.oauth_refresh_token_enc)

    try:
        messages = await run_in_threadpool(
            gmail.fetch_unread, refresh_token, get_settings().sync_max_results
        )
    except Exception:
        account.status = "error"
        await session.commit()
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY, detail="Gmail sync failed."
        )

    existing_ids = set(
        (
            await session.execute(
                select(Email.provider_message_id).where(Email.account_id == account.id)
            )
        )
        .scalars()
        .all()
    )

    new_count = 0
    for msg in messages:
        if msg["provider_message_id"] in existing_ids:
            continue
        session.add(
            Email(user_id=user_uuid, account_id=account.id, status="new", **msg)
        )
        new_count += 1

    account.last_synced_at = dt.datetime.now(dt.timezone.utc)
    account.status = "connected"

    await log_action(
        session,
        user_id=user_uuid,
        action="sync_run",
        entity_type="email_account",
        entity_id=account.id,
        metadata={"fetched": len(messages), "new": new_count},
    )
    await session.commit()

    return SyncResult(account_id=account.id, fetched=len(messages), new=new_count)
