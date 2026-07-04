"""Classification parsing/coercion tests (no network)."""

import json

import pytest

from app.llm import coerce_classification, parse_classification

CATEGORIES = ["Sales", "Support", "Billing", "Personal", "Other"]


def test_valid_data_passes_through():
    c = coerce_classification(
        {"category": "Support", "priority": "high", "reason": "Customer needs help."},
        CATEGORIES,
    )
    assert c.category == "Support"
    assert c.priority == "high"
    assert c.reason == "Customer needs help."


def test_category_match_is_case_insensitive():
    c = coerce_classification(
        {"category": "billing", "priority": "normal", "reason": "Invoice."}, CATEGORIES
    )
    assert c.category == "Billing"


def test_unknown_category_falls_back_to_other():
    c = coerce_classification(
        {"category": "Newsletter", "priority": "low", "reason": "Promo."}, CATEGORIES
    )
    assert c.category == "Other"


def test_invalid_priority_becomes_normal():
    c = coerce_classification(
        {"category": "Sales", "priority": "super-urgent", "reason": "x"}, CATEGORIES
    )
    assert c.priority == "normal"


def test_reason_is_truncated():
    c = coerce_classification(
        {"category": "Sales", "priority": "low", "reason": "x" * 500}, CATEGORIES
    )
    assert len(c.reason) <= 280


def test_parse_classification_from_json_string():
    content = json.dumps({"category": "Sales", "priority": "urgent", "reason": "Deal."})
    c = parse_classification(content, CATEGORIES)
    assert c.category == "Sales"
    assert c.priority == "urgent"


def test_parse_classification_rejects_malformed_json():
    with pytest.raises(json.JSONDecodeError):
        parse_classification("not json at all", CATEGORIES)
