import { ConnectGmailButton } from "@/components/connect-gmail-button";
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
  priority: string | null;
  status: string;
};

export default async function InboxPage({
  searchParams,
}: {
  searchParams: Promise<{ gmail?: string; reason?: string }>;
}) {
  const params = await searchParams;
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
          Your unread mail, pulled on demand. Nothing here is ever sent for you.
        </p>
      </div>

      <ConnectBanner gmail={params.gmail} reason={params.reason} />

      {!accountsRes.ok ? (
        <ErrorCard message={accountsRes.error} />
      ) : accountsRes.data.length === 0 ? (
        <EmptyConnect />
      ) : (
        <ConnectedInbox account={accountsRes.data[0]} token={token} />
      )}
    </div>
  );
}

async function ConnectedInbox({
  account,
  token,
}: {
  account: Account;
  token: string;
}) {
  const emailsRes = await apiFetch<EmailItem[]>("/emails", token);

  return (
    <div className="flex flex-col gap-4">
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

      {!emailsRes.ok ? (
        <ErrorCard message={emailsRes.error} />
      ) : emailsRes.data.length === 0 ? (
        <div className="rounded-xl border border-dashed border-border bg-surface px-6 py-12 text-center">
          <p className="text-sm font-medium text-ink">No unread mail synced yet</p>
          <p className="mt-1 text-sm text-ink-soft">
            Click <span className="font-medium">Sync inbox</span> to pull your
            latest unread messages.
          </p>
        </div>
      ) : (
        <ul className="overflow-hidden rounded-xl border border-border bg-surface">
          {emailsRes.data.map((email) => (
            <EmailRow key={email.id} email={email} />
          ))}
        </ul>
      )}
    </div>
  );
}

function EmailRow({ email }: { email: EmailItem }) {
  const who = email.from_name || email.from_email || "Unknown sender";
  return (
    <li className="flex flex-col gap-1 border-b border-border px-4 py-3 last:border-b-0">
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
      {email.priority && <PriorityBadge priority={email.priority} />}
    </li>
  );
}

function PriorityBadge({ priority }: { priority: string }) {
  const urgent = priority === "urgent";
  return (
    <span
      className={`mt-1 inline-flex w-fit rounded-full px-2 py-0.5 text-xs font-medium ${
        urgent ? "bg-urgent/10 text-urgent" : "bg-surface-2 text-ink-soft"
      }`}
    >
      {priority}
    </span>
  );
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

function ConnectBanner({
  gmail,
  reason,
}: {
  gmail?: string;
  reason?: string;
}) {
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
