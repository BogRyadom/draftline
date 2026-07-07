"use client";

import { useEffect } from "react";

import { Button } from "@/components/ui/button";

export default function AppError({
  error,
  reset,
}: {
  error: Error & { digest?: string };
  reset: () => void;
}) {
  useEffect(() => {
    // Surface the error for debugging; the UI stays calm.
    console.error(error);
  }, [error]);

  return (
    <div className="flex flex-col items-start gap-4 rounded-xl border border-border bg-surface px-6 py-10">
      <div className="flex flex-col gap-1.5">
        <h2 className="text-base font-semibold text-ink">Something went wrong</h2>
        <p className="max-w-prose text-sm text-ink-soft">
          This page hit an unexpected error. On the free tier the API may be waking
          from sleep — try again in a moment.
        </p>
      </div>
      <Button onClick={reset}>Try again</Button>
    </div>
  );
}
