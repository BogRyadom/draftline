# Draftline Web

Next.js (App Router · TypeScript · Tailwind v4) frontend for Draftline.
Handles Supabase Auth (email/password + Google), guards the `/app` area, and
calls the FastAPI backend with the user's JWT.

## Local setup

```bash
cd web
npm install
cp .env.example .env.local      # fill in Supabase URL + anon key, and the API URL
npm run dev                     # http://localhost:3000
```

You also need the API running (see [`../api/README.md`](../api/README.md)) and a
Supabase project with the schema applied (see
[`../supabase/README.md`](../supabase/README.md)).

## Environment

- `NEXT_PUBLIC_SUPABASE_URL` / `NEXT_PUBLIC_SUPABASE_ANON_KEY` — from Supabase
  *Project Settings → API*.
- `NEXT_PUBLIC_API_BASE_URL` — where the FastAPI backend is served
  (`http://localhost:8000` locally).

Enable **Google** under *Authentication → Providers* in Supabase, and add
`http://localhost:3000/auth/callback` (and your deployed origin) to the provider's
redirect URLs.

## Routes

- `/` — public landing
- `/sign-in`, `/sign-up` — auth (email/password + Google)
- `/app` — protected; renders the signed-in user and the `/me` round-trip
- `/auth/callback` — OAuth code exchange · `/auth/sign-out` — ends the session
