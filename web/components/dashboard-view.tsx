"use client";

import { useQuery } from "@tanstack/react-query";
import Link from "next/link";

import { Skeleton } from "@/components/ui/skeleton";
import { apiJson } from "@/lib/api-client";
import { actionLabel, relativeTime } from "@/lib/audit";

type CountItem = { label: string; count: number };

type ActivityItem = {
  action: string;
  entity_type: string | null;
  entity_id: string | null;
  metadata: Record<string, unknown>;
  created_at: string;
};

type Stats = {
  emails_total: number;
  emails_classified: number;
  emails_unclassified: number;
  by_category: CountItem[];
  by_priority: CountItem[];
  drafts_pending: number;
  drafts_saved: number;
  drafts_dismissed: number;
  documents_total: number;
  documents_ready: number;
  recent_activity: ActivityItem[];
};

export function DashboardView() {
  const { data, isPending, isError, error } = useQuery({
    queryKey: ["dashboard", "stats"],
    queryFn: () => apiJson<Stats>("/dashboard/stats"),
  });

  if (isError) return <ErrorCard message={(error as Error).message} />;
  if (isPending) return <DashboardSkeleton />;
  return <Overview stats={data} />;
}

function DashboardSkeleton() {
  return (
    <div className="flex flex-col gap-6">
      <div className="grid grid-cols-2 gap-3 sm:grid-cols-3 lg:grid-cols-5">
        {Array.from({ length: 5 }).map((_, i) => (
          <Skeleton key={i} className="h-24 w-full" />
        ))}
      </div>
      <div className="grid grid-cols-1 gap-4 lg:grid-cols-2">
        <Skeleton className="h-48 w-full" />
        <Skeleton className="h-48 w-full" />
      </div>
      <Skeleton className="h-64 w-full" />
    </div>
  );
}

function Overview({ stats }: { stats: Stats }) {
  const nothingYet =
    stats.emails_total === 0 &&
    stats.documents_total === 0 &&
    stats.recent_activity.length === 0;

  if (nothingYet) {
    return (
      <div className="rounded-xl border border-dashed border-border bg-surface px-6 py-12 text-center">
        <p className="text-sm font-medium text-ink">Nothing to show yet</p>
        <p className="mx-auto mt-1 max-w-prose text-sm text-ink-soft">
          Connect Gmail and sync your inbox, then upload a document or two. As
          Draftline classifies mail and drafts replies, your activity shows up here.
        </p>
        <div className="mt-4 flex flex-wrap justify-center gap-3">
          <Link
            href="/app"
            className="rounded-lg bg-primary px-4 py-2 text-sm font-medium text-primary-fg hover:bg-primary-hover"
          >
            Go to inbox
          </Link>
          <Link
            href="/app/knowledge"
            className="rounded-lg border border-border bg-surface px-4 py-2 text-sm font-medium text-ink hover:bg-surface-2"
          >
            Upload documents
          </Link>
        </div>
      </div>
    );
  }

  return (
    <div className="flex flex-col gap-6">
      <div className="grid grid-cols-2 gap-3 sm:grid-cols-3 lg:grid-cols-5">
        <StatTile label="Emails synced" value={stats.emails_total} />
        <StatTile
          label="Classified"
          value={stats.emails_classified}
          sub={
            stats.emails_unclassified > 0
              ? `${stats.emails_unclassified} pending`
              : "all done"
          }
        />
        <StatTile
          label="Drafts to review"
          value={stats.drafts_pending}
          accent={stats.drafts_pending > 0}
        />
        <StatTile label="Saved to Gmail" value={stats.drafts_saved} />
        <StatTile
          label="Documents ready"
          value={stats.documents_ready}
          sub={
            stats.documents_total > stats.documents_ready
              ? `${stats.documents_total - stats.documents_ready} processing`
              : undefined
          }
        />
      </div>

      <div className="grid grid-cols-1 gap-4 lg:grid-cols-2">
        <Panel title="By category">
          <BreakdownBars items={stats.by_category} empty="No emails classified yet." />
        </Panel>
        <Panel title="By priority">
          <BreakdownBars
            items={stats.by_priority}
            empty="No priorities assigned yet."
            highlight="urgent"
          />
        </Panel>
      </div>

      <Panel
        title="Recent activity"
        action={
          <Link
            href="/app/audit"
            className="text-xs font-medium text-primary underline-offset-2 hover:underline"
          >
            View all →
          </Link>
        }
      >
        {stats.recent_activity.length === 0 ? (
          <p className="text-sm text-ink-soft">No activity recorded yet.</p>
        ) : (
          <ul className="flex flex-col">
            {stats.recent_activity.map((item, i) => (
              <li
                key={`${item.created_at}-${i}`}
                className="flex items-center justify-between gap-4 border-b border-border py-2.5 last:border-b-0"
              >
                <span className="truncate text-sm text-ink">
                  {actionLabel(item.action)}
                  <ActivityDetail item={item} />
                </span>
                <span className="shrink-0 font-mono text-xs text-ink-soft">
                  {relativeTime(item.created_at)}
                </span>
              </li>
            ))}
          </ul>
        )}
      </Panel>
    </div>
  );
}

