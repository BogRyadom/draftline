# Supabase

Schema and setup for Draftline's Postgres database (Auth + pgvector).

## Apply the schema

**Option A — SQL editor (simplest).** Open your Supabase project →
*SQL Editor* → paste the contents of
[`migrations/0001_init.sql`](migrations/0001_init.sql) → Run.

**Option B — Supabase CLI.**

```bash
supabase link --project-ref <your-project-ref>
supabase db push
```

The migration creates every §3 table, enables Row-Level Security with a
`user_id = auth.uid()` policy on each, installs `pgvector`, and defines a
768-dim embedding column (Gemini `text-embedding-004`).

## JWT signing keys (required for the API)

The FastAPI backend verifies access tokens against the project's **public JWKS**,
so Auth must use **asymmetric** signing keys (ES256/RS256). New projects default
to this. On an older project: *Authentication → Signing Keys* → create/rotate to
an ECC (asymmetric) key. The JWKS endpoint is:

```
https://<project-ref>.supabase.co/auth/v1/.well-known/jwks.json
```

## Google login (Phase 0) and Gmail (Phase 1)

Phase 0 uses Supabase Auth's **Google provider** for login — enable it under
*Authentication → Providers → Google* with an OAuth client. Phase 1 adds Gmail
API access (read + `drafts.create`) as a separate OAuth flow.
