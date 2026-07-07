"use client";

import { useQueryClient } from "@tanstack/react-query";
import { useState } from "react";

import { Button } from "@/components/ui/button";
import { apiFetch } from "@/lib/api-client";

export function SyncButton({ accountId }: { accountId: string }) {
  const queryClient = useQueryClient();
  const [loading, setLoading] = useState(false);
  const [message, setMessage] = useState<string | null>(null);
  const [error, setError] = useState<string | null>(null);

  async function sync() {
    setLoading(true);
    setError(null);
    setMessage(null);
    try {
      const res = await apiFetch(`/accounts/${accountId}/sync`, { method: "POST" });
      if (!res.ok) {
        setError(
          res.status === 502
            ? "Gmail sync failed — try reconnecting the account."
            : `Sync failed (HTTP ${res.status}).`,
        );
        return;
      }
      const data: { fetched: number; new: number } = await res.json();
      setMessage(
        data.new > 0
          ? `Synced ${data.fetched} · ${data.new} new`
          : `Synced ${data.fetched} · up to date`,
      );
      // New mail + background classification affect these surfaces.
      queryClient.invalidateQueries({ queryKey: ["emails"] });
      queryClient.invalidateQueries({ queryKey: ["accounts"] });
      queryClient.invalidateQueries({ queryKey: ["dashboard"] });
      queryClient.invalidateQueries({ queryKey: ["audit"] });
    } catch {
      setError("Couldn't reach the API. It may be waking up — try again in ~30s.");
    } finally {
      setLoading(false);
    }
  }

  return (
    <div className="flex items-center gap-3">
      <Button onClick={sync} disabled={loading}>
        {loading ? "Syncing…" : "Sync inbox"}
      </Button>
      {message && <span className="text-sm text-ink-soft">{message}</span>}
      {error && <span className="text-sm text-urgent">{error}</span>}
    </div>
  );
}
