"""Supabase JWT authentication.

Supabase Auth issues the access token on the frontend. Here we verify it against
the project's public JWKS (asymmetric ES256/RS256 signing keys) and derive the
current user. Postgres RLS enforces per-user isolation as a second layer.

`verify_access_token` is kept pure (no network, key passed in) so the crypto is
unit-testable; `get_current_user` is the FastAPI dependency that resolves the
signing key from the live JWKS endpoint and wraps it.
"""

from __future__ import annotations

import jwt
from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from jwt import PyJWKClient
from jwt.exceptions import PyJWKClientError
from pydantic import BaseModel

from app.config import get_settings

# Supabase signs with ECC (ES256) by default for asymmetric keys; RS256 is the
# other supported asymmetric algorithm. HS256 is intentionally excluded — we
# never verify with a shared secret here.
ALGORITHMS = ["ES256", "RS256"]


class CurrentUser(BaseModel):
    """The authenticated identity derived from a verified access token."""

    id: str
    email: str | None = None


def verify_access_token(token: str, signing_key: object, audience: str) -> CurrentUser:
    """Verify signature + standard claims and return the trusted identity.

    Pure function: the public `signing_key` is supplied by the caller, so this
    can be exercised in tests without touching the network. Raises the relevant
    `jwt` exception on any failure (bad signature, expired, wrong audience, …).
    """
    payload = jwt.decode(
        token,
        signing_key,
        algorithms=ALGORITHMS,
        audience=audience,
        options={"require": ["exp", "sub"]},
    )
    return CurrentUser(id=payload["sub"], email=payload.get("email"))


_jwk_client: PyJWKClient | None = None


def get_jwk_client() -> PyJWKClient:
    """Return a lazily-created, caching JWKS client for the Supabase project."""
    global _jwk_client
    if _jwk_client is None:
        url = get_settings().resolved_jwks_url
        if not url:
            raise RuntimeError(
                "SUPABASE_URL or SUPABASE_JWKS_URL must be set to verify tokens."
            )
        # PyJWKClient caches fetched keys and refetches on unknown `kid`.
        _jwk_client = PyJWKClient(url)
    return _jwk_client


_bearer = HTTPBearer(auto_error=False)


async def get_current_user(
    credentials: HTTPAuthorizationCredentials | None = Depends(_bearer),
) -> CurrentUser:
    """FastAPI dependency: require and verify a Supabase bearer token."""
    if credentials is None or not credentials.credentials:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Missing bearer token",
            headers={"WWW-Authenticate": "Bearer"},
        )

    token = credentials.credentials
    try:
        signing_key = get_jwk_client().get_signing_key_from_jwt(token).key
        return verify_access_token(token, signing_key, get_settings().jwt_audience)
    except (jwt.PyJWTError, PyJWKClientError) as exc:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or expired token",
            headers={"WWW-Authenticate": "Bearer"},
        ) from exc
