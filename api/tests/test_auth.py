"""JWT verification tests (§7).

Generates an RSA keypair, signs tokens locally, and exercises both the pure
`verify_access_token` function and the `/me` endpoint end to end. A fake JWKS
client feeds the endpoint our public key so no network access is needed.
"""

from __future__ import annotations

import datetime as dt
import uuid

import jwt
import pytest
from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.primitives.asymmetric import rsa
from fastapi.testclient import TestClient

import app.auth as auth_module
from app.auth import verify_access_token
from app.main import app

AUDIENCE = "authenticated"


@pytest.fixture(scope="module")
def keypair() -> tuple[bytes, bytes]:
    """Return (private_pem, public_pem) for signing and verifying test tokens."""
    private_key = rsa.generate_private_key(public_exponent=65537, key_size=2048)
    private_pem = private_key.private_bytes(
        encoding=serialization.Encoding.PEM,
        format=serialization.PrivateFormat.PKCS8,
        encryption_algorithm=serialization.NoEncryption(),
    )
    public_pem = private_key.public_key().public_bytes(
        encoding=serialization.Encoding.PEM,
        format=serialization.PublicFormat.SubjectPublicKeyInfo,
    )
    return private_pem, public_pem


def make_token(
    private_pem: bytes,
    *,
    sub: str | None = "given",
    aud: str = AUDIENCE,
    email: str | None = "user@example.com",
    exp_delta: int = 3600,
) -> str:
    """Sign a Supabase-shaped access token (RS256)."""
    now = dt.datetime.now(dt.timezone.utc)
    payload: dict = {
        "aud": aud,
        "iat": now,
        "exp": now + dt.timedelta(seconds=exp_delta),
    }
    if sub is not None:
        payload["sub"] = str(uuid.uuid4()) if sub == "given" else sub
    if email is not None:
        payload["email"] = email
    return jwt.encode(payload, private_pem, algorithm="RS256")


# ── Pure verification ──────────────────────────────────────────────────────


def test_accepts_valid_token(keypair):
    private_pem, public_pem = keypair
    user_id = str(uuid.uuid4())
    token = make_token(private_pem, sub=user_id, email="a@b.com")

    user = verify_access_token(token, public_pem, AUDIENCE)

    assert user.id == user_id
    assert user.email == "a@b.com"


def test_rejects_tampered_signature(keypair):
    private_pem, public_pem = keypair
    token = make_token(private_pem)
    tampered = token[:-3] + ("aaa" if token[-3:] != "aaa" else "bbb")

    with pytest.raises(jwt.InvalidSignatureError):
        verify_access_token(tampered, public_pem, AUDIENCE)


def test_rejects_expired_token(keypair):
    private_pem, public_pem = keypair
    token = make_token(private_pem, exp_delta=-10)

    with pytest.raises(jwt.ExpiredSignatureError):
        verify_access_token(token, public_pem, AUDIENCE)


def test_rejects_wrong_audience(keypair):
    private_pem, public_pem = keypair
    token = make_token(private_pem, aud="some-other-service")

    with pytest.raises(jwt.InvalidAudienceError):
        verify_access_token(token, public_pem, AUDIENCE)


def test_rejects_missing_subject(keypair):
    private_pem, public_pem = keypair
    token = make_token(private_pem, sub=None)

    with pytest.raises(jwt.MissingRequiredClaimError):
        verify_access_token(token, public_pem, AUDIENCE)


def test_rejects_token_signed_by_other_key(keypair):
    _, public_pem = keypair
    other_key = rsa.generate_private_key(public_exponent=65537, key_size=2048)
    other_pem = other_key.private_bytes(
        encoding=serialization.Encoding.PEM,
        format=serialization.PrivateFormat.PKCS8,
        encryption_algorithm=serialization.NoEncryption(),
    )
    token = make_token(other_pem)

    with pytest.raises(jwt.InvalidSignatureError):
        verify_access_token(token, public_pem, AUDIENCE)


# ── Endpoint integration (/me, /health) ────────────────────────────────────


class _FakeSigningKey:
    def __init__(self, key: bytes) -> None:
        self.key = key


class _FakeJWKClient:
    """Stands in for PyJWKClient, returning a fixed public key."""

    def __init__(self, public_pem: bytes) -> None:
        self._public_pem = public_pem

    def get_signing_key_from_jwt(self, token: str) -> _FakeSigningKey:
        return _FakeSigningKey(self._public_pem)


@pytest.fixture
def client(keypair, monkeypatch) -> TestClient:
    _, public_pem = keypair
    monkeypatch.setattr(auth_module, "get_jwk_client", lambda: _FakeJWKClient(public_pem))
    return TestClient(app)


def test_health_is_open(client):
    resp = client.get("/health")
    assert resp.status_code == 200
    assert resp.json() == {"status": "ok"}


def test_me_returns_user_with_valid_token(client, keypair):
    private_pem, _ = keypair
    user_id = str(uuid.uuid4())
    token = make_token(private_pem, sub=user_id, email="me@example.com")

    resp = client.get("/me", headers={"Authorization": f"Bearer {token}"})

    assert resp.status_code == 200
    assert resp.json() == {"id": user_id, "email": "me@example.com"}


def test_me_rejects_missing_token(client):
    resp = client.get("/me")
    assert resp.status_code == 401


def test_me_rejects_invalid_token(client):
    resp = client.get("/me", headers={"Authorization": "Bearer not.a.jwt"})
    assert resp.status_code == 401
