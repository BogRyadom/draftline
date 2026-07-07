"""Shared API response schemas for drafts and email detail."""

from __future__ import annotations

import datetime as dt
import uuid

from pydantic import BaseModel, ConfigDict


class CitationOut(BaseModel):
    document_id: str | None = None
    filename: str | None = None
    chunk_index: int | None = None
    quote: str


class DraftOut(BaseModel):
    # `model` shadows pydantic's protected namespace; allow it.
    model_config = ConfigDict(from_attributes=True, protected_namespaces=())

    id: uuid.UUID
    email_id: uuid.UUID
    body: str | None
    model: str | None
    prompt_tokens: int | None
    completion_tokens: int | None
    citations: list[CitationOut]
    confidence: str | None
    status: str
    created_at: dt.datetime
    updated_at: dt.datetime


class EmailDetail(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    account_id: uuid.UUID
    from_name: str | None
    from_email: str | None
    subject: str | None
    snippet: str | None
    body_text: str | None
    received_at: dt.datetime | None
    category: str | None
    priority: str | None
    classification_reason: str | None
    status: str
    created_at: dt.datetime
    draft: DraftOut | None = None
