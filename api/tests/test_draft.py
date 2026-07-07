"""Draft parsing + citation mapping tests (no network)."""

import json

import pytest

from app.llm import DRAFT_MODEL, parse_draft

CHUNKS = [
    {"document_id": "d1", "filename": "policy.docx", "chunk_index": 0, "content": "Refund within 30 days."},
    {"document_id": "d2", "filename": "hours.docx", "chunk_index": 3, "content": "Open 9 to 5."},
]


def _json(**kw) -> str:
    return json.dumps(kw)


def test_maps_used_sources_to_citations():
    content = _json(body="Yes, within 30 days [1].", used_sources=[1], confidence="high")
    result = parse_draft(content, CHUNKS, usage_prompt=10, usage_completion=5)

    assert result.body == "Yes, within 30 days [1]."
    assert result.confidence == "high"
    assert result.model == DRAFT_MODEL
    assert result.prompt_tokens == 10 and result.completion_tokens == 5
    assert len(result.citations) == 1
    c = result.citations[0]
    assert c.document_id == "d1"
    assert c.filename == "policy.docx"
    assert c.chunk_index == 0
    assert c.quote == "Refund within 30 days."


def test_dedupes_and_drops_out_of_range_sources():
    content = _json(body="…", used_sources=[1, 1, 2, 5, "x"], confidence="medium")
    result = parse_draft(content, CHUNKS, usage_prompt=1, usage_completion=1)

    assert [c.chunk_index for c in result.citations] == [0, 3]  # sources 1 and 2 only


def test_no_chunks_forces_low_confidence():
    content = _json(body="I don't have that information on file.", used_sources=[], confidence="high")
    result = parse_draft(content, [], usage_prompt=1, usage_completion=1)

    assert result.confidence == "low"
    assert result.citations == []


def test_invalid_confidence_defaults_low():
    content = _json(body="…", used_sources=[1], confidence="totally-sure")
    result = parse_draft(content, CHUNKS, usage_prompt=1, usage_completion=1)
    assert result.confidence == "low"


def test_malformed_json_raises():
    with pytest.raises(json.JSONDecodeError):
        parse_draft("not json", CHUNKS, usage_prompt=0, usage_completion=0)
