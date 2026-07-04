"""Signed, time-limited OAuth `state` values.

Google's redirect to our callback is a top-level browser navigation that carries
no Draftline JWT. To recover *which* user started the flow (and to block CSRF),
we sign a small state payload (user id + nonce + issued-at) with HMAC-SHA256 and
verify it on the way back. No server-side storage required.
"""

from __future__ import annotations

import base64
import hmac
import json
import secrets
import time
from hashlib import sha256

from app.config import get_settings

STATE_TTL_SECONDS = 600


class StateError(Exception):
    """Raised when an OAuth state value is malformed, forged, or expired."""


def _secret() -> bytes:
    key = get_settings().fernet_key
    if not key:
        raise RuntimeError("FERNET_KEY is required to sign OAuth state.")
    return key.encode()


def _b64(raw: bytes) -> str:
    return base64.urlsafe_b64encode(raw).decode().rstrip("=")


def _unb64(data: str) -> bytes:
    return base64.urlsafe_b64decode(data + "=" * (-len(data) % 4))


def _sign(payload_b64: str, secret: bytes) -> str:
    return _b64(hmac.new(secret, payload_b64.encode(), sha256).digest())


def create_state(user_id: str, *, secret: bytes | None = None) -> str:
    """Return a signed state string encoding the user id."""
    secret = secret or _secret()
    payload = {"uid": user_id, "iat": int(time.time()), "nonce": secrets.token_urlsafe(8)}
    payload_b64 = _b64(json.dumps(payload, separators=(",", ":")).encode())
    return f"{payload_b64}.{_sign(payload_b64, secret)}"


def verify_state(
    state: str, *, secret: bytes | None = None, max_age: int = STATE_TTL_SECONDS
) -> str:
    """Verify a state string and return the encoded user id, or raise StateError."""
    secret = secret or _secret()
    try:
        payload_b64, signature = state.rsplit(".", 1)
    except ValueError as exc:
        raise StateError("malformed state") from exc

    if not hmac.compare_digest(signature, _sign(payload_b64, secret)):
        raise StateError("bad signature")

    try:
        payload = json.loads(_unb64(payload_b64))
    except (ValueError, json.JSONDecodeError) as exc:
        raise StateError("bad payload") from exc

    if time.time() - float(payload.get("iat", 0)) > max_age:
        raise StateError("expired state")

    uid = payload.get("uid")
    if not uid:
        raise StateError("missing user id")
    return uid
