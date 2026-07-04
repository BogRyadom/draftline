# Draftline — AI Inbox Assistant

Connect an email account and Draftline reads incoming mail, **classifies and
prioritizes** it, and writes a **grounded reply draft** from your uploaded
knowledge base — with citations and a confidence signal. You review, edit, and
decide.

> **Draftline never sends email.** Drafts live in-app and, only on your explicit
> action, are written to your provider's *Drafts* folder. There is no send path.

## Why it exists

This is the pattern teams keep asking for: **Gmail → read → AI classify +
prioritize → RAG draft → human approves → nothing auto-sent.** Human-in-the-loop
by design, grounded rather than hallucinated, and small enough to reason about.

## Stack (all free-tier)

| Layer        | Choice |
|--------------|--------|
| Frontend     | Next.js (App Router) · TypeScript · Tailwind · shadcn/ui — Vercel |
| Backend      | FastAPI · Python 3.12 · uvicorn · Pydantic v2 — Render |
| DB / Auth    | Supabase (Postgres + Auth + pgvector) |
| DB access    | SQLAlchemy 2.0 async + asyncpg |
| Email        | Gmail API (read + `drafts.create` only) |
| LLM          | Groq — `llama-3.1-8b-instant` (classify) · `llama-3.3-70b-versatile` (draft) |
| Embeddings   | Google Gemini `text-embedding-004` (768 dims) |

## Repository layout

```
draftline/
├── web/    Next.js frontend (App Router, TypeScript)
└── api/    FastAPI backend (async)
```

## Status

🚧 **In active development, built phase by phase.**

- [x] **Phase 0** — Foundation: repo, auth, DB schema, authenticated round-trip
- [x] **Phase 1** — Connect Gmail (OAuth) + sync unread mail into the app
- [ ] Phase 2 — Classify + prioritize
- [ ] Phase 3 — Knowledge base + RAG index
- [ ] Phase 4 — Draft generation
- [ ] Phase 5 — Dashboard, audit, settings, polish
- [ ] Phase 6 — Deploy + demo assets

## Local setup

See [`web/README.md`](web/README.md) and [`api/README.md`](api/README.md).
Copy each `.env.example` to `.env` and fill in your own keys. **Never commit
secrets** — `.env*` files are gitignored.
