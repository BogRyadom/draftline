"""Knowledge-base processing and retrieval.

`process_document` runs after upload (background): extract → chunk → embed → store,
tracking `documents.status`. `retrieve` does cosine search over `document_chunks`
for grounding drafts (Phase 4) and the search endpoint.
"""

from __future__ import annotations

import logging
import uuid

from fastapi.concurrency import run_in_threadpool
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app import llm
from app.audit import log_action
from app.db import get_sessionmaker
from app.extract import chunk_text, extract_text
from app.models import Document, DocumentChunk

logger = logging.getLogger("draftline.knowledge")


async def _set_status(
    document_id: uuid.UUID, user_id: uuid.UUID, status: str, chunk_count: int = 0
) -> None:
    """Update a document's status in its own session (used for failure paths)."""
    async with get_sessionmaker()() as session:
        doc = (
            await session.execute(
                select(Document).where(
                    Document.id == document_id, Document.user_id == user_id
                )
            )
        ).scalar_one_or_none()
        if doc is not None:
            doc.status = status
            doc.chunk_count = chunk_count
            await session.commit()


async def process_document(
    document_id: uuid.UUID,
    user_id: uuid.UUID,
    data: bytes,
    filename: str,
    mime_type: str | None,
) -> None:
    """Background task: extract, chunk, embed, and store a document's chunks."""
    logger.info("process document %s (%s) start", document_id, filename)
    try:
        text = await run_in_threadpool(
            extract_text, data, mime_type=mime_type, filename=filename
        )
        chunks = chunk_text(text)
        if not chunks:
            logger.warning("document %s produced no text", document_id)
            await _set_status(document_id, user_id, "failed")
            return

        vectors = await run_in_threadpool(llm.embed, chunks)

        async with get_sessionmaker()() as session:
            doc = (
                await session.execute(
                    select(Document).where(
                        Document.id == document_id, Document.user_id == user_id
                    )
                )
            ).scalar_one_or_none()
            if doc is None:
                logger.warning("document %s vanished before storing chunks", document_id)
                return

            for index, (content, vector) in enumerate(zip(chunks, vectors)):
                session.add(
                    DocumentChunk(
                        document_id=document_id,
                        user_id=user_id,
                        content=content,
                        embedding=vector,
                        chunk_index=index,
                        metadata_={"filename": filename},
                    )
                )
            doc.status = "ready"
            doc.chunk_count = len(chunks)
            await log_action(
                session,
                user_id=user_id,
                action="document_uploaded",
                entity_type="document",
                entity_id=document_id,
                metadata={"filename": filename, "chunk_count": len(chunks)},
            )
            await session.commit()
        logger.info("process document %s done: %d chunks", document_id, len(chunks))
    except Exception:
        logger.exception("process document %s failed", document_id)
        await _set_status(document_id, user_id, "failed")


async def retrieve(
    session: AsyncSession, user_id: uuid.UUID, query: str, k: int = 5
) -> list[dict]:
    """Cosine-similarity search over the user's ready document chunks."""
    query_vector = await run_in_threadpool(llm.embed_query, query)
    distance = DocumentChunk.embedding.cosine_distance(query_vector)

    rows = await session.execute(
        select(DocumentChunk, Document.filename, distance.label("distance"))
        .join(Document, Document.id == DocumentChunk.document_id)
        .where(DocumentChunk.user_id == user_id, Document.status == "ready")
        .order_by(distance)
        .limit(k)
    )

    results: list[dict] = []
    for chunk, filename, dist in rows.all():
        results.append(
            {
                "document_id": str(chunk.document_id),
                "filename": filename,
                "chunk_index": chunk.chunk_index,
                "content": chunk.content,
                "similarity": round(1.0 - float(dist), 4),
            }
        )
    return results