function ActivityDetail({ item }: { item: ActivityItem }) {
  const m = item.metadata ?? {};
  const detail =
    (typeof m.filename === "string" && m.filename) ||
    (typeof m.category === "string" && m.category) ||
    (typeof m.email === "string" && m.email) ||
    (item.action === "sync_run" && typeof m.new === "number"
      ? `${m.new} new`
      : null);
  if (!detail) return null;
  return <span className="text-ink-soft"> · {detail}</span>;
}

function StatTile({
  label,
  value,
  sub,
  accent,
}: {
  label: string;
  value: number;
  sub?: string;
  accent?: boolean;
}) {
  return (
    <div className="flex flex-col gap-1 rounded-xl border border-border bg-surface p-4">
      <span className="text-xs font-medium uppercase tracking-wide text-ink-soft">
        {label}
      </span>
      <span
        className={`font-display text-2xl font-semibold tabular-nums ${
          accent ? "text-primary" : "text-ink"
        }`}
      >
        {value}
      </span>
      {sub && <span className="text-xs text-ink-soft">{sub}</span>}
    </div>
  );
}

function Panel({
  title,
  action,
  children,
}: {
  title: string;
  action?: React.ReactNode;
  children: React.ReactNode;
}) {
  return (
    <section className="rounded-xl border border-border bg-surface p-5">
      <div className="mb-3 flex items-center justify-between gap-4">
        <h2 className="text-sm font-semibold text-ink">{title}</h2>
        {action}
      </div>
      {children}
    </section>
  );
}

function BreakdownBars({
  items,
  empty,
  highlight,
}: {
  items: CountItem[];
  empty: string;
  highlight?: string;
}) {
  if (items.length === 0) {
    return <p className="text-sm text-ink-soft">{empty}</p>;
  }
  const max = Math.max(...items.map((i) => i.count), 1);
  return (
    <ul className="flex flex-col gap-2.5">
      {items.map((item) => {
        const isHot = highlight && item.label === highlight;
        return (
          <li key={item.label} className="flex items-center gap-3">
            <span className="w-24 truncate text-sm text-ink" title={item.label}>
              {item.label}
            </span>
            <div className="h-2 flex-1 overflow-hidden rounded-full bg-surface-2">
              <div
                className={`h-full rounded-full ${isHot ? "bg-urgent" : "bg-primary"}`}
                style={{ width: `${(item.count / max) * 100}%` }}
              />
            </div>
            <span className="w-8 shrink-0 text-right font-mono text-xs text-ink-soft tabular-nums">
              {item.count}
            </span>
          </li>
        );
      })}
    </ul>
  );
}

function ErrorCard({ message }: { message: string }) {
  return (
    <div className="rounded-xl border border-urgent/30 bg-urgent/10 px-4 py-3">
      <p className="text-sm font-medium text-urgent">Couldn&rsquo;t load your dashboard</p>
      <p className="mt-1 text-sm text-ink-soft">{message}</p>
    </div>
  );
}
