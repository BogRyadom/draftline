"""Gmail OAuth + API helpers.

The OAuth exchange happens server-side so the refresh token never reaches the
browser. These functions are blocking (Google's client libraries are sync); call
them from async routes via `run_in_threadpool`.
"""

from __future__ import annotations

import base64
import datetime as dt
import html as html_lib
import os
import re
from email.utils import parseaddr

# Google occasionally returns scopes in a different order or adds `openid`;
# relax oauthlib's strict scope-equality check so token exchange doesn't fail.
os.environ.setdefault("OAUTHLIB_RELAX_TOKEN_SCOPE", "1")

from google.auth.transport.requests import Request as GoogleAuthRequest  # noqa: E402
from google.oauth2.credentials import Credentials  # noqa: E402
from google_auth_oauthlib.flow import Flow  # noqa: E402
from googleapiclient.discovery import build  # noqa: E402

from app.config import get_settings  # noqa: E402

SCOPES = [
    "https://www.googleapis.com/auth/gmail.readonly",
    "https://www.googleapis.com/auth/gmail.compose",
]

AUTH_URI = "https://accounts.google.com/o/oauth2/auth"
TOKEN_URI = "https://oauth2.googleapis.com/token"


def _client_config() -> dict:
    s = get_settings()
    return {
        "web": {
            "client_id": s.google_client_id,
            "client_secret": s.google_client_secret,
            "auth_uri": AUTH_URI,
            "token_uri": TOKEN_URI,
            "redirect_uris": [s.google_oauth_redirect_uri],
        }
    }


def _flow(state: str | None = None) -> Flow:
    # Disable PKCE: we are a confidential client (client_secret protects the
    # exchange), and connect/callback are separate stateless requests, so there
    # is nowhere to carry a per-request code_verifier. Both flows must agree —
    # keeping this in the single helper guarantees no code_challenge is sent at
    # connect and no verifier is expected at callback.
    flow = Flow.from_client_config(
        _client_config(),
        scopes=SCOPES,
        state=state,
        autogenerate_code_verifier=False,
    )
    flow.redirect_uri = get_settings().google_oauth_redirect_uri
    return flow


def build_authorization_url(state: str) -> str:
    """Build the Google consent URL. `access_type=offline` + `prompt=consent`
    ensures a refresh token is returned."""
    url, _ = _flow(state=state).authorization_url(
        access_type="offline",
        include_granted_scopes="true",
        prompt="consent",
    )
    return url


def exchange_code(code: str) -> dict:
    """Blocking: exchange the auth code for tokens and read the account email."""
    flow = _flow()
    flow.fetch_token(code=code)
    creds = flow.credentials
    return {
        "refresh_token": creds.refresh_token,
        "access_token": creds.token,
        "email": _profile_email(creds),
    }


def _profile_email(creds: Credentials) -> str:
    service = build("gmail", "v1", credentials=creds, cache_discovery=False)
    profile = service.users().getProfile(userId="me").execute()
    return profile["emailAddress"]


def credentials_from_refresh_token(refresh_token: str) -> Credentials:
    """Build credentials that can mint fresh access tokens for sync."""
    s = get_settings()
    return Credentials(
        token=None,
        refresh_token=refresh_token,
        token_uri=TOKEN_URI,
        client_id=s.google_client_id,
        client_secret=s.google_client_secret,
        scopes=SCOPES,
    )


# ── Reading mail ────────────────────────────────────────────────────────────


def fetch_unread(refresh_token: str, max_results: int) -> list[dict]:
    """Blocking: pull up to `max_results` unread messages, fully parsed."""
    creds = credentials_from_refresh_token(refresh_token)
    creds.refresh(GoogleAuthRequest())
    service = build("gmail", "v1", credentials=creds, cache_discovery=False)

    listing = (
        service.users()
        .messages()
        .list(userId="me", q="is:unread", maxResults=max_results)
        .execute()
    )

    parsed: list[dict] = []
    for ref in listing.get("messages", []):
        full = (
            service.users()
            .messages()
            .get(userId="me", id=ref["id"], format="full")
            .execute()
        )
        parsed.append(parse_message(full))
    return parsed


def _header(headers: list[dict], name: str) -> str | None:
    for h in headers:
        if h.get("name", "").lower() == name.lower():
            return h.get("value")
    return None


def _decode_b64url(data: str) -> str:
    return base64.urlsafe_b64decode(data.encode("utf-8")).decode("utf-8", errors="replace")


def _strip_html(html: str) -> str:
    text = re.sub(r"(?is)<(script|style).*?>.*?</\1>", " ", html)
    text = re.sub(r"(?s)<[^>]+>", " ", text)
    return html_lib.unescape(re.sub(r"[ \t\r\f\v]+", " ", text)).strip()


def _extract_body(payload: dict) -> str:
    """Prefer text/plain; fall back to (stripped) text/html. Recurses parts."""
    mime = payload.get("mimeType", "")
    body = payload.get("body", {})

    if mime == "text/plain" and body.get("data"):
        return _decode_b64url(body["data"])

    for part in payload.get("parts", []) or []:
        if part.get("mimeType") == "text/plain" and part.get("body", {}).get("data"):
            return _decode_b64url(part["body"]["data"])

    for part in payload.get("parts", []) or []:
        text = _extract_body(part)
        if text:
            return text

    if mime == "text/html" and body.get("data"):
        return _strip_html(_decode_b64url(body["data"]))
    return ""


def parse_message(full: dict) -> dict:
    """Map a Gmail `messages.get` (format=full) result to our email columns."""
    payload = full.get("payload", {})
    headers = payload.get("headers", [])
    from_name, from_email = parseaddr(_header(headers, "From") or "")

    received_at: dt.datetime | None = None
    internal = full.get("internalDate")
    if internal:
        received_at = dt.datetime.fromtimestamp(int(internal) / 1000, tz=dt.timezone.utc)

    body_text = _extract_body(payload)

    return {
        "provider_message_id": full["id"],
        "thread_id": full.get("threadId"),
        "from_name": from_name or None,
        "from_email": from_email or None,
        "subject": _header(headers, "Subject"),
        "snippet": full.get("snippet"),
        "body_text": body_text or None,
        "received_at": received_at,
    }
