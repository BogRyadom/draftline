"""Thin LLM module.

One interface, one default: Groq via the OpenAI-compatible client. Swapping to
real OpenAI or Anthropic later is a base-URL + key change in this one file — no
plugin system. Phase 2 uses only `classify()`; `draft()`/`embed()` arrive later.
"""

from __future__ import annotations

import json
import re
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
_MAX_LANGUAGE_CHARS = 40


class LLMError(Exception):
    """Raised when the model call fails after retries/backoff."""


class Classification(BaseModel):
    category: str
    priority: Literal["low", "normal", "high", "urgent"]
    reason: str
    # Human-readable language the email is written in (e.g. "English", "Russian").
    language: str = ""


@lru_cache
def _client() -> OpenAI:
    key = get_settings().groq_api_key
    if not key:
        raise LLMError("GROQ_API_KEY is not configured.")
    return OpenAI(api_key=key, base_url=GROQ_BASE_URL)


_SYSTEM_PROMPT = (
    "You are an email triage assistant. Read one email and classify it. "
    "Respond with ONLY a JSON object of exactly this shape: "
    '{"category": string, "priority": string, "reason": string, "language": string}. '
    "`priority` must be one of: low, normal, high, urgent — based on how urgent "
    "and important the email is to the recipient. `reason` is one short sentence "
    "explaining the choice. `category` must be exactly one of the allowed "
    "categories provided by the user. `language` is the human-readable name of the "
    'language the email is written in (e.g. "English", "Russian", "Spanish").'
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
    language = str(data.get("language", "")).strip()[:_MAX_LANGUAGE_CHARS]
    return Classification(category=match, priority=priority, reason=reason, language=language)


def parse_classification(content: str, categories: list[str]) -> Classification:
    """Parse + validate a JSON model response. Raises on malformed JSON."""
    return coerce_classification(json.loads(content), categories)


def _chat(messages: list[dict], *, model: str, temperature: float = 0.0, max_429_retries: int = 3):
    """Call Groq in JSON mode, backing off on 429. Returns the completion."""
    for attempt in range(max_429_retries + 1):
        try:
            return _client().chat.completions.create(
                model=model,
                messages=messages,
                response_format={"type": "json_object"},
                temperature=temperature,
            )
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
        content = _chat(messages, model=CLASSIFY_MODEL, temperature=0).choices[0].message.content or ""
        try:
            return parse_classification(content, categories)
        except (json.JSONDecodeError, ValidationError):
            continue

    raise LLMError("Model did not return valid classification JSON.")


# ── Drafting (Groq 70B, grounded) ───────────────────────────────────────────

DRAFT_MODEL = "llama-3.3-70b-versatile"

_MAX_SOURCE_BODY_CHARS = 4000
_MAX_CHUNK_CHARS = 1200
_MAX_QUOTE_CHARS = 240


class Citation(BaseModel):
    document_id: str | None = None
    filename: str | None = None
    chunk_index: int | None = None
    quote: str
    # TEMPORARY diagnostic: cosine similarity of this chunk to the query, surfaced
    # in the UI to help tune the retrieval threshold. Remove after tuning.
    similarity: float | None = None


class DraftResult(BaseModel):
    body: str
    citations: list[Citation]
    confidence: Literal["low", "medium", "high"]
    model: str
    prompt_tokens: int
    completion_tokens: int


_DRAFT_SYSTEM_PROMPT = (
    "You draft reply emails for a human to review before anything is sent. Rules:\n"
    "- Ground every factual claim ONLY in the incoming email and the provided sources.\n"
    "- If sources ARE provided, answer specifically using ONLY those sources and cite "
    "them inline as [n] (n is the source number); never cite a number that was not "
    "provided.\n"
    "- If NO sources are provided, do not answer from your own knowledge: write a "
    "short, polite reply saying we do not have this information in our knowledge base "
    "and that a team member will follow up. Invent no facts, policies, prices, dates, "
    "or commitments, and cite nothing.\n"
    "- Write only the reply body: no subject line, no email headers, and no "
    "signature or sign-off (do not add 'Best regards', a name, etc.) — the "
    "signature is added afterward.\n"
    "- Match the requested tone and length.\n"
    'Return ONLY JSON: {"body": string}.'
)


def _language_instruction(language: str | None) -> str:
    """How the reply's language is chosen: honor the detected language, else
    tell the model to mirror the incoming email's language."""
    lang = (language or "").strip()
    if lang:
        return (
            f"Write the ENTIRE reply in {lang}, matching the language the customer "
            "wrote in. Do not switch languages."
        )
    return (
        "Detect the language of the incoming email and write the ENTIRE reply in "
        "that same language. Do not switch languages."
    )


def _draft_messages(
    source_email: dict, chunks: list[dict], tone: dict, language: str | None = None
) -> list[dict]:
    body = (source_email.get("body_text") or source_email.get("snippet") or "").strip()
    lines = [
        _language_instruction(language),
        "",
        "Incoming email:",
        f"From: {source_email.get('from_name') or ''} <{source_email.get('from_email') or 'unknown'}>",
        f"Subject: {source_email.get('subject') or '(no subject)'}",
        f"Body:\n{body[:_MAX_SOURCE_BODY_CHARS] or '(empty)'}",
        "",
    ]
    if chunks:
        lines.append("Knowledge base sources (cite with [n]):")
        for i, ch in enumerate(chunks, start=1):
            label = f"{ch.get('filename') or 'document'}, chunk {ch.get('chunk_index')}"
            lines.append(f"[{i}] ({label}): {(ch.get('content') or '')[:_MAX_CHUNK_CHARS]}")
    else:
        lines.append(
            "Knowledge base sources: NONE. Do not invent an answer. Write a short, "
            "polite reply stating we do not have this information in our knowledge base "
            "and that a team member will follow up. Do not include any [n] citations."
        )
    lines += [
        "",
        f"Tone: formality={tone.get('formality', 'neutral')}, length={tone.get('length', 'concise')}.",
        "\nReturn the JSON now.",
    ]

    return [
        {"role": "system", "content": _DRAFT_SYSTEM_PROMPT},
        {"role": "user", "content": "\n".join(lines)},
    ]


def citations_from_chunks(chunks: list[dict]) -> list[Citation]:
    """Citations are the retrieved above-threshold chunks — the single source of
    truth, independent of which [n] the model happened to cite. This makes the
    citations for a given email deterministic."""
    return [
        Citation(
            document_id=ch.get("document_id"),
            filename=ch.get("filename"),
            chunk_index=ch.get("chunk_index"),
            quote=(ch.get("content") or "").strip()[:_MAX_QUOTE_CHARS],
            # TEMPORARY diagnostic: round the retrieval score for display.
            similarity=round(float(ch["similarity"]), 3) if ch.get("similarity") is not None else None,
        )
        for ch in chunks
    ]


# A small multilingual set of closing salutations, used to detect and trim a
# model-added sign-off before appending the user's configured signature.
_SIGNOFF_MARKERS = frozenset(
    {
        "best regards", "kind regards", "warm regards", "best wishes", "regards",
        "best", "sincerely", "yours sincerely", "yours faithfully", "yours truly",
        "respectfully", "cheers", "thanks", "thank you", "many thanks", "thanks again",
        "с уважением", "с наилучшими пожеланиями", "спасибо",  # Russian
        "saludos", "atentamente", "un saludo",  # Spanish
        "cordialement", "bien à vous",  # French
        "mit freundlichen grüßen",  # German
    }
)


def strip_signoff(body: str) -> str:
    """Trim a trailing closing salutation and the name line(s) after it, so an
    appended signature does not double up or drift. Conservative: only fires when
    a known closing is, on its own, one of the last few lines."""
    lines = body.rstrip().split("\n")
    start = max(0, len(lines) - 5)
    for i in range(len(lines) - 1, start - 1, -1):
        norm = lines[i].strip().rstrip(".,!;:").lower()
        if not norm:
            continue
        if norm in _SIGNOFF_MARKERS:
            return "\n".join(lines[:i]).rstrip()
    return body.rstrip()


def apply_signature(body: str, signature: str) -> str:
    """Strip any model-generated sign-off, then append the configured signature.
    Signature handling lives in code, not the prompt, so it never doubles up."""
    body = strip_signoff(body)
    signature = (signature or "").strip()
    if signature:
        body = f"{body}\n\n{signature}"
    return body


_CITATION_MARKER_RE = re.compile(r"\[(\d+)\]")


def strip_out_of_range_citations(body: str, n_sources: int) -> str:
    """Drop any [n] whose number falls outside 1..n_sources (e.g. a hallucinated
    [5] when only 3 sources exist, or any marker at all when there are none), then
    tidy the whitespace and stray punctuation the removal leaves behind."""

    def repl(match: re.Match) -> str:
        n = int(match.group(1))
        return match.group(0) if 1 <= n <= n_sources else ""

    cleaned = _CITATION_MARKER_RE.sub(repl, body)
    cleaned = re.sub(r"[ \t]{2,}", " ", cleaned)
    cleaned = re.sub(r"[ \t]+([.,;:!?])", r"\1", cleaned)
    return cleaned.strip()


def confidence_from_chunks(chunks: list[dict], *, high_cutoff: float) -> str:
    """Confidence is computed from retrieval, not decided by the model:
    no chunks → low; top similarity below `high_cutoff` → medium; at/above → high."""
    if not chunks:
        return "low"
    top = max(float(ch.get("similarity") or 0.0) for ch in chunks)
    return "high" if top >= high_cutoff else "medium"


def parse_draft(
    content: str,
    chunks: list[dict],
    *,
    usage_prompt: int,
    usage_completion: int,
    high_cutoff: float,
) -> DraftResult:
    """Parse the model's draft JSON (body only) and attach code-derived citations
    and confidence from the retrieved chunks."""
    data = json.loads(content)
    body = str(data.get("body", "")).strip()
    # Drop citation markers the model may have invented beyond the real sources.
    body = strip_out_of_range_citations(body, len(chunks))
    return DraftResult(
        body=body,
        citations=citations_from_chunks(chunks),
        confidence=confidence_from_chunks(chunks, high_cutoff=high_cutoff),
        model=DRAFT_MODEL,
        prompt_tokens=usage_prompt,
        completion_tokens=usage_completion,
    )


def draft(
    *, source_email: dict, chunks: list[dict], tone: dict, language: str | None = None
) -> DraftResult:
    """Generate a grounded reply draft. Citations and confidence come from the
    retrieved chunks (deterministic), not from the model. The reply is written in
    `language` when known, otherwise in the incoming email's detected language."""
    high_cutoff = get_settings().rag_confidence_high_similarity
    messages = _draft_messages(source_email, chunks, tone, language)

    for _ in range(2):  # initial attempt + one retry on parse failure
        resp = _chat(messages, model=DRAFT_MODEL, temperature=0.4)
        content = resp.choices[0].message.content or ""
        usage = resp.usage
        try:
            return parse_draft(
                content,
                chunks,
                usage_prompt=getattr(usage, "prompt_tokens", 0) or 0,
                usage_completion=getattr(usage, "completion_tokens", 0) or 0,
                high_cutoff=high_cutoff,
            )
        except (json.JSONDecodeError, ValidationError):
            continue

    raise LLMError("Model did not return a valid draft.")


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
