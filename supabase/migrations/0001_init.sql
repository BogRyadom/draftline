-- Draftline — initial schema (§3 of the spec).
-- Postgres + pgvector. RLS enabled on every app table with policy
-- `user_id = auth.uid()`. Embedding dimension is 768 (Gemini text-embedding-004);
-- change it only if you change the embedding provider.
--
-- Apply via the Supabase SQL editor, or `supabase db push` (see supabase/README.md).

-- pgvector, installed into `public` so `vector(768)` and the `<=>` operator
-- resolve without schema qualification in later phases.
create extension if not exists vector;

-- Keep `updated_at` fresh on rows that track edits.
create or replace function set_updated_at()
returns trigger
language plpgsql
as $$
begin
  new.updated_at = now();
  return new;
end;
$$;

-- ── email_accounts ─────────────────────────────────────────────────────────
create table if not exists email_accounts (
  id                     uuid primary key default gen_random_uuid(),
  user_id                uuid not null references auth.users (id) on delete cascade,
  provider               text not null check (provider in ('gmail', 'outlook')),
  email_address          text not null,
  oauth_refresh_token_enc text,
  status                 text not null default 'connected'
                           check (status in ('connected', 'error', 'revoked')),
  last_synced_at         timestamptz,
  created_at             timestamptz not null default now()
);
create index if not exists email_accounts_user_id_idx on email_accounts (user_id);

-- ── emails ─────────────────────────────────────────────────────────────────
create table if not exists emails (
  id                    uuid primary key default gen_random_uuid(),
  user_id               uuid not null references auth.users (id) on delete cascade,
  account_id            uuid not null references email_accounts (id) on delete cascade,
  provider_message_id   text not null,
  thread_id             text,
  from_name             text,
  from_email            text,
  subject               text,
  snippet               text,
  body_text             text,
  received_at           timestamptz,
  category              text,
  priority              text check (priority in ('low', 'normal', 'high', 'urgent')),
  classification_reason text,
  status                text not null default 'new'
                          check (status in ('new', 'classified', 'drafted', 'dismissed')),
  created_at            timestamptz not null default now(),
  -- provider_message_id is unique per connected account (dedup on sync).
  constraint emails_account_message_unique unique (account_id, provider_message_id)
);
create index if not exists emails_user_id_idx on emails (user_id);
create index if not exists emails_account_id_idx on emails (account_id);
create index if not exists emails_status_idx on emails (status);

-- ── drafts ─────────────────────────────────────────────────────────────────
create table if not exists drafts (
  id                uuid primary key default gen_random_uuid(),
  user_id           uuid not null references auth.users (id) on delete cascade,
  email_id          uuid not null references emails (id) on delete cascade,
  body              text,
  model             text,
  prompt_tokens     int,
  completion_tokens int,
  citations         jsonb not null default '[]'::jsonb,  -- [{document_id, filename, chunk_index, quote}]
  confidence        text check (confidence in ('low', 'medium', 'high')),
  status            text not null default 'pending'
                      check (status in ('pending', 'edited', 'saved_to_gmail', 'dismissed')),
  created_at        timestamptz not null default now(),
  updated_at        timestamptz not null default now()
);
create index if not exists drafts_user_id_idx on drafts (user_id);
create index if not exists drafts_email_id_idx on drafts (email_id);

create trigger drafts_set_updated_at
  before update on drafts
  for each row execute function set_updated_at();

-- ── documents ──────────────────────────────────────────────────────────────
create table if not exists documents (
  id          uuid primary key default gen_random_uuid(),
  user_id     uuid not null references auth.users (id) on delete cascade,
  filename    text not null,
  mime_type   text,
  status      text not null default 'processing'
                check (status in ('processing', 'ready', 'failed')),
  chunk_count int not null default 0,
  created_at  timestamptz not null default now()
);
create index if not exists documents_user_id_idx on documents (user_id);

-- ── document_chunks ────────────────────────────────────────────────────────
create table if not exists document_chunks (
  id          uuid primary key default gen_random_uuid(),
  document_id uuid not null references documents (id) on delete cascade,
  user_id     uuid not null references auth.users (id) on delete cascade,
  content     text not null,
  embedding   vector(768),
  chunk_index int not null,
  metadata    jsonb not null default '{}'::jsonb
);
create index if not exists document_chunks_document_id_idx on document_chunks (document_id);
create index if not exists document_chunks_user_id_idx on document_chunks (user_id);

-- Approximate-nearest-neighbour index for cosine similarity (used from Phase 3).
-- Safe to build on an empty table; remove if your pgvector is < 0.5.
create index if not exists document_chunks_embedding_idx
  on document_chunks using hnsw (embedding vector_cosine_ops);

-- ── audit_logs ─────────────────────────────────────────────────────────────
create table if not exists audit_logs (
  id          uuid primary key default gen_random_uuid(),
  user_id     uuid not null references auth.users (id) on delete cascade,
  action      text not null,
  entity_type text,
  entity_id   uuid,
  metadata    jsonb not null default '{}'::jsonb,
  created_at  timestamptz not null default now()
);
create index if not exists audit_logs_user_id_idx on audit_logs (user_id);
create index if not exists audit_logs_action_idx on audit_logs (action);

-- ── settings ───────────────────────────────────────────────────────────────
create table if not exists settings (
  user_id               uuid primary key references auth.users (id) on delete cascade,
  categories            jsonb not null default
                          '["Sales","Support","Billing","Personal","Other"]'::jsonb,
  tone                  jsonb not null default
                          '{"formality":"neutral","length":"concise","signature":""}'::jsonb,
  poll_enabled          boolean not null default false,
  poll_interval_minutes int not null default 15,
  auto_push_drafts      boolean not null default false
);

-- ── Row-level security ─────────────────────────────────────────────────────
-- Every app table is isolated per user. The backend also filters by user_id;
-- RLS is the enforced second layer, and the only guard for any direct client
-- access via the Supabase anon key.
alter table email_accounts   enable row level security;
alter table emails           enable row level security;
alter table drafts           enable row level security;
alter table documents        enable row level security;
alter table document_chunks  enable row level security;
alter table audit_logs       enable row level security;
alter table settings         enable row level security;

create policy "own rows" on email_accounts
  for all to authenticated
  using (auth.uid() = user_id) with check (auth.uid() = user_id);

create policy "own rows" on emails
  for all to authenticated
  using (auth.uid() = user_id) with check (auth.uid() = user_id);

create policy "own rows" on drafts
  for all to authenticated
  using (auth.uid() = user_id) with check (auth.uid() = user_id);

create policy "own rows" on documents
  for all to authenticated
  using (auth.uid() = user_id) with check (auth.uid() = user_id);

create policy "own rows" on document_chunks
  for all to authenticated
  using (auth.uid() = user_id) with check (auth.uid() = user_id);

create policy "own rows" on audit_logs
  for all to authenticated
  using (auth.uid() = user_id) with check (auth.uid() = user_id);

create policy "own rows" on settings
  for all to authenticated
  using (auth.uid() = user_id) with check (auth.uid() = user_id);
