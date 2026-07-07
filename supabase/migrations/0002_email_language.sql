-- Draftline — add detected language to emails.
-- The classify pass now records the human-readable language each email is
-- written in (e.g. 'English', 'Russian') so reply drafts answer in the
-- customer's language. Nullable; existing rows stay null until re-classified.
--
-- Apply via the Supabase SQL editor, or `supabase db push`.

alter table emails add column if not exists language text;
