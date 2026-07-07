"use client";

import { useRouter } from "next/navigation";
import { useMemo, useState } from "react";

import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { apiFetch } from "@/lib/api-client";

export type SettingsValues = {
  categories: string[];
  tone: { formality: string; length: string; signature: string };
  poll_enabled: boolean;
  poll_interval_minutes: number;
  auto_push_drafts: boolean;
};

const FORMALITY = ["casual", "neutral", "formal"];
const LENGTH = ["brief", "concise", "detailed"];
const MAX_CATEGORIES = 20;

export function SettingsForm({ initial }: { initial: SettingsValues }) {
  const router = useRouter();
  const [values, setValues] = useState<SettingsValues>(initial);
  const [categoryDraft, setCategoryDraft] = useState("");
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [notice, setNotice] = useState<string | null>(null);

  const dirty = useMemo(
    () => JSON.stringify(values) !== JSON.stringify(initial),
    [values, initial],
  );

  function patch(next: Partial<SettingsValues>) {
    setValues((v) => ({ ...v, ...next }));
    setNotice(null);
  }

  function addCategory() {
    const name = categoryDraft.trim().slice(0, 40);
    if (!name) return;
    const exists = values.categories.some(
      (c) => c.toLowerCase() === name.toLowerCase(),
    );
    if (exists || values.categories.length >= MAX_CATEGORIES) {
      setCategoryDraft("");
      return;
    }
    patch({ categories: [...values.categories, name] });
    setCategoryDraft("");
  }

  function removeCategory(name: string) {
    patch({ categories: values.categories.filter((c) => c !== name) });
  }

  async function save() {
    if (values.categories.length === 0) {
      setError("Add at least one category.");
      return;
    }
    setBusy(true);
    setError(null);
    setNotice(null);
    try {
      const res = await apiFetch("/settings", {
        method: "PUT",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(values),
      });
      if (!res.ok) {
        setError(
          res.status === 422
            ? "Some values are invalid — check categories and the poll interval."
            : `Couldn't save settings (HTTP ${res.status}).`,
        );
        return;
      }
      setValues(await res.json());
      setNotice("Settings saved.");
      router.refresh();
    } catch {
      setError("Couldn't reach the API. It may be waking up — try again in ~30s.");
    } finally {
      setBusy(false);
    }
  }

  return (
    <div className="flex flex-col gap-5">
      <Section
        title="Categories"
        description="How Draftline sorts your mail. These drive classification and the inbox filters."
      >
        <div className="flex flex-wrap gap-2">
          {values.categories.map((c) => (
            <span
              key={c}
              className="inline-flex items-center gap-1.5 rounded-full border border-border bg-surface-2 py-1 pl-3 pr-1.5 text-sm text-ink"
            >
              {c}
              <button
                type="button"
                onClick={() => removeCategory(c)}
                aria-label={`Remove ${c}`}
                className="flex h-5 w-5 items-center justify-center rounded-full text-ink-soft transition-colors hover:bg-border hover:text-ink"
              >
                ×
              </button>
            </span>
          ))}
          {values.categories.length === 0 && (
            <span className="text-sm text-ink-soft">No categories — add at least one.</span>
          )}
        </div>
        <div className="flex gap-2">
          <Input
            value={categoryDraft}
            onChange={(e) => setCategoryDraft(e.target.value)}
            onKeyDown={(e) => {
              if (e.key === "Enter") {
                e.preventDefault();
                addCategory();
              }
            }}
            placeholder="Add a category"
            maxLength={40}
            className="sm:max-w-xs"
          />
          <Button
            type="button"
            variant="outline"
            onClick={addCategory}
            disabled={!categoryDraft.trim() || values.categories.length >= MAX_CATEGORIES}
          >
            Add
          </Button>
        </div>
      </Section>

      <Section
        title="Tone & signature"
        description="Shapes the voice of generated reply drafts."
      >
        <div className="grid gap-4 sm:grid-cols-2">
          <SelectField
            label="Formality"
            value={values.tone.formality}
            options={FORMALITY}
            onChange={(formality) => patch({ tone: { ...values.tone, formality } })}
          />
          <SelectField
            label="Length"
            value={values.tone.length}
            options={LENGTH}
            onChange={(length) => patch({ tone: { ...values.tone, length } })}
          />
        </div>
        <label className="flex flex-col gap-1.5">
          <span className="text-sm font-medium text-ink">Signature</span>
          <textarea
            value={values.tone.signature}
            onChange={(e) =>
              patch({ tone: { ...values.tone, signature: e.target.value } })
            }
            rows={3}
            maxLength={500}
            placeholder="e.g. Best regards,&#10;Bohdan"
            className="w-full resize-y rounded-lg border border-border bg-surface p-3 text-sm text-ink outline-none placeholder:text-ink-soft/60 focus-visible:border-primary"
          />
          <span className="text-xs text-ink-soft">
            Appended to drafts. Leave blank for none.
          </span>
        </label>
      </Section>

      <Section
        title="Polling"
        description="Optionally re-sync your inbox on a schedule (background polling arrives later; this stores your preference)."
      >
        <Toggle
          checked={values.poll_enabled}
          onChange={(poll_enabled) => patch({ poll_enabled })}
          label="Automatically re-sync my inbox"
        />
        {values.poll_enabled && (
          <label className="flex flex-wrap items-center gap-2 text-sm text-ink">
            Every
            <input
              type="number"
              min={5}
              max={1440}
              value={values.poll_interval_minutes}
              onChange={(e) =>
                patch({
                  poll_interval_minutes: clampInterval(Number(e.target.value)),
                })
              }
              className="h-10 w-20 rounded-lg border border-border bg-surface px-3 text-sm text-ink outline-none focus-visible:border-primary"
            />
            minutes
          </label>
        )}
      </Section>

      <Section
        title="Drafts"
        description="Draftline never sends email. This only controls whether generated drafts are written to your Gmail Drafts automatically."
      >
        <Toggle
          checked={values.auto_push_drafts}
          onChange={(auto_push_drafts) => patch({ auto_push_drafts })}
          label="Auto-save generated drafts to Gmail Drafts"
        />
      </Section>

      <div className="flex flex-wrap items-center gap-3 border-t border-border pt-4">
        <Button onClick={save} disabled={busy || !dirty}>
          {busy ? "Saving…" : "Save settings"}
        </Button>
        {notice && <span className="text-sm text-primary">{notice}</span>}
        {error && <span className="text-sm text-urgent">{error}</span>}
        {!notice && !error && dirty && (
          <span className="text-sm text-ink-soft">Unsaved changes</span>
        )}
      </div>
    </div>
  );
}

