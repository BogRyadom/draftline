"""Gmail message parsing tests (no network)."""

import base64
import datetime as dt

from app.gmail import parse_message


def _b64url(text: str) -> str:
    return base64.urlsafe_b64encode(text.encode()).decode()


def test_parses_multipart_plain_text():
    message = {
        "id": "msg-1",
        "threadId": "thread-1",
        "snippet": "Hi there, quick question",
        "internalDate": "1700000000000",  # ms epoch
        "payload": {
            "mimeType": "multipart/alternative",
            "headers": [
                {"name": "From", "value": "Ada Lovelace <ada@example.com>"},
                {"name": "Subject", "value": "Quick question"},
            ],
            "parts": [
                {"mimeType": "text/plain", "body": {"data": _b64url("Hello in plain text")}},
                {"mimeType": "text/html", "body": {"data": _b64url("<p>Hello in HTML</p>")}},
            ],
        },
    }

    parsed = parse_message(message)

    assert parsed["provider_message_id"] == "msg-1"
    assert parsed["thread_id"] == "thread-1"
    assert parsed["from_name"] == "Ada Lovelace"
    assert parsed["from_email"] == "ada@example.com"
    assert parsed["subject"] == "Quick question"
    assert parsed["snippet"] == "Hi there, quick question"
    assert parsed["body_text"] == "Hello in plain text"
    assert parsed["received_at"] == dt.datetime(2023, 11, 14, 22, 13, 20, tzinfo=dt.timezone.utc)


def test_falls_back_to_stripped_html():
    message = {
        "id": "msg-2",
        "threadId": "thread-2",
        "snippet": "html only",
        "payload": {
            "mimeType": "text/html",
            "headers": [{"name": "From", "value": "noreply@shop.example"}],
            "body": {"data": _b64url("<h1>Sale</h1><p>50% <b>off</b></p>")},
        },
    }

    parsed = parse_message(message)

    assert parsed["from_name"] is None
    assert parsed["from_email"] == "noreply@shop.example"
    assert parsed["subject"] is None
    assert parsed["body_text"] == "Sale 50% off"
    assert parsed["received_at"] is None
