"use client";

import { useRouter } from "next/navigation";
import { useRef, useState } from "react";

import { Button } from "@/components/ui/button";
import { apiFetch } from "@/lib/api-client";

export function UploadDocument() {
  const router = useRouter();
  const inputRef = useRef<HTMLInputElement>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  async function onChange(e: React.ChangeEvent<HTMLInputElement>) {
    const file = e.target.files?.[0];
    if (!file) return;
    setLoading(true);
    setError(null);
    try {
      const form = new FormData();
      form.append("file", file);
      const res = await apiFetch("/documents", { method: "POST", body: form });
      if (!res.ok) {
        setError(
          res.status === 415
            ? "Only PDF and DOCX files are supported."
            : res.status === 413
              ? "File exceeds the 10 MB limit."
              : `Upload failed (HTTP ${res.status}).`,
        );
      } else {
        router.refresh();
      }
    } catch {
      setError("Couldn't reach the API. It may be waking up — try again in ~30s.");
    } finally {
      setLoading(false);
      if (inputRef.current) inputRef.current.value = "";
    }
  }

  return (
    <div className="flex flex-col gap-2">
      <input
        ref={inputRef}
        type="file"
        accept=".pdf,.docx,application/pdf,application/vnd.openxmlformats-officedocument.wordprocessingml.document"
        hidden
        onChange={onChange}
      />
      <Button onClick={() => inputRef.current?.click()} disabled={loading}>
        {loading ? "Uploading…" : "Upload PDF or DOCX"}
      </Button>
      {error && <p className="text-sm text-urgent">{error}</p>}
    </div>
  );
}
