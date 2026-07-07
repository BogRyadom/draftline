import Link from "next/link";

import { actionLabel, relativeTime } from "@/lib/audit";
import { apiFetch } from "@/lib/api";
import { createClient } from "@/lib/supabase/server";

type AuditEntry = {
  id: string;
  action: string;
  entity_type: string | null;
  entity_id: string | null;
  metadata: Record<string, unknown>;
  created_at: string;
};

const PAGE_SIZE = 50;

export const metadata = { title: "Audit log · Draftline" };

export default async function AuditPage({
  searchParams,
}: {
  searchParams: Promise<{ action?: string; page?: string }>;
}) {
  const params = await searchParams;
  const action = params.action;
  const page = Math.max(0, Number.parseInt(params.page ?? "0", 10) || 0);
  const offset = page * PAGE_SIZE;

  const supabase = await createClient();
  const {
    data: { session },
  } = await supabase.auth.getSession();
  const token = session?.access_token ?? "";

  const [actionsRes, entriesRes] = await Promise.all([
    apiFetch<string[]>("/audit/actions", token),
    apiFetch<AuditEntry[]>(
      `/audit?limit=${PAGE_SIZE}&offset=${offset}${
        action ? `&action=${encodeURIComponent(action)}` : ""
      }`,
      token,
    ),
  ]);

  const actions = actionsRes.ok ? actionsRes.data : [];
  const entries = entriesRes.ok ? entriesRes.data : [];
  const hasNext = entries.length === PAGE_SIZE;

  return (
    <div className="flex flex-col gap-6">
      <div className="flex flex-col gap-1.5">
        <h1 className="font-display text-2xl font-semibold tracking-tight text-ink">
          Audit log
        </h1>
        <p className="text-sm text-ink-soft">
          A complete, timestamped record of what Draftline did — every connect,
          sync, classification, draft, and save.
        </p>
      </div>

      {actions.length > 0 && (
        <div className="flex flex-wrap items-center gap-2">
          <span className="w-16 text-xs font-medium text-ink-soft">Action</span>
          <Chip href="/app/audit" active={!action}>
            All
          </Chip>
          {actions.map((a) => (
            <Chip
              key={a}
              href={`/app/audit?action=${encodeURIComponent(a)}`}
              active={action === a}
            >
              {actionLabel(a)}
            </Chip>
          ))}
        </div>
      )}

      {!entriesRes.ok ? (
        <ErrorCard message={entriesRes.error} />
      ) : entries.length === 0 ? (
        <div className="rounded-xl border border-dashed border-border bg-surface px-6 py-12 text-center">
          <p className="text-sm font-medium text-ink">
            {action ? "No entries for this action" : "No activity recorded yet"}
          </p>
          <p className="mt-1 text-sm text-ink-soft">
            {action ? (
              <Link href="/app/audit" className="font-medium text-primary hover:underline">
                Clear filter
              </Link>
            ) : (
              "Connect Gmail and sync your inbox — actions will appear here as they happen."
            )}
          </p>
        </div>
      ) : (
        <>
          <ul className="overflow-hidden rounded-xl border border-border bg-surface">
            {entries.map((entry) => (
              <AuditRow key={entry.id} entry={entry} />
            ))}
          </ul>
          <Pagination action={action} page={page} hasNext={hasNext} />
        </>
      )}
    </div>
  );
}

function AuditRow({ entry }: { entry: AuditEntry }) {
  return (
    <li className="flex items-center justify-between gap-4 border-b border-border px-4 py-3 last:border-b-0">
      <div className="flex min-w-0 items-center gap-3">
        <span aria-hidden className="h-1.5 w-1.5 shrink-0 rounded-full bg-primary" />
        <div className="flex min-w-0 flex-col">
          <span className="truncate text-sm font-medium text-ink">
            {actionLabel(entry.action)}
          </span>
          <MetadataLine entry={entry} />
        </div>
      </div>
      <time
        dateTime={entry.created_at}
        title={new Date(entry.created_at).toLocaleString()}
        className="shrink-0 font-mono text-xs text-ink-soft"
      >
        {relativeTime(entry.created_at)}
      </time>
    </li>
  );
}

function MetadataLine({ entry }: { entry: AuditEntry }) {
  const parts: string[] = [];
  if (entry.entity_type) parts.push(entry.entity_type);
  const m = entry.metadata ?? {};
  for (const key of ["filename", "email", "category", "priority"]) {
    if (typeof m[key] === "string" && m[key]) parts.push(m[key] as string);
  }
  if (entry.action === "sync_run" && typeof m.new === "number") {
    parts.push(`${m.new} new of ${m.fetched ?? "?"}`);
  }
  if (parts.length === 0) return null;
  return (
    <span className="truncate font-mono text-xs text-ink-soft">
      {parts.join(" · ")}
    </span>
  );
}

function Pagination({
  action,
  page,
  hasNext,
}: {
  action?: string;
  page: number;
  hasNext: boolean;
}) {
  const base = action ? `?action=${encodeURIComponent(action)}&` : "?";
  if (page === 0 && !hasNext) return null;
  return (
    <div className="flex items-center justify-between gap-4">
      {page > 0 ? (
        <Link
          href={`/app/audit${base}page=${page - 1}`}
          className="rounded-lg border border-border bg-surface px-3 py-1.5 text-sm font-medium text-ink hover:bg-surface-2"
        >
          ← Newer
        </Link>
      ) : (
        <span />
      )}
      <span className="font-mono text-xs text-ink-soft">Page {page + 1}</span>
      {hasNext ? (
        <Link
          href={`/app/audit${base}page=${page + 1}`}
          className="rounded-lg border border-border bg-surface px-3 py-1.5 text-sm font-medium text-ink hover:bg-surface-2"
        >
          Older →
        </Link>
      ) : (
        <span />
      )}
    </div>
  );
}

function Chip({
  href,
  active,
  children,
}: {
  href: string;
  active: boolean;
  children: React.ReactNode;
}) {
  return (
    <Link
      href={href}
      className={`rounded-full border px-2.5 py-0.5 text-xs font-medium transition-colors ${
        active
          ? "border-primary bg-primary/10 text-primary"
          : "border-border bg-surface text-ink-soft hover:bg-surface-2"
      }`}
    >
      {children}
    </Link>
  );
}

function ErrorCard({ message }: { message: string }) {
  return (
    <div className="rounded-xl border border-urgent/30 bg-urgent/10 px-4 py-3">
      <p className="text-sm font-medium text-urgent">Couldn&rsquo;t load the audit log</p>
      <p className="mt-1 text-sm text-ink-soft">{message}</p>
    </div>
  );
}
