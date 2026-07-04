# Draftline API

FastAPI backend for Draftline. Validates Supabase-issued JWTs against the
project's JWKS and exposes the app's REST surface. It reads and drafts email —
**it never sends.**

## Requirements

- **Python 3.12** (matches the Render runtime). 3.13 also works locally; all
  dependencies ship wheels for both.
- A Supabase project whose Auth uses **asymmetric JWT signing keys** (ES256/RS256),
  so tokens can be verified via the public JWKS endpoint. New Supabase projects
  default to this; on an older project, enable it under
  *Authentication → Signing Keys* and migrate to the standby ECC key.

## Local setup

```bash
cd api
python -m venv .venv
# Windows PowerShell:  .venv\Scripts\Activate.ps1
# macOS/Linux:         source .venv/bin/activate
pip install -r requirements-dev.txt
cp .env.example .env          # then fill in SUPABASE_URL (and others as phases land)
uvicorn app.main:app --reload --port 8000
```

- Health check: <http://localhost:8000/health> → `{"status":"ok"}`
- Interactive docs: <http://localhost:8000/docs>

## Environment

See [`.env.example`](.env.example). Phase 0 only needs `SUPABASE_URL`
(and optionally `SUPABASE_JWKS_URL`, `FRONTEND_ORIGIN`); the rest are placeholders
for later phases and may stay empty.

## Tests

```bash
pytest
```

Covers JWT verification (accepts a validly signed token, rejects tampered /
expired / wrong-audience tokens).

## Deployment (Render, later)

Render web service, build `pip install -r requirements.txt`, start
`uvicorn app.main:app --host 0.0.0.0 --port $PORT`. Pin the interpreter with a
`PYTHON_VERSION=3.12.x` environment variable. Free tier sleeps after ~15 min
idle — warm `/health` before a live demo.
