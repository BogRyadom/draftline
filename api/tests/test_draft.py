"""Draft assembly tests: code-side citations + confidence (no network)."""

import json

import pytest

from app.llm import (
    DRAFT_MODEL,
    citations_from_chunks,
    confidence_from_chunks,
    parse_draft,
    strip_out_of_range_citations,
)

CHUNKS = [
    {"document_id": "d1", "filename": "policy.docx", "chunk_index": 0,
     "content": "Refund within 30 days.", "similarity": 0.72},
    {"document_id": "d2", "filename": "hours.docx", "chunk_index": 3,
     "content": "Open 9 to 5.", "similarity": 0.55},
]


def test_citations_come_from_retrieved_chunks():
    cites = citations_from_chunks(CHUNKS)
    assert [c.chunk_index for c in cites] == [0, 3]
    assert cites[0].document_id == "d1"
    assert cites[0].filename == "policy.docx"
    assert cites[0].quote == "Refund within 30 days."


def test_citations_are_deterministic_ignoring_model_claims():
    # The model's own words about sources/confidence are ignored; citations are
    # the retrieved chunks, so the same email always yields the same citations.
    content = json.dumps(
        {"body": "Yes, within 30 days [1].", "used_sources": [2], "confidence": "low"}
    )
    result = parse_draft(
        content, CHUNKS, usage_prompt=10, usage_completion=5, high_cutoff=0.6
    )
    assert result.body == "Yes, within 30 days [1]."
    assert [c.chunk_index for c in result.citations] == [0, 3]
    assert result.model == DRAFT_MODEL
    assert result.prompt_tokens == 10 and result.completion_tokens == 5


def test_confidence_high_when_top_similarity_meets_cutoff():
    assert confidence_from_chunks(CHUNKS, high_cutoff=0.6) == "high"  # top 0.72


def test_confidence_medium_when_below_cutoff():
    assert confidence_from_chunks(CHUNKS, high_cutoff=0.8) == "medium"  # top 0.72


def test_confidence_low_when_no_chunks():
    assert confidence_from_chunks([], high_cutoff=0.6) == "low"


def test_no_chunks_yields_low_confidence_and_no_citations():
    content = json.dumps({"body": "A team member will follow up."})
    result = parse_draft(content, [], usage_prompt=1, usage_completion=1, high_cutoff=0.6)
    assert result.confidence == "low"
    assert result.citations == []


def test_strips_out_of_range_citation_markers():
    assert (
        strip_out_of_range_citations("A [1] and [2] but not [5].", 2)
        == "A [1] and [2] but not."
    )


def test_strips_all_markers_when_no_sources():
    assert strip_out_of_range_citations("We will follow up [1].", 0) == "We will follow up."


def test_parse_draft_drops_hallucinated_markers_in_body():
    content = json.dumps({"body": "Refund in 30 days [1]. Also see [9]."})
    result = parse_draft(content, CHUNKS, usage_prompt=1, usage_completion=1, high_cutoff=0.6)
    assert "[9]" not in result.body
    assert "[1]" in result.body


def test_malformed_json_raises():
    with pytest.raises(json.JSONDecodeError):
        parse_draft("not json", CHUNKS, usage_prompt=0, usage_completion=0, high_cutoff=0.6)
