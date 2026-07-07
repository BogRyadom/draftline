"""Knowledge base: upload, list, delete documents, and search chunks."""

from __future__ import annotations

import datetime as dt
import uuid

from fastapi import (
    APIRouter,
    BackgroundTasks,
    Depends,
    File,
    HTTPException,
    Query,
    UploadFile,
    status,
)
from fastapi.responses import Response
from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.audit import log_action
from app.auth import CurrentUser, get_current_user
from app.db import get_session
from app.extract import SUPPORTED_MIME_TYPES
from app.knowledge import process_document, retrieve
from app.models import Document

router = APIRouter(prefix="/documents", tags=["documents"])

_MAX_UPLOAD_BYTES = 10 * 1024 * 1024  # 10 MB


class DocumentOut(BaseModel):
    id: uuid.UUID
    filename: str
    mime_type: str | None
    status: str
    chunk_count: int
    created_at: dt.datetime


class RetrievedChunk(BaseModel):
    document_id: str
    filename: str | None
    chunk_index: int
    content: str
    similarity: float


def _is_supported(filename: str, mime_type: str | None) -> bool:
    if mime_type in SUPPORTED_MIME_TYPES:
        return True
    return filename.lower().endswith((".pdf", ".docx"))


@router.get("", response_model=list[DocumentOut])
async def list_documents(
    user: CurrentUser = Depends(get_current_user),
    session: AsyncSession = Depends(get_session),
) -> list[Document]:
    """List the user's knowledge-base documents, newest first."""
    rows = await session.execute(
        select(Document)
        .where(Document.user_id == uuid.UUID(user.id))
        .order_by(Document.created_at.desc())
    )
    return list(rows.scalars().all())


@router.get("/search", response_model=list[RetrievedChunk])
async def search_documents(
    q: str = Query(..., min_length=1),
    k: int = Query(default=5, ge=1, le=20),
    user: CurrentUser = Depends(get_current_user),
    session: AsyncSession = Depends(get_session),
) -> list[dict]:
    """Cosine-similarity search over the user's document chunks."""
    return await retrieve(session, uuid.UUID(user.id), q, k)


@router.post("", response_model=DocumentOut, status_code=status.HTTP_201_CREATED)
async def upload_document(
    background: BackgroundTasks,
    file: UploadFile = File(...),
    user: CurrentUser = Depends(get_current_user),
    session: AsyncSession = Depends(get_session),
) -> Document:
    """Upload a PDF/DOCX; processing (extract → chunk → embed) runs in the background."""
    filename = file.filename or "document"
    if not _is_supported(filename, file.content_type):
        raise HTTPException(
            status_code=status.HTTP_415_UNSUPPORTED_MEDIA_TYPE,
            detail="Only PDF and DOCX files are supported.",
        )

    data = await file.read()
    if len(data) == 0:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Empty file.")
    if len(data) > _MAX_UPLOAD_BYTES:
        raise HTTPException(
            status_code=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE,
            detail="File exceeds the 10 MB limit.",
        )

    user_uuid = uuid.UUID(user.id)
    doc = Document(
        user_id=user_uuid,
        filename=filename,
        mime_type=file.content_type,
        status="processing",
        chunk_count=0,
    )
    session.add(doc)
    await session.flush()
    document_id = doc.id
    await session.commit()
    await session.refresh(doc)

    background.add_task(
        process_document, document_id, user_uuid, data, filename, file.content_type
    )
    return doc


@router.delete("/{document_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_document(
    document_id: uuid.UUID,
    user: CurrentUser = Depends(get_current_user),
    session: AsyncSession = Depends(get_session),
) -> Response:
    """Delete a document and its chunks (FK cascade)."""
    user_uuid = uuid.UUID(user.id)
    doc = (
        await session.execute(
            select(Document).where(
                Document.id == document_id, Document.user_id == user_uuid
            )
        )
    ).scalar_one_or_none()
    if doc is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Document not found.")

    filename = doc.filename
    await session.delete(doc)
    await log_action(
        session,
        user_id=user_uuid,
        action="document_deleted",
        entity_type="document",
        entity_id=document_id,
        metadata={"filename": filename},
    )
    await session.commit()
    return Response(status_code=status.HTTP_204_NO_CONTENT)
