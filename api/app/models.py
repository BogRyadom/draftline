"""SQLAlchemy models mirroring the Supabase schema (§3).

Only the tables used so far are defined; the rest are added in their phases.
Server-side defaults (uuid, timestamps) match the migration, so inserts can omit
them and read them back via RETURNING.
"""

from __future__ import annotations

import datetime as dt
import uuid

from sqlalchemy import Boolean, ForeignKey, Integer, String, Text, text
from sqlalchemy.dialects.postgresql import JSONB, TIMESTAMP, UUID
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column

from app.vectortype import Vector

EMBEDDING_DIM = 768


class Base(DeclarativeBase):
    pass


def _uuid_pk() -> Mapped[uuid.UUID]:
    return mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        server_default=text("gen_random_uuid()"),
    )


class EmailAccount(Base):
    __tablename__ = "email_accounts"

    id: Mapped[uuid.UUID] = _uuid_pk()
    user_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), nullable=False)
    provider: Mapped[str] = mapped_column(String, nullable=False)
    email_address: Mapped[str] = mapped_column(String, nullable=False)
    oauth_refresh_token_enc: Mapped[str | None] = mapped_column(Text)
    status: Mapped[str] = mapped_column(String, nullable=False, server_default=text("'connected'"))
    last_synced_at: Mapped[dt.datetime | None] = mapped_column(TIMESTAMP(timezone=True))
    created_at: Mapped[dt.datetime] = mapped_column(
        TIMESTAMP(timezone=True), server_default=text("now()")
    )


class Email(Base):
    __tablename__ = "emails"

    id: Mapped[uuid.UUID] = _uuid_pk()
    user_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), nullable=False)
    account_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("email_accounts.id", ondelete="CASCADE"), nullable=False
    )
    provider_message_id: Mapped[str] = mapped_column(String, nullable=False)
    thread_id: Mapped[str | None] = mapped_column(String)
    from_name: Mapped[str | None] = mapped_column(String)
    from_email: Mapped[str | None] = mapped_column(String)
    subject: Mapped[str | None] = mapped_column(Text)
    snippet: Mapped[str | None] = mapped_column(Text)
    body_text: Mapped[str | None] = mapped_column(Text)
    received_at: Mapped[dt.datetime | None] = mapped_column(TIMESTAMP(timezone=True))
    category: Mapped[str | None] = mapped_column(String)
    priority: Mapped[str | None] = mapped_column(String)
    classification_reason: Mapped[str | None] = mapped_column(Text)
    # Human-readable language the email is written in (e.g. "English", "Russian").
    language: Mapped[str | None] = mapped_column(String)
    status: Mapped[str] = mapped_column(String, nullable=False, server_default=text("'new'"))
    created_at: Mapped[dt.datetime] = mapped_column(
        TIMESTAMP(timezone=True), server_default=text("now()")
    )


class Draft(Base):
    __tablename__ = "drafts"

    id: Mapped[uuid.UUID] = _uuid_pk()
    user_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), nullable=False)
    email_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("emails.id", ondelete="CASCADE"), nullable=False
    )
    body: Mapped[str | None] = mapped_column(Text)
    model: Mapped[str | None] = mapped_column(String)
    prompt_tokens: Mapped[int | None] = mapped_column(Integer)
    completion_tokens: Mapped[int | None] = mapped_column(Integer)
    citations: Mapped[list] = mapped_column(
        JSONB, nullable=False, server_default=text("'[]'::jsonb")
    )
    confidence: Mapped[str | None] = mapped_column(String)
    status: Mapped[str] = mapped_column(String, nullable=False, server_default=text("'pending'"))
    created_at: Mapped[dt.datetime] = mapped_column(
        TIMESTAMP(timezone=True), server_default=text("now()")
    )
    updated_at: Mapped[dt.datetime] = mapped_column(
        TIMESTAMP(timezone=True), server_default=text("now()")
    )


class Document(Base):
    __tablename__ = "documents"

    id: Mapped[uuid.UUID] = _uuid_pk()
    user_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), nullable=False)
    filename: Mapped[str] = mapped_column(String, nullable=False)
    mime_type: Mapped[str | None] = mapped_column(String)
    status: Mapped[str] = mapped_column(String, nullable=False, server_default=text("'processing'"))
    chunk_count: Mapped[int] = mapped_column(Integer, nullable=False, server_default=text("0"))
    created_at: Mapped[dt.datetime] = mapped_column(
        TIMESTAMP(timezone=True), server_default=text("now()")
    )


class DocumentChunk(Base):
    __tablename__ = "document_chunks"

    id: Mapped[uuid.UUID] = _uuid_pk()
    document_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("documents.id", ondelete="CASCADE"), nullable=False
    )
    user_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), nullable=False)
    content: Mapped[str] = mapped_column(Text, nullable=False)
    embedding: Mapped[list[float]] = mapped_column(Vector(EMBEDDING_DIM))
    chunk_index: Mapped[int] = mapped_column(Integer, nullable=False)
    metadata_: Mapped[dict] = mapped_column(
        "metadata", JSONB, nullable=False, server_default=text("'{}'::jsonb")
    )


class Settings(Base):
    __tablename__ = "settings"

    user_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True)
    categories: Mapped[list] = mapped_column(JSONB, nullable=False)
    tone: Mapped[dict] = mapped_column(JSONB, nullable=False)
    poll_enabled: Mapped[bool] = mapped_column(Boolean, nullable=False, server_default=text("false"))
    poll_interval_minutes: Mapped[int] = mapped_column(Integer, nullable=False, server_default=text("15"))
    auto_push_drafts: Mapped[bool] = mapped_column(Boolean, nullable=False, server_default=text("false"))


class AuditLog(Base):
    __tablename__ = "audit_logs"

    id: Mapped[uuid.UUID] = _uuid_pk()
    user_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), nullable=False)
    action: Mapped[str] = mapped_column(String, nullable=False)
    entity_type: Mapped[str | None] = mapped_column(String)
    entity_id: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True))
    metadata_: Mapped[dict] = mapped_column(
        "metadata", JSONB, nullable=False, server_default=text("'{}'::jsonb")
    )
    created_at: Mapped[dt.datetime] = mapped_column(
        TIMESTAMP(timezone=True), server_default=text("now()")
    )
