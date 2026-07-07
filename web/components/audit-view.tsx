"use client";

import { useQuery } from "@tanstack/react-query";
import Link from "next/link";

import { Skeleton } from "@/components/ui/skeleton";
import { apiJson } from "@/lib/api-client";
import { actionLabel, relativeTime } from "@/lib/audit";

type AuditEntry = {
  id: string;
  action: string;
  entity_type: string | null;
  entity_id: string | null;
  metadata: Record<string, unknown>;
  created_at: string;
};

const PAGE_SIZE = 50;

export function AuditView({ action, page }: { action?: string; page: number }) {
  const offset = page * PAGE_SIZE;

  const actionsQuery = useQuery({
    queryKey: ["audit", "actions"],
    queryFn: () => apiJson<string[]>("/audit/actions"),
  });

  const entriesQuery = useQuery({
    queryKey: ["audit", "list", action ?? null, page],
    queryFn: () =>
      apiJson<AuditEntry[]>(
        `/audit?limit=${PAGE_SIZE}&offset=${offset}${
          action ? `&action=${encodeURIComponent(action)}` : ""
        }`,
      ),
    placeholderData: (prev) => prev,
  });

  const actions = actionsQuery.data ?? [];
  const entries = entriesQuery.data ?? [];
  const hasNext = entries.length === PAGE_SIZE;

  return (
    <>
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

      {entriesQuery.isError ? (
        <ErrorCard message={(entriesQuery.error as Error).message} />
      ) : entriesQuery.isPending ? (
        <ListSkeleton />
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
    </>
  );
}

function ListSkeleton() {
  return (
    <div className="overflow-hidden rounded-xl border border-border bg-surface">
      {Array.from({ length: 8 }).map((_, i) => (
        <div
          key={i}
          className="flex items-center justify-between gap-4 border-b border-border px-4 py-3 last:border-b-0"
        >
          <div className="flex flex-col gap-1.5">
            <Skeleton className="h-4 w-40" />
            <Skeleton className="h-3 w-24" />
          </div>
          <Skeleton className="h-3 w-16" />
        </div>
      ))}
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
