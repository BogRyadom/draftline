"""Signed OAuth state tests."""

import time

import pytest

from app.oauth_state import StateError, create_state, verify_state

SECRET = b"test-secret-key-for-hmac"


def test_round_trip_returns_user_id():
    state = create_state("user-123", secret=SECRET)
    assert verify_state(state, secret=SECRET) == "user-123"


def test_rejects_tampered_payload():
    state = create_state("user-123", secret=SECRET)
    payload, sig = state.rsplit(".", 1)
    forged = f"{payload}x.{sig}"
    with pytest.raises(StateError):
        verify_state(forged, secret=SECRET)


def test_rejects_wrong_secret():
    state = create_state("user-123", secret=SECRET)
    with pytest.raises(StateError):
        verify_state(state, secret=b"a-different-secret")


def test_rejects_expired_state():
    state = create_state("user-123", secret=SECRET)
    time.sleep(0.05)
    with pytest.raises(StateError):
        verify_state(state, secret=SECRET, max_age=0)


def test_rejects_malformed_state():
    with pytest.raises(StateError):
        verify_state("not-a-valid-state", secret=SECRET)
