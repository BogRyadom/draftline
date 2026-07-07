import Link from "next/link";

import { DraftReview, type Draft, type EmailDetail } from "@/components/draft-review";
import { apiFetch } from "@/lib/api";
import { createClient } from "@/lib/supabase/server";

type Detail = EmailDetail & { draft: Draft | null };

export const metadata = { title: "Review draft · Draftline" };

export default async function EmailReviewPage({
  params,
}: {
  params: Promise<{ id: string }>;
}) {
  const { id } = await params;
  const supabase = await createClient();
  const {
    data: { session },
  } = await supabase.auth.getSession();
  const token = session?.access_token ?? "";

  const res = await apiFetch<Detail>(`/emails/${id}`, token);

  return (
    <div className="flex flex-col gap-5">
      <Link
        href="/app"
        className="text-sm text-ink-soft transition-colors hover:text-ink"
      >
        ← Back to inbox
      </Link>

      {!res.ok ? (
        <div className="rounded-xl border border-urgent/30 bg-urgent/10 px-4 py-3">
          <p className="text-sm font-medium text-urgent">Couldn&rsquo;t load this email</p>
          <p className="mt-1 text-sm text-ink-soft">{res.error}</p>
        </div>
      ) : (
        <>
          <h1 className="font-display text-xl font-semibold tracking-tight text-ink">
            {res.data.subject || "(no subject)"}
          </h1>
          <DraftReview email={res.data} initialDraft={res.data.draft} />
        </>
      )}
    </div>
  );
}
