"""Gmail OAuth + API helpers.

The OAuth exchange happens server-side so the refresh token never reaches the
browser. These functions are blocking (Google's client libraries are sync); call
them from async routes via `run_in_threadpool`.
"""

from __future__ import annotations

import os

# Google occasionally returns scopes in a different order or adds `openid`;
# relax oauthlib's strict scope-equality check so token exchange doesn't fail.
os.environ.setdefault("OAUTHLIB_RELAX_TOKEN_SCOPE", "1")

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
    flow = Flow.from_client_config(_client_config(), scopes=SCOPES, state=state)
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
