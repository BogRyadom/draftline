"use client";

import { useQueryClient } from "@tanstack/react-query";
import { useState } from "react";

import { Button } from "@/components/ui/button";
import { apiFetch } from "@/lib/api-client";

/** Synchronous fallback: classify every still-unbadged email now. */
export function ClassifyAllButton() {
  const queryClient = useQueryClient();
  const [loading, setLoading] = useState(false);
  const [message, setMessage] = useState<string | null>(null);

  async function run() {
    setLoading(true);
    setMessage(null);
    try {
      const res = await apiFetch("/emails/classify-unbadged", { method: "POST" });
      if (!res.ok) {
        setMessage(`Failed (HTTP ${res.status}).`);
        return;
      }
      const data: { total: number; classified: number; failed: number } =
        await res.json();
      setMessage(
        data.total === 0
          ? "All caught up"
          : `Classified ${data.classified}${data.failed ? ` · ${data.failed} failed` : ""}`,
      );
      queryClient.invalidateQueries({ queryKey: ["emails"] });
      queryClient.invalidateQueries({ queryKey: ["dashboard"] });
      queryClient.invalidateQueries({ queryKey: ["audit"] });
    } catch {
      setMessage("Couldn't reach the API. It may be waking up — try again in ~30s.");
    } finally {
      setLoading(false);
    }
  }

  return (
    <div className="flex items-center gap-2">
      <Button variant="outline" onClick={run} disabled={loading}>
        {loading ? "Classifying…" : "Classify all"}
      </Button>
      {message && <span className="text-xs text-ink-soft">{message}</span>}
    </div>
  );
}
