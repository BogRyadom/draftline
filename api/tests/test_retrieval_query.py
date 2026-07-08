"""Retrieval-query construction: the KB search query is focused (subject + head
of body), while the draft prompt still sees the full body. No network/DB."""

from app.llm import _draft_messages
from app.routers.emails import RAG_QUERY_HEAD_CHARS, build_retrieval_query

# A distinctive token buried well past the head cutoff, so it is excluded from the
# focused retrieval query but must still reach the draft prompt (full body).
BURIED = "ZEBRAQUESTION"
SUBJECT = "Order help"
BODY = ("Please help me. " * 30) + BURIED + " Thanks."  # BURIED sits ~past char 480


def test_retrieval_query_is_subject_plus_head_only():
    q = build_retrieval_query(SUBJECT, BODY)
    assert q.startswith(SUBJECT)
    # Only the first RAG_QUERY_HEAD_CHARS of the body are included.
    assert q == f"{SUBJECT} {BODY[:RAG_QUERY_HEAD_CHARS]}".strip()
    # A question buried past the head is NOT in the retrieval query.
    assert BURIED not in q


def test_draft_prompt_sees_the_full_body_including_buried_text():
    # The same email's draft prompt must contain the buried token, proving the
    # truncation is retrieval-only and the reply stays grounded in the whole email.
    source = {
        "from_name": "Sam",
        "from_email": "sam@acme.com",
        "subject": SUBJECT,
        "body_text": BODY,
        "snippet": "",
    }
    chunks = [{"filename": "kb.docx", "chunk_index": 0, "content": "Some policy."}]
    messages = _draft_messages(source, chunks, tone={})
    joined = "\n".join(m["content"] for m in messages)
    assert BURIED in joined


def test_retrieval_query_short_body_is_untruncated():
    q = build_retrieval_query("Hi", "short body")
    assert q == "Hi short body"


def test_retrieval_query_handles_missing_subject():
    # Off-topic emails often have an empty subject; no leading space, head only.
    q = build_retrieval_query("", BODY)
    assert q == BODY[:RAG_QUERY_HEAD_CHARS].strip()
    assert BURIED not in q


def test_retrieval_query_handles_missing_body():
    assert build_retrieval_query("Just a subject", None) == "Just a subject"
    assert build_retrieval_query(None, None) == ""
