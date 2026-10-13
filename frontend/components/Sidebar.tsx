"use client";

import { useEffect, useState } from "react";
import { FileSearch, FlaskConical, History, Scale, type LucideIcon } from "lucide-react";
import { listSessions, type SessionSummary } from "@/lib/history";
import { restoreSession } from "@/lib/flow";
import { useAppStore } from "@/lib/store";
import { cn } from "@/lib/utils";

interface NavItem { key: string; label: string; Icon: LucideIcon; onClick: () => void; active?: boolean }

const scoreTone = (n: number) => (n >= 70 ? "text-up" : n < 50 ? "text-down" : "text-gold-dim");

/** The terminal's navigation rail: brand tile, icon-tile nav, and a watchlist-style list of recent analyses. */
export function Sidebar({ onHistory, onHowWeScore, onSample, onNavigate }: {
  onHistory: () => void; onHowWeScore: () => void; onSample: () => void; onNavigate?: () => void;
}) {
  const versions = useAppStore((s) => s.versions.length);
  const sessionId = useAppStore((s) => s.sessionId);
  const busy = useAppStore((s) => s.busy);
  const [recent, setRecent] = useState<SessionSummary[]>([]);
  useEffect(() => { listSessions().then((r) => setRecent(r.slice(0, 6))).catch(() => setRecent([])); }, [versions, sessionId]);

  const go = (fn: () => void) => () => { fn(); onNavigate?.(); };
  const nav: NavItem[] = [
    { key: "analyse", label: "Analyse", Icon: FileSearch, onClick: go(() => document.getElementById("work")?.scrollTo({ top: 0, behavior: "smooth" })), active: true },
    { key: "sample", label: "Try a sample", Icon: FlaskConical, onClick: go(onSample) },
    { key: "history", label: "History", Icon: History, onClick: go(onHistory) },
    { key: "score", label: "How we score", Icon: Scale, onClick: go(onHowWeScore) },
  ];

  return (
    <div className="flex h-full min-h-0 flex-col px-4 pt-5 pb-4">
      <div className="flex items-center gap-3 px-2.5">
        <span aria-hidden="true" className="grid h-10 w-10 flex-none place-items-center rounded-[11px] bg-[linear-gradient(150deg,#2a2318,#171310)] text-[#d9bd8b]">
          <FileSearch className="h-[18px] w-[18px]" />
        </span>
        <span className="min-w-0">
          <span className="block text-[19px] leading-[1.12] tracking-[0.02em]">Shortlist</span>
          <span className="mt-1 block truncate text-[12px] text-ink-3">Resume desk · India-first</span>
        </span>
      </div>

      <nav aria-label="Primary" className="mt-7 flex flex-none flex-col gap-1">
        {nav.map((item) => (
          <button
            key={item.key}
            type="button"
            onClick={item.onClick}
            disabled={busy !== "idle" && item.key !== "score" && item.key !== "analyse"}
            aria-current={item.active ? "page" : undefined}
            className={cn(
              "group flex min-h-12 items-center gap-3.5 rounded-[12px] px-2.5 text-left text-[14px] font-medium transition-[color,background-color,border-color,box-shadow] duration-300 disabled:opacity-40",
              item.active
                ? "bg-[linear-gradient(140deg,rgba(var(--c-gold-rgb),0.13),rgba(var(--c-gold-rgb),0.04))] text-ink shadow-[inset_0_1px_0_rgba(var(--c-gold-hi-rgb),0.08)]"
                : "text-ink-3 hover:bg-[rgba(var(--c-gold-rgb),0.045)] hover:text-ink",
            )}
          >
            <span
              aria-hidden="true"
              className={cn(
                "grid h-9 w-9 flex-none place-items-center rounded-[10px] border transition-colors",
                item.active
                  ? "border-[rgba(var(--c-gold-rgb),0.28)] bg-[rgba(var(--c-gold-rgb),0.14)] text-gold"
                  : "border-rule-control text-ink-3 group-hover:border-[rgba(var(--c-gold-rgb),0.24)] group-hover:text-gold",
              )}
            >
              <item.Icon className="h-[18px] w-[18px]" />
            </span>
            {item.label}
          </button>
        ))}
      </nav>

      <section aria-label="Recent analyses" className="mt-8 flex min-h-0 flex-1 flex-col">
        <div className="flex items-center justify-between px-2.5">
          <span className="text-[13.5px] text-ink-3">Recent</span>
          <span className="figure text-[12px] text-ink-3">{recent.length}</span>
        </div>
        {recent.length === 0 ? (
          <p className="mt-3 px-2.5 text-[12.5px] leading-relaxed text-ink-3">Your analyses appear here. Saved only in this browser.</p>
        ) : (
          <ul className="mt-2 flex flex-col gap-0.5 overflow-y-auto">
            {recent.map((r) => (
              <li key={r.id}>
                <button
                  type="button"
                  disabled={busy !== "idle"}
                  onClick={go(() => void restoreSession(r.id))}
                  className={cn(
                    "flex min-h-12 w-full items-center gap-3 rounded-[12px] px-2.5 text-left transition-colors hover:bg-[rgba(var(--c-gold-rgb),0.045)] disabled:opacity-40",
                    r.id === sessionId && "bg-[rgba(var(--c-gold-rgb),0.06)]",
                  )}
                >
                  <span aria-hidden="true" className="grid h-8 w-8 flex-none place-items-center rounded-[9px] border border-rule-control text-[13px] text-ink-2">
                    {r.jd_title.trim().charAt(0).toUpperCase() || "J"}
                  </span>
                  <span className="min-w-0 flex-1">
                    <span className="block truncate text-[13px] text-ink">{r.jd_title}</span>
                    <span className="block text-[11.5px] text-ink-3">{r.region === "india" ? "India" : "International"}</span>
                  </span>
                  <span className={cn("figure text-[13px]", scoreTone(r.best_overall))}>{r.best_overall}</span>
                </button>
              </li>
            ))}
          </ul>
        )}
      </section>

      <p className="mt-4 flex-none rounded-[12px] border border-rule-control px-3 py-2.5 text-[12px] leading-relaxed text-ink-3">
        Resumes are processed in memory and never stored on our servers.
      </p>
    </div>
  );
}
