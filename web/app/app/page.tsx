import Link from "next/link";

import { AutoRefresh } from "@/components/auto-refresh";
import { ConnectGmailButton } from "@/components/connect-gmail-button";
import { ReclassifyButton } from "@/components/reclassify-button";
import { SyncButton } from "@/components/sync-button";
import { apiFetch } from "@/lib/api";
import { createClient } from "@/lib/supabase/server";

type Account = {
  id: string;
  provider: string;
  email_address: string;
  status: string;
  last_synced_at: string | null;
  created_at: string;
};

type EmailItem = {
  id: string;
  from_name: string | null;
  from_email: string | null;
  subject: string | null;
  snippet: string | null;
  received_at: string | null;
  category: string | null;
  priority: string | null;
  classification_reason: string | null;
  status: string;
};

type Settings = { categories: string[] };

type Filters = { category?: string; priority?: string; sort?: string };

const PRIORITIES = ["urgent", "high", "normal", "low"];

export default async function InboxPage({
  searchParams,
}: {
  searchParams: Promise<{
    gmail?: string;
    reason?: string;
    category?: string;
    priority?: string;
    sort?: string;
  }>;
}) {
  const params = await searchParams;
  const filters: Filters = {
    category: params.category,
    priority: params.priority,
    sort: params.sort,
  };

  const supabase = await createClient();
  const {
    data: { session },
  } = await supabase.auth.getSession();
  const token = session?.access_token ?? "";

  const accountsRes = await apiFetch<Account[]>("/accounts", token);

  return (
    <div className="flex flex-col gap-6">
      <div className="flex flex-col gap-1.5">
        <h1 className="font-display text-2xl font-semibold tracking-tight text-ink">
          Inbox
        </h1>
        <p className="text-sm text-ink-soft">
          Your unread mail, classified and prioritized. Nothing here is ever sent
          for you.
        </p>
      </div>

      <ConnectBanner gmail={params.gmail} reason={params.reason} />

      {!accountsRes.ok ? (
        <ErrorCard message={accountsRes.error} />
      ) : accountsRes.data.length === 0 ? (
        <EmptyConnect />
      ) : (
        <ConnectedInbox
          account={accountsRes.data[0]}
          token={token}
          filters={filters}
        />
      )}
    </div>
  );
}

async function ConnectedInbox({
  account,
  token,
  filters,
}: {
  account: Account;
  token: string;
  filters: Filters;
}) {
  const settingsRes = await apiFetch<Settings>("/settings", token);
  const categories = settingsRes.ok ? settingsRes.data.categories : [];

  const query = new URLSearchParams();
  if (filters.category) query.set("category", filters.category);
  if (filters.priority) query.set("priority", filters.priority);
  if (filters.sort === "priority") query.set("sort", "priority");
  const emailsRes = await apiFetch<EmailItem[]>(
    `/emails${query.toString() ? `?${query}` : ""}`,
    token,
  );
  const emails = emailsRes.ok ? emailsRes.data : [];
  const pending = emails.some((e) => e.status === "new" && !e.category);
  const filtersActive = Boolean(filters.category || filters.priority);

  return (
    <div className="flex flex-col gap-4">
      {/* Keep polling while new emails are still being classified. */}
      <AutoRefresh active={pending} />

      <div className="flex flex-wrap items-center justify-between gap-4 rounded-xl border border-border bg-surface px-4 py-3">
        <div className="flex flex-col">
          <span className="text-sm font-medium text-ink">
            {account.email_address}
          </span>
          <span className="text-xs text-ink-soft">
            {account.status === "connected" ? "Connected" : account.status} ·{" "}
            {account.last_synced_at
              ? `last synced ${formatDate(account.last_synced_at)}`
              : "not synced yet"}
          </span>
        </div>
        <SyncButton accountId={account.id} />
      </div>

      <FilterBar filters={filters} categories={categories} />

      {!emailsRes.ok ? (
        <ErrorCard message={emailsRes.error} />
      ) : emails.length === 0 ? (
        <div className="rounded-xl border border-dashed border-border bg-surface px-6 py-12 text-center">
          <p className="text-sm font-medium text-ink">
            {filtersActive ? "No emails match these filters" : "No unread mail synced yet"}
          </p>
          <p className="mt-1 text-sm text-ink-soft">
            {filtersActive ? (
              <Link href="/app" className="font-medium text-primary hover:underline">
                Clear filters
              </Link>
            ) : (
              <>
                Click <span className="font-medium">Sync inbox</span> to pull your
                latest unread messages.
              </>
            )}
          </p>
        </div>
      ) : (
        <ul className="overflow-hidden rounded-xl border border-border bg-surface">
          {emails.map((email) => (
            <EmailRow key={email.id} email={email} />
          ))}
        </ul>
      )}
    </div>
  );
}

function EmailRow({ email }: { email: EmailItem }) {
  const who = email.from_name || email.from_email || "Unknown sender";
  const classifying = email.status === "new" && !email.category;
  return (
    <li className="flex flex-col gap-1.5 border-b border-border px-4 py-3 last:border-b-0">
      <div className="flex items-baseline justify-between gap-4">
        <span className="truncate text-sm font-medium text-ink">{who}</span>
        <span className="shrink-0 font-mono text-xs text-ink-soft">
          {formatDate(email.received_at)}
        </span>
      </div>
      <span className="truncate text-sm text-ink">
        {email.subject || "(no subject)"}
      </span>
      {email.snippet && (
        <span className="line-clamp-1 text-sm text-ink-soft">{email.snippet}</span>
      )}
      <div className="mt-0.5 flex flex-wrap items-center gap-2">
        {classifying ? (
          <span className="inline-flex items-center gap-1.5 rounded-full bg-surface-2 px-2 py-0.5 text-xs text-ink-soft">
            <span
              aria-hidden
              className="h-1.5 w-1.5 animate-pulse rounded-full bg-ink-soft"
            />
            Classifying…
          </span>
        ) : (
          <>
            {email.category && <CategoryBadge category={email.category} />}
            {email.priority && <PriorityBadge priority={email.priority} />}
          </>
        )}
        <span className="ml-auto">
          <ReclassifyButton emailId={email.id} />
        </span>
      </div>
      {email.classification_reason && (
        <span className="line-clamp-1 text-xs text-ink-soft/80">
          {email.classification_reason}
        </span>
      )}
    </li>
  );
}

