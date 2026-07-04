"use client";

import { useState } from "react";

import { Button } from "@/components/ui/button";
import { apiFetch } from "@/lib/api-client";

export function ConnectGmailButton({
  label = "Connect Gmail",
  variant = "primary",
}: {
  label?: string;
  variant?: "primary" | "outline";
}) {
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  async function connect() {
    setLoading(true);
    setError(null);
    try {
      const res = await apiFetch("/accounts/gmail/connect", { method: "POST" });
      if (!res.ok) {
        setError(
          res.status === 503
            ? "Gmail isn't configured on the server yet."
            : `Couldn't start the connection (HTTP ${res.status}).`,
        );
        setLoading(false);
        return;
      }
      const { authorization_url } = await res.json();
      window.location.href = authorization_url;
    } catch {
      setError("Couldn't reach the API. It may be waking up — try again in ~30s.");
      setLoading(false);
    }
  }

  return (
    <div className="flex flex-col items-start gap-2">
      <Button onClick={connect} disabled={loading} variant={variant}>
        {loading ? "Redirecting…" : label}
      </Button>
      {error && <p className="text-sm text-urgent">{error}</p>}
    </div>
  );
}
