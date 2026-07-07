"""Extraction + chunking tests (no network)."""

import io

import pytest
from docx import Document as DocxDocument

from app.extract import (
    DOCX_MIME,
    UnsupportedFileType,
    chunk_text,
    extract_text,
    normalize_text,
)


def _make_docx(paragraphs: list[str]) -> bytes:
    doc = DocxDocument()
    for p in paragraphs:
        doc.add_paragraph(p)
    buf = io.BytesIO()
    doc.save(buf)
    return buf.getvalue()


def test_extract_docx_returns_paragraph_text():
    data = _make_docx(["Refund policy", "Returns accepted within 30 days."])
    text = extract_text(data, mime_type=DOCX_MIME, filename="policy.docx")
    assert "Refund policy" in text
    assert "within 30 days" in text


def test_extract_rejects_unsupported_type():
    with pytest.raises(UnsupportedFileType):
        extract_text(b"data", mime_type="text/plain", filename="notes.txt")


def test_extension_fallback_when_mime_missing():
    data = _make_docx(["Hello world"])
    text = extract_text(data, mime_type=None, filename="doc.docx")
    assert "Hello world" in text


def test_normalize_collapses_whitespace():
    assert normalize_text("a\r\n\n\n\nb   c\t\td") == "a\n\nb c d"


def test_chunk_short_text_single_chunk():
    assert chunk_text("just a short note") == ["just a short note"]


def test_chunk_empty_text():
    assert chunk_text("   \n  ") == []


def test_chunk_long_text_overlaps_and_respects_size():
    words = " ".join(f"word{i}" for i in range(3000))  # well over one chunk
    chunks = chunk_text(words, chunk_chars=1000, overlap_chars=200)

    assert len(chunks) > 1
    # Each chunk is within the size budget (allowing for the break search window).
    assert all(len(c) <= 1000 for c in chunks)
    # Consecutive chunks overlap (end of one appears at the start region of next).
    tail = chunks[0][-100:].split()[-1]
    assert tail in chunks[1]
