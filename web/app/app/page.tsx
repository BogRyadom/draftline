import { apiFetch } from "@/lib/api";
import { createClient } from "@/lib/supabase/server";

type Me = { id: string; email: string | null };

export default async function AppHome() {
  const supabase = await createClient();
  const {
    data: { user },
  } = await supabase.auth.getUser();
  const {
    data: { session },
  } = await supabase.auth.getSession();

  const token = session?.access_token;
  const result = token
    ? await apiFetch<Me>("/me", token)
    : ({ ok: false, error: "No active session token." } as const);

  return (
    <div className="flex flex-col gap-8">
      <div className="flex flex-col gap-1.5">
        <h1 className="font-display text-2xl font-semibold tracking-tight text-ink">
          You&rsquo;re signed in
        </h1>
        <p className="text-sm text-ink-soft">
          Phase&nbsp;0 checkpoint — the authenticated round-trip is working.
        </p>
      </div>

      <div className="grid gap-4 sm:grid-cols-2">
        {/* Identity from Supabase Auth. */}
        <section className="rounded-xl border border-border bg-surface p-5">
          <h2 className="text-sm font-semibold text-ink">Your account</h2>
          <dl className="mt-3 flex flex-col gap-2 text-sm">
            <div className="flex justify-between gap-4">
              <dt className="text-ink-soft">Email</dt>
              <dd className="text-ink">{user?.email}</dd>
            </div>
            <div className="flex justify-between gap-4">
              <dt className="text-ink-soft">User ID</dt>
              <dd className="truncate font-mono text-xs text-ink">{user?.id}</dd>
            </div>
          </dl>
        </section>

        {/* Proof the frontend called the API with the JWT. */}
        <section className="rounded-xl border border-border bg-surface p-5">
          <div className="flex items-center justify-between">
            <h2 className="text-sm font-semibold text-ink">
              API round-trip
              <span className="ml-2 font-mono text-xs text-ink-soft">
                GET /me
              </span>
            </h2>
            <span
              className={`inline-flex items-center gap-1.5 rounded-full px-2 py-0.5 text-xs font-medium ${
                result.ok
                  ? "bg-primary/10 text-primary"
                  : "bg-urgent/10 text-urgent"
              }`}
            >
              <span
                aria-hidden
                className={`h-1.5 w-1.5 rounded-full ${
                  result.ok ? "bg-primary" : "bg-urgent"
                }`}
              />
              {result.ok ? "Verified" : "Unavailable"}
            </span>
          </div>

          {result.ok ? (
            <pre className="mt-3 overflow-x-auto rounded-lg bg-surface-2 p-3 font-mono text-xs text-ink">
              {JSON.stringify(result.data, null, 2)}
            </pre>
          ) : (
            <p className="mt-3 text-sm text-ink-soft">{result.error}</p>
          )}
        </section>
      </div>

      {/* Product ethos, present from day one. */}
      <p className="rounded-xl border border-primary/25 bg-primary/5 px-4 py-3 text-sm text-ink">
        <span className="font-medium text-primary">
          Draftline never sends email.
        </span>{" "}
        Once you connect an inbox, replies are drafted for your review and only
        saved to Gmail when you say so.
      </p>

      <section className="flex flex-col gap-2">
        <h2 className="text-sm font-semibold text-ink">What&rsquo;s next</h2>
        <p className="text-sm text-ink-soft">
          Connecting a Gmail account and syncing your inbox arrives in Phase&nbsp;1.
        </p>
      </section>
    </div>
  );
}
