"use client";

import { useRouter } from "next/navigation";
import { useState } from "react";

import { apiFetch } from "@/lib/api-client";

export function ReclassifyButton({ emailId }: { emailId: string }) {
  const router = useRouter();
  const [loading, setLoading] = useState(false);

  async function run() {
    setLoading(true);
    try {
      const res = await apiFetch(`/emails/${emailId}/classify`, { method: "POST" });
      if (res.ok) router.refresh();
    } finally {
      setLoading(false);
    }
  }

  return (
    <button
      type="button"
      onClick={run}
      disabled={loading}
      className="rounded px-1.5 py-0.5 text-xs text-ink-soft transition-colors hover:text-primary disabled:opacity-60"
    >
      {loading ? "Classifying…" : "Re-classify"}
    </button>
  );
}