function clampInterval(n: number): number {
  if (Number.isNaN(n)) return 15;
  return Math.min(1440, Math.max(5, Math.round(n)));
}

function Section({
  title,
  description,
  children,
}: {
  title: string;
  description: string;
  children: React.ReactNode;
}) {
  return (
    <section className="flex flex-col gap-3 rounded-xl border border-border bg-surface p-5">
      <div className="flex flex-col gap-1">
        <h2 className="text-sm font-semibold text-ink">{title}</h2>
        <p className="max-w-prose text-sm text-ink-soft">{description}</p>
      </div>
      {children}
    </section>
  );
}

function SelectField({
  label,
  value,
  options,
  onChange,
}: {
  label: string;
  value: string;
  options: string[];
  onChange: (value: string) => void;
}) {
  return (
    <label className="flex flex-col gap-1.5">
      <span className="text-sm font-medium text-ink">{label}</span>
      <select
        value={value}
        onChange={(e) => onChange(e.target.value)}
        className="h-10 w-full rounded-lg border border-border bg-surface px-3 text-sm capitalize text-ink outline-none focus-visible:border-primary"
      >
        {options.map((opt) => (
          <option key={opt} value={opt} className="capitalize">
            {opt}
          </option>
        ))}
      </select>
    </label>
  );
}

function Toggle({
  checked,
  onChange,
  label,
}: {
  checked: boolean;
  onChange: (checked: boolean) => void;
  label: string;
}) {
  return (
    <button
      type="button"
      role="switch"
      aria-checked={checked}
      onClick={() => onChange(!checked)}
      className="flex items-center gap-3 text-left"
    >
      <span
        className={`relative inline-flex h-6 w-11 shrink-0 items-center rounded-full transition-colors ${
          checked ? "bg-primary" : "bg-surface-2"
        }`}
      >
        <span
          className={`inline-block h-5 w-5 rounded-full bg-surface shadow-sm transition-transform ${
            checked ? "translate-x-5" : "translate-x-0.5"
          }`}
        />
      </span>
      <span className="text-sm text-ink">{label}</span>
    </button>
  );
}
