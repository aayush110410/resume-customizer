"use client";

import { useEffect, useState } from "react";
import { ping } from "@/lib/api";

const COLD_START_COPY =
  "Waking up the analysis server — free hosting sleeps when idle. This can take up to a minute.";

/** Pings the backend on load; if it hasn't answered within 3 s, explains the free-tier cold start. */
export function ServerStatusBanner() {
  const [waking, setWaking] = useState(false);

  useEffect(() => {
    let cancelled = false;
    const slow = setTimeout(() => !cancelled && setWaking(true), 3000);
    (async () => {
      for (let attempt = 0; attempt < 20 && !cancelled; attempt++) {
        try {
          await ping(AbortSignal.timeout(15000));
          break;
        } catch {
          await new Promise((r) => setTimeout(r, 3000));
        }
      }
      clearTimeout(slow);
      if (!cancelled) setWaking(false);
    })();
    return () => {
      cancelled = true;
      clearTimeout(slow);
    };
  }, []);

  if (!waking) return null;
  return (
    <div role="status" className="border-b bg-amber-50 px-4 py-2 text-center text-sm text-amber-900 dark:bg-amber-950 dark:text-amber-100">
      {COLD_START_COPY}
    </div>
  );
}
