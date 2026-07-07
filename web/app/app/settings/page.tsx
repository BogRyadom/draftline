import { SettingsForm, type SettingsValues } from "@/components/settings-form";
import { apiFetch } from "@/lib/api";
import { createClient } from "@/lib/supabase/server";

export const metadata = { title: "Settings · Draftline" };

export default async function SettingsPage() {
  const supabase = await createClient();
  const {
    data: { session },
  } = await supabase.auth.getSession();
  const token = session?.access_token ?? "";

  const res = await apiFetch<SettingsValues>("/settings", token);

  return (
    <div className="flex flex-col gap-6">
      <div className="flex flex-col gap-1.5">
        <h1 className="font-display text-2xl font-semibold tracking-tight text-ink">
          Settings
        </h1>
        <p className="text-sm text-ink-soft">
          Tune how Draftline classifies your mail and drafts replies. Changes take
          effect on the next classification or draft.
        </p>
      </div>

      {!res.ok ? (
        <div className="rounded-xl border border-urgent/30 bg-urgent/10 px-4 py-3">
          <p className="text-sm font-medium text-urgent">Couldn&rsquo;t load your settings</p>
          <p className="mt-1 text-sm text-ink-soft">{res.error}</p>
        </div>
      ) : (
        <SettingsForm initial={res.data} />
      )}
    </div>
  );
}
