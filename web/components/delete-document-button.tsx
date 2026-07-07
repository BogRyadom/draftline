"use client";

import { useRouter } from "next/navigation";
import { useState } from "react";

import { apiFetch } from "@/lib/api-client";

export function DeleteDocumentButton({
  documentId,
  filename,
}: {
  documentId: string;
  filename: string;
}) {
  const router = useRouter();
  const [loading, setLoading] = useState(false);

  async function onDelete() {
    if (
      !window.confirm(
        `Delete "${filename}"? This removes its chunks from the knowledge base.`,
      )
    ) {
      return;
    }
    setLoading(true);
    try {
      const res = await apiFetch(`/documents/${documentId}`, { method: "DELETE" });
      if (res.ok || res.status === 204) router.refresh();
    } finally {
      setLoading(false);
    }
  }

  return (
    <button
      type="button"
      onClick={onDelete}
      disabled={loading}
      className="rounded px-1.5 py-0.5 text-xs text-ink-soft transition-colors hover:text-urgent disabled:opacity-60"
    >
      {loading ? "Deleting…" : "Delete"}
    </button>
  );
}
