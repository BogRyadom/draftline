"use client";

import { useRouter } from "next/navigation";
import { useEffect, useRef } from "react";

/**
 * Polls the server component while background work is pending (e.g. classification
 * after a sync), so results appear without a manual reload. Stops when `active`
 * turns false or after `maxTicks` to avoid polling forever on a stuck item.
 */
export function AutoRefresh({
  active,
  intervalMs = 4000,
  maxTicks = 15,
}: {
  active: boolean;
  intervalMs?: number;
  maxTicks?: number;
}) {
  const router = useRouter();
  const ticks = useRef(0);

  useEffect(() => {
    if (!active) return;
    ticks.current = 0;
    const id = setInterval(() => {
      ticks.current += 1;
      router.refresh();
      if (ticks.current >= maxTicks) clearInterval(id);
    }, intervalMs);
    return () => clearInterval(id);
  }, [active, intervalMs, maxTicks, router]);

  return null;
}
