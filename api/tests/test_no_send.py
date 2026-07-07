"""Guardrails: Draftline must never send email (§1, §7)."""

import inspect

import app.gmail as gmail_module
from app.gmail import SCOPES
from app.main import app


def test_no_send_route_exists():
    for path, operations in app.openapi()["paths"].items():
        assert "send" not in path.lower(), f"unexpected send-like route: {path}"
        for method, op in operations.items():
            assert "send" not in (op.get("operationId", "")).lower(), (
                f"unexpected send-like operation on {method} {path}"
            )


def test_gmail_scopes_are_read_and_compose_only():
    assert set(SCOPES) == {
        "https://www.googleapis.com/auth/gmail.readonly",
        "https://www.googleapis.com/auth/gmail.compose",
    }
    assert not any("gmail.send" in scope for scope in SCOPES)


def test_gmail_module_makes_no_send_call():
    source = inspect.getsource(gmail_module)
    assert "messages().send" not in source
    assert ".send(" not in source
