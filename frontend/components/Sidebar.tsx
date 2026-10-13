"use client";

import { useEffect, useState } from "react";
import { FileSearch, Plus, Trash2 } from "lucide-react";
import { deleteSession, listSessions, type SessionSummary } from "@/lib/history";
import { restoreSession } from "@/lib/flow";
import { useAppStore } from "@/lib/store";
import { cn } from "@/lib/utils";

const scoreTone = (n: number) => (n >= 70 ? "text-up" : n < 50 ? "text-down" : "text-gold-dim");

function ago(iso: string): string {
  const mins = Math.round((Date.now() - new Date(iso).getTime()) / 60000);
  if (mins < 60) return `${Math.max(1, mins)}m ago`;
  if (mins < 60 * 24) return `${Math.round(mins / 60)}h ago`;
  return new Date(iso).toLocaleDateString("en-IN", { day: "numeric", month: "short" });
}

/** The terminal's rail: brand, one primary action, and saved analyses as the only history. */
export function Sidebar({ onNew, onHowWeScore, onNavigate }: { onNew: () => void; onHowWeScore: () => void; onNavigate?: () => void }) {
  const versions = useAppStore((s) => s.versions.length);
  const sessionId = useAppStore((s) => s.sessionId);
  const busy = useAppStore((s) => s.busy);
  const [recent, setRecent] = useState<SessionSummary[]>([]);
  useEffect(() => { listSessions().then(setRecent).catch(() => setRecent([])); }, [versions, sessionId]);

  return (
    <div className="flex h-full min-h-0 flex-col px-4 pt-5 pb-4">
      <div className="flex items-center gap-3 px-2.5">
        <span aria-hidden="true" className="grid h-10 w-10 flex-none place-items-center rounded-[11px] bg-[linear-gradient(150deg,#2a2318,#171310)] text-[#d9bd8b]">
          <FileSearch className="h-[18px] w-[18px]" />
        </span>
        <span className="min-w-0">
          <span className="block text-[19px] leading-[1.12] tracking-[0.02em]">Shortlist</span>
          <span className="mt-1 block truncate text-[12px] text-ink-3">Resume desk</span>
        </span>
      </div>

      <button
        type="button"
        disabled={busy !== "idle"}
        onClick={() => { onNew(); onNavigate?.(); }}
        className="mt-7 flex min-h-12 items-center gap-3.5 rounded-[12px] bg-[linear-gradient(140deg,rgba(var(--c-gold-rgb),0.13),rgba(var(--c-gold-rgb),0.04))] px-2.5 text-[14px] font-medium text-ink shadow-[inset_0_1px_0_rgba(var(--c-gold-hi-rgb),0.08)] transition-opacity disabled:opacity-40"
      >
        <span aria-hidden="true" className="grid h-9 w-9 flex-none place-items-center rounded-[10px] border border-[rgba(var(--c-gold-rgb),0.28)] bg-[rgba(var(--c-gold-rgb),0.14)] text-gold">
          <Plus className="h-[18px] w-[18px]" />
        </span>
        New analysis
      </button>

      <section aria-label="Saved analyses" className="mt-8 flex min-h-0 flex-1 flex-col">
        <div className="flex items-center justify-between px-2.5">
          <span className="text-[13.5px] text-ink-3">Saved</span>
          <span className="figure text-[12px] text-ink-3">{recent.length}</span>
        </div>
        {recent.length === 0 ? (
          <p className="mt-3 px-2.5 text-[12.5px] leading-relaxed text-ink-3">Analyses you run are kept here, in this browser only.</p>
        ) : (
          <ul className="no-scrollbar mt-2 flex min-h-0 flex-col gap-0.5 overflow-y-auto">
            {recent.map((r) => (
              <li key={r.id} className="group relative">
                <button
                  type="button"
                  disabled={busy !== "idle"}
                  onClick={() => { void restoreSession(r.id); onNavigate?.(); }}
                  className={cn(
                    "flex min-h-12 w-full items-center gap-3 rounded-[12px] px-2.5 pr-10 text-left transition-colors hover:bg-[rgba(var(--c-gold-rgb),0.045)] disabled:opacity-40",
                    r.id === sessionId && "bg-[rgba(var(--c-gold-rgb),0.07)]",
                  )}
                >
                  <span aria-hidden="true" className="grid h-8 w-8 flex-none place-items-center rounded-[9px] border border-rule-control text-[13px] text-ink-2">
                    {r.jd_title.trim().charAt(0).toUpperCase() || "J"}
                  </span>
                  <span className="min-w-0 flex-1">
                    <span className="block truncate text-[13px] text-ink">{r.jd_title}</span>
                    <span className="block text-[11.5px] text-ink-3">{r.region === "india" ? "India" : "International"} · {ago(r.created_at)}</span>
                  </span>
                  <span className={cn("figure text-[13px] transition-opacity group-hover:opacity-0", scoreTone(r.best_overall))}>{r.best_overall}</span>
                </button>
                <button
                  type="button"
                  aria-label={`Delete ${r.jd_title}`}
                  onClick={async () => { await deleteSession(r.id); setRecent((x) => x.filter((i) => i.id !== r.id)); }}
                  className="absolute top-1/2 right-1.5 grid size-8 -translate-y-1/2 place-items-center rounded-full text-ink-3 opacity-0 transition-opacity group-hover:opacity-100 hover:text-down focus-visible:opacity-100"
                >
                  <Trash2 className="size-3.5" aria-hidden />
                </button>
              </li>
            ))}
          </ul>
        )}
      </section>

      <div className="mt-4 flex flex-none flex-col gap-2 px-2.5">
        <button type="button" onClick={() => { onHowWeScore(); onNavigate?.(); }} className="text-left text-[13px] text-gold-dim hover:text-gold">How scoring works</button>
        <p className="text-[12px] leading-relaxed text-ink-3">Resumes are processed in memory, never stored on the server.</p>
      </div>
    </div>
  );
}
