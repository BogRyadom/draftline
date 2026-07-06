"""Thin LLM module.

One interface, one default: Groq via the OpenAI-compatible client. Swapping to
real OpenAI or Anthropic later is a base-URL + key change in this one file — no
plugin system. Phase 2 uses only `classify()`; `draft()`/`embed()` arrive later.
"""

from __future__ import annotations

import json
import time
from functools import lru_cache
from typing import Literal

import httpx
from openai import APIError, OpenAI, RateLimitError
from pydantic import BaseModel, ValidationError

from app.config import get_settings

GROQ_BASE_URL = "https://api.groq.com/openai/v1"
CLASSIFY_MODEL = "llama-3.1-8b-instant"

# Embeddings: Gemini (Groq has no embeddings API). text-embedding-004 is retired;
# gemini-embedding-001 with outputDimensionality=768 keeps the vector(768) schema.
GEMINI_BASE_URL = "https://generativelanguage.googleapis.com/v1"
EMBED_MODEL = "gemini-embedding-001"
EMBEDDING_DIM = 768

PRIORITIES = ("low", "normal", "high", "urgent")

# Bound token usage on very long emails.
_MAX_BODY_CHARS = 2000
_MAX_REASON_CHARS = 280


class LLMError(Exception):
    """Raised when the model call fails after retries/backoff."""


class Classification(BaseModel):
    category: str
    priority: Literal["low", "normal", "high", "urgent"]
    reason: str


@lru_cache
def _client() -> OpenAI:
    key = get_settings().groq_api_key
    if not key:
        raise LLMError("GROQ_API_KEY is not configured.")
    return OpenAI(api_key=key, base_url=GROQ_BASE_URL)


_SYSTEM_PROMPT = (
    "You are an email triage assistant. Read one email and classify it. "
    "Respond with ONLY a JSON object of exactly this shape: "
    '{"category": string, "priority": string, "reason": string}. '
    "`priority` must be one of: low, normal, high, urgent — based on how urgent "
    "and important the email is to the recipient. `reason` is one short sentence "
    "explaining the choice. `category` must be exactly one of the allowed "
    "categories provided by the user."
)


def _messages(
    *,
    subject: str | None,
    from_email: str | None,
    snippet: str | None,
    body_text: str | None,
    categories: list[str],
) -> list[dict]:
    body = (body_text or snippet or "").strip()[:_MAX_BODY_CHARS]
    user = (
        f"Allowed categories (choose exactly one): {', '.join(categories)}\n\n"
        f"From: {from_email or 'unknown'}\n"
        f"Subject: {subject or '(no subject)'}\n"
        f"Body:\n{body or '(empty)'}\n\n"
        "Return the JSON object now."
    )
    return [
        {"role": "system", "content": _SYSTEM_PROMPT},
        {"role": "user", "content": user},
    ]


def coerce_classification(data: dict, categories: list[str]) -> Classification:
    """Clamp a raw model dict to our schema (valid priority + allowed category)."""
    priority = str(data.get("priority", "")).strip().lower()
    if priority not in PRIORITIES:
        priority = "normal"

    raw_category = str(data.get("category", "")).strip()
    match = next((c for c in categories if c.lower() == raw_category.lower()), None)
    if match is None:
        match = "Other" if "Other" in categories else (categories[-1] if categories else "Other")

    reason = str(data.get("reason", "")).strip()[:_MAX_REASON_CHARS]
    return Classification(category=match, priority=priority, reason=reason)


def parse_classification(content: str, categories: list[str]) -> Classification:
    """Parse + validate a JSON model response. Raises on malformed JSON."""
    return coerce_classification(json.loads(content), categories)


def _complete(messages: list[dict], *, max_429_retries: int = 3) -> str:
    """Call Groq in JSON mode, backing off on 429. Returns the raw content."""
    for attempt in range(max_429_retries + 1):
        try:
            resp = _client().chat.completions.create(
                model=CLASSIFY_MODEL,
                messages=messages,
                response_format={"type": "json_object"},
                temperature=0,
            )
            return resp.choices[0].message.content or ""
        except RateLimitError:
            if attempt == max_429_retries:
                raise LLMError("Groq rate limit exceeded after backoff.")
            time.sleep(2 * (attempt + 1))
        except APIError as exc:
            raise LLMError(f"Groq API error: {exc}") from exc
    raise LLMError("Groq call failed.")  # pragma: no cover


def classify(
    *,
    subject: str | None,
    from_email: str | None,
    snippet: str | None,
    body_text: str | None,
    categories: list[str],
) -> Classification:
    """Classify one email into {category, priority, reason}. JSON mode, one retry
    on a malformed response, backoff on 429."""
    messages = _messages(
        subject=subject,
        from_email=from_email,
        snippet=snippet,
        body_text=body_text,
        categories=categories,
    )

    for _ in range(2):  # initial attempt + one retry on parse failure
        content = _complete(messages)
        try:
            return parse_classification(content, categories)
        except (json.JSONDecodeError, ValidationError):
            continue

    raise LLMError("Model did not return valid classification JSON.")


# ── Embeddings (Gemini) ─────────────────────────────────────────────────────


def _embed_one(
    client: httpx.Client, key: str, text: str, task_type: str, *, max_retries: int = 4
) -> list[float]:
    url = f"{GEMINI_BASE_URL}/models/{EMBED_MODEL}:embedContent?key={key}"
    body = {
        "model": f"models/{EMBED_MODEL}",
        "content": {"parts": [{"text": text}]},
        "taskType": task_type,
        "outputDimensionality": EMBEDDING_DIM,
    }
    for attempt in range(max_retries + 1):
        try:
            resp = client.post(url, json=body)
        except httpx.TransportError as exc:
            if attempt == max_retries:
                raise LLMError(f"Gemini network error: {exc}") from exc
            time.sleep(2 * (attempt + 1))
            continue
        if resp.status_code == 429:
            if attempt == max_retries:
                raise LLMError("Gemini rate limit exceeded after backoff.")
            time.sleep(2 * (attempt + 1))
            continue
        if resp.status_code >= 400:
            raise LLMError(f"Gemini embed error {resp.status_code}: {resp.text[:200]}")
        return resp.json()["embedding"]["values"]
    raise LLMError("Gemini embed failed.")  # pragma: no cover


def embed(
    texts: list[str], *, task_type: str = "RETRIEVAL_DOCUMENT"
) -> list[list[float]]:
    """Embed texts with Gemini gemini-embedding-001 at 768 dims. Blocking; call via
    run_in_threadpool. `task_type` is RETRIEVAL_DOCUMENT for stored chunks and
    RETRIEVAL_QUERY for search queries. One request per text (this model's batch
    endpoint is unreliable); retries transient network errors and 429s."""
    if not texts:
        return []
    key = get_settings().gemini_api_key
    if not key:
        raise LLMError("GEMINI_API_KEY is not configured.")

    with httpx.Client(timeout=90) as client:
        return [_embed_one(client, key, text, task_type) for text in texts]


def embed_query(text: str) -> list[float]:
    """Embed a single search query."""
    return embed([text], task_type="RETRIEVAL_QUERY")[0]
