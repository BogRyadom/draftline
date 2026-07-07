"use client";

import { useQueryClient } from "@tanstack/react-query";
import { useRouter } from "next/navigation";
import { useState } from "react";

import { Button } from "@/components/ui/button";
import { apiFetch } from "@/lib/api-client";

type Citation = {
  document_id: string | null;
  filename: string | null;
  chunk_index: number | null;
  quote: string;
};

export type Draft = {
  id: string;
  body: string | null;
  confidence: string | null;
  status: string;
  citations: Citation[];
  model: string | null;
  prompt_tokens: number | null;
  completion_tokens: number | null;
};

export type EmailDetail = {
  id: string;
  from_name: string | null;
  from_email: string | null;
  subject: string | null;
  body_text: string | null;
  received_at: string | null;
  category: string | null;
  priority: string | null;
  status: string;
};

export function DraftReview({
  email,
  initialDraft,
}: {
  email: EmailDetail;
  initialDraft: Draft | null;
}) {
  const router = useRouter();
  const queryClient = useQueryClient();
  const [draft, setDraft] = useState<Draft | null>(initialDraft);
  const [body, setBody] = useState(initialDraft?.body ?? "");
  const [busy, setBusy] = useState<null | "generate" | "save" | "gmail" | "dismiss">(null);
  const [error, setError] = useState<string | null>(null);
  const [notice, setNotice] = useState<string | null>(null);

  // Draft actions change the inbox status, dashboard counts, and audit trail.
  function invalidateLists() {
    queryClient.invalidateQueries({ queryKey: ["emails"] });
    queryClient.invalidateQueries({ queryKey: ["dashboard"] });
    queryClient.invalidateQueries({ queryKey: ["audit"] });
  }

  const dirty = draft != null && body !== (draft.body ?? "");
  const savedToGmail = draft?.status === "saved_to_gmail";
  const dismissed = draft?.status === "dismissed";

  function apply(updated: Draft) {
    setDraft(updated);
    setBody(updated.body ?? "");
  }

  async function generate() {
    setBusy("generate");
    setError(null);
    setNotice(null);
    try {
      const res = await apiFetch(`/emails/${email.id}/draft`, { method: "POST" });
      if (!res.ok) {
        setError(
          res.status === 502
            ? "The model couldn't draft a reply. Please try again."
            : `Draft failed (HTTP ${res.status}).`,
        );
        return;
      }
      apply(await res.json());
      invalidateLists();
      router.refresh();
    } catch {
      setError("Couldn't reach the API. It may be waking up — try again in ~30s.");
    } finally {
      setBusy(null);
    }
  }

  async function persistEdit(): Promise<Draft | null> {
    if (!draft) return null;
    const res = await apiFetch(`/drafts/${draft.id}`, {
      method: "PATCH",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ body }),
    });
    if (!res.ok) return null;
    const updated = await res.json();
    apply(updated);
    return updated;
  }

  async function saveEdit() {
    if (!draft) return;
    setBusy("save");
    setError(null);
    setNotice(null);
    try {
      const updated = await persistEdit();
      if (updated) setNotice("Changes saved.");
      else setError("Couldn't save your changes.");
    } finally {
      setBusy(null);
    }
  }

  async function saveToGmail() {
    if (!draft) return;
    setBusy("gmail");
    setError(null);
    setNotice(null);
    try {
      // Persist any pending edits first so Gmail gets the current text.
      if (dirty) {
        const updated = await persistEdit();
        if (!updated) {
          setError("Couldn't save your changes before saving to Gmail.");
          return;
        }
      }
      const res = await apiFetch(`/drafts/${draft.id}/save-to-gmail`, { method: "POST" });
      if (!res.ok) {
        setError(
          res.status === 502
            ? "Could not save to Gmail. Please try again."
            : `Save to Gmail failed (HTTP ${res.status}).`,
        );
        return;
      }
      apply(await res.json());
      setNotice("Saved to Gmail.");
      invalidateLists();
      router.refresh();
    } catch {
      setError("Couldn't reach the API. It may be waking up — try again in ~30s.");
    } finally {
      setBusy(null);
    }
  }

  async function dismiss() {
    if (!draft) return;
    setBusy("dismiss");
    setError(null);
    setNotice(null);
    try {
      const res = await apiFetch(`/drafts/${draft.id}/dismiss`, { method: "POST" });
      if (res.ok) {
        apply(await res.json());
        invalidateLists();
        router.refresh();
      } else {
        setError(`Dismiss failed (HTTP ${res.status}).`);
      }
    } finally {
      setBusy(null);
    }
  }

  return (
    <div className="flex flex-col gap-4">
      <SafetyBanner />

      <div className="grid gap-4 lg:grid-cols-3">
        {/* Source email */}
        <section className="flex flex-col gap-3 rounded-xl border border-border bg-surface p-4">
          <h2 className="text-xs font-semibold uppercase tracking-wide text-ink-soft">
            Source email
          </h2>
          <div className="flex flex-col gap-0.5">
            <span className="text-sm font-medium text-ink">
              {email.from_name || email.from_email || "Unknown sender"}
            </span>
            {email.from_email && (
              <span className="font-mono text-xs text-ink-soft">{email.from_email}</span>
            )}
          </div>
          <p className="text-sm font-medium text-ink">{email.subject || "(no subject)"}</p>
          <div className="max-h-[52vh] overflow-y-auto whitespace-pre-wrap text-sm text-ink-soft">
            {email.body_text || email.subject || "(no content)"}
          </div>
        </section>

        {/* Editable draft */}
        <section className="flex flex-col gap-3 rounded-xl border border-border bg-surface p-4">
          <div className="flex items-center justify-between">
            <h2 className="text-xs font-semibold uppercase tracking-wide text-ink-soft">
              Reply draft
            </h2>
            {draft?.confidence && <ConfidenceBadge confidence={draft.confidence} />}
          </div>

          {draft == null ? (
            <div className="flex flex-1 flex-col items-start justify-center gap-3 py-8">
              <p className="text-sm text-ink-soft">
                No draft yet. Generate a grounded reply from your knowledge base.
              </p>
              <Button onClick={generate} disabled={busy === "generate"}>
                {busy === "generate" ? "Drafting…" : "Generate draft"}
              </Button>
            </div>
          ) : (
            <>
              {draft.confidence === "low" && (
                <p className="rounded-lg border border-border bg-surface-2 px-3 py-2 text-xs text-ink-soft">
                  Grounding was weak — verify the facts before saving.
                </p>
              )}
              <textarea
                value={body}
                onChange={(e) => setBody(e.target.value)}
                disabled={savedToGmail || dismissed}
                rows={14}
                className="w-full flex-1 resize-y rounded-lg border border-border bg-canvas p-3 text-sm text-ink outline-none focus-visible:border-primary disabled:opacity-70"
              />

              {error && <p className="text-sm text-urgent">{error}</p>}
              {notice && <p className="text-sm text-primary">{notice}</p>}

              {dismissed ? (
                <div className="flex flex-wrap items-center gap-3">
                  <span className="text-sm text-ink-soft">
                    This draft was dismissed.
                  </span>
                  <Button onClick={generate} disabled={busy != null}>
                    {busy === "generate" ? "Drafting…" : "Generate new draft"}
                  </Button>
                </div>
              ) : savedToGmail ? (
                <div className="flex flex-wrap items-center gap-3">
                  <span className="inline-flex items-center gap-1.5 rounded-lg bg-primary/10 px-3 py-1.5 text-sm font-medium text-primary">
                    ✓ Saved to your Gmail Drafts
                  </span>
                  <Button variant="outline" onClick={generate} disabled={busy === "generate"}>
                    {busy === "generate" ? "Drafting…" : "Regenerate"}
                  </Button>
                </div>
              ) : (
                <div className="flex flex-wrap items-center gap-2">
                  <Button onClick={saveToGmail} disabled={busy != null}>
                    {busy === "gmail" ? "Saving…" : "Save to Gmail"}
                  </Button>
                  <Button variant="outline" onClick={saveEdit} disabled={busy != null || !dirty}>
                    {busy === "save" ? "Saving…" : "Save changes"}
                  </Button>
                  <Button variant="ghost" onClick={generate} disabled={busy != null}>
                    {busy === "generate" ? "Drafting…" : "Regenerate"}
                  </Button>
                  <Button variant="ghost" onClick={dismiss} disabled={busy != null}>
                    {busy === "dismiss" ? "Dismissing…" : "Dismiss"}
                  </Button>
                </div>
              )}
            </>
          )}
        </section>

        {/* Citations */}
        <section className="flex flex-col gap-3 rounded-xl border border-border bg-surface p-4">
          <h2 className="text-xs font-semibold uppercase tracking-wide text-ink-soft">
            Citations
          </h2>
          {draft == null ? (
            <p className="text-sm text-ink-soft">
              Sources the draft grounds itself in will appear here.
            </p>
          ) : draft.citations.length === 0 ? (
            <p className="text-sm text-ink-soft">
              No sources cited — the draft did not ground itself in your knowledge base.
            </p>
          ) : (
            <ol className="flex flex-col gap-3">
              {draft.citations.map((c, i) => (
                <li key={i} className="flex flex-col gap-1">
                  <span className="text-xs font-medium text-ink">
                    [{i + 1}] {c.filename || "document"}
                    {c.chunk_index != null && (
                      <span className="text-ink-soft"> · chunk {c.chunk_index}</span>
                    )}
                  </span>
                  <blockquote className="border-l-2 border-border pl-3 text-xs text-ink-soft">
                    {c.quote}
                  </blockquote>
                </li>
              ))}
            </ol>
          )}
        </section>
      </div>
    </div>
  );
}

function SafetyBanner() {
  return (
    <div className="flex items-center gap-3 rounded-xl border border-primary/30 bg-primary/5 px-4 py-3">
      <span
        aria-hidden
        className="flex h-6 w-6 shrink-0 items-center justify-center rounded-full bg-primary/15 text-primary"
      >
        🔒
      </span>
      <p className="text-sm text-ink">
        <span className="font-semibold text-primary">This is a draft.</span> Nothing is
        sent without you — Save to Gmail only writes it to your Drafts folder for review.
      </p>
    </div>
  );
}

function ConfidenceBadge({ confidence }: { confidence: string }) {
  const label = confidence.charAt(0).toUpperCase() + confidence.slice(1);
  const styles: Record<string, string> = {
    high: "bg-primary/10 text-primary",
    medium: "bg-surface-2 text-ink",
    low: "bg-surface-2 text-ink-soft",
  };
  return (
    <span
      className={`inline-flex items-center rounded-full px-2 py-0.5 text-xs font-medium ${
        styles[confidence] ?? "bg-surface-2 text-ink-soft"
      }`}
    >
      {label} confidence
    </span>
  );
}