function CategoryBadge({ category }: { category: string }) {
  return (
    <span className="inline-flex rounded-full bg-surface-2 px-2 py-0.5 text-xs font-medium text-ink-soft">
      {category}
    </span>
  );
}

function PriorityBadge({ priority }: { priority: string }) {
  // Only `urgent` gets the warm signal color; the rest stay calm.
  const styles: Record<string, string> = {
    urgent: "bg-urgent/10 text-urgent",
    high: "bg-surface-2 text-ink",
    normal: "bg-surface-2 text-ink-soft",
    low: "bg-surface-2 text-ink-soft",
  };
  return (
    <span
      className={`inline-flex items-center gap-1 rounded-full px-2 py-0.5 text-xs font-medium ${
        styles[priority] ?? "bg-surface-2 text-ink-soft"
      }`}
    >
      {priority === "urgent" && (
        <span aria-hidden className="h-1.5 w-1.5 rounded-full bg-urgent" />
      )}
      {priority}
    </span>
  );
}

function FilterBar({
  filters,
  categories,
}: {
  filters: Filters;
  categories: string[];
}) {
  return (
    <div className="flex flex-col gap-2.5">
      <FilterRow label="Category">
        <Chip href={hrefWith(filters, { category: "" })} active={!filters.category}>
          All
        </Chip>
        {categories.map((c) => (
          <Chip
            key={c}
            href={hrefWith(filters, { category: c })}
            active={filters.category === c}
          >
            {c}
          </Chip>
        ))}
      </FilterRow>
      <FilterRow label="Priority">
        <Chip href={hrefWith(filters, { priority: "" })} active={!filters.priority}>
          All
        </Chip>
        {PRIORITIES.map((p) => (
          <Chip
            key={p}
            href={hrefWith(filters, { priority: p })}
            active={filters.priority === p}
          >
            {p}
          </Chip>
        ))}
      </FilterRow>
      <FilterRow label="Sort">
        <Chip
          href={hrefWith(filters, { sort: "received" })}
          active={filters.sort !== "priority"}
        >
          Newest
        </Chip>
        <Chip
          href={hrefWith(filters, { sort: "priority" })}
          active={filters.sort === "priority"}
        >
          Priority
        </Chip>
      </FilterRow>
    </div>
  );
}

function FilterRow({
  label,
  children,
}: {
  label: string;
  children: React.ReactNode;
}) {
  return (
    <div className="flex flex-wrap items-center gap-2">
      <span className="w-16 text-xs font-medium text-ink-soft">{label}</span>
      {children}
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

function hrefWith(current: Filters, patch: Filters): string {
  const next = { ...current, ...patch };
  const sp = new URLSearchParams();
  if (next.category) sp.set("category", next.category);
  if (next.priority) sp.set("priority", next.priority);
  if (next.sort && next.sort !== "received") sp.set("sort", next.sort);
  const qs = sp.toString();
  return qs ? `/app?${qs}` : "/app";
}

function EmptyConnect() {
  return (
    <div className="flex flex-col items-start gap-4 rounded-xl border border-border bg-surface px-6 py-10">
      <div className="flex flex-col gap-1.5">
        <h2 className="text-base font-semibold text-ink">Connect your Gmail</h2>
        <p className="max-w-prose text-sm text-ink-soft">
          Draftline reads your unread mail so it can classify, prioritize, and
          draft replies for your review. It requests read and draft access only —
          there is no send permission.
        </p>
      </div>
      <ConnectGmailButton />
      <p className="text-xs text-ink-soft">
        The demo OAuth app is in Google&rsquo;s testing mode; your account must be
        added as a test user.
      </p>
    </div>
  );
}

function ConnectBanner({ gmail, reason }: { gmail?: string; reason?: string }) {
  if (gmail === "connected") {
    return (
      <p className="rounded-xl border border-primary/25 bg-primary/5 px-4 py-3 text-sm text-ink">
        <span className="font-medium text-primary">Gmail connected.</span> Click{" "}
        <span className="font-medium">Sync inbox</span> to pull your unread mail.
      </p>
    );
  }
  if (gmail === "error") {
    return (
      <p className="rounded-xl border border-urgent/30 bg-urgent/10 px-4 py-3 text-sm text-urgent">
        Couldn&rsquo;t connect Gmail
        {reason === "norefresh"
          ? " — Google didn't grant offline access. Try again and approve all prompts."
          : ". Please try connecting again."}
      </p>
    );
  }
  return null;
}

function ErrorCard({ message }: { message: string }) {
  return (
    <div className="rounded-xl border border-urgent/30 bg-urgent/10 px-4 py-3">
      <p className="text-sm font-medium text-urgent">Couldn&rsquo;t load your inbox</p>
      <p className="mt-1 text-sm text-ink-soft">{message}</p>
    </div>
  );
}

function formatDate(iso: string | null): string {
  if (!iso) return "—";
  return new Date(iso).toLocaleString("en-US", {
    month: "short",
    day: "numeric",
    hour: "numeric",
    minute: "2-digit",
  });
}
