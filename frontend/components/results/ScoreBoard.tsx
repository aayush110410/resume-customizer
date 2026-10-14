"use client";

import { AlertTriangle } from "lucide-react";
import { Delta } from "@/components/ledger";
import { Sheet, SheetContent, SheetDescription, SheetHeader, SheetTitle } from "@/components/ui/sheet";
import type { Region, ScoreKey, ScoreReport } from "@/lib/types";
import { cn } from "@/lib/utils";

const KEYS: ScoreKey[] = ["match", "ats", "quality", "region", "story"];
const NAME: Record<ScoreKey, string> = { match: "JD match", ats: "ATS", quality: "Content quality", region: "Region fit", story: "Career story" };
const SHORT: Record<ScoreKey, string> = { match: "JD match", ats: "ATS", quality: "Content", region: "Region fit", story: "Story" };
const RUBRIC: Record<ScoreKey, string> = {
  match: "Each JD requirement is weighted must 3 · should 2 · nice 1 and credited strong 1.0 · partial 0.6 · transferable 0.4 · missing 0, from evidence the model must quote verbatim. A years-of-experience shortfall scales the result down (to at most −25%). A missing must-have is flagged as a knockout risk.",
  ats: "Parseability 30 (columns, tables, images, hidden text, contact info) · keyword coverage 35 (in a bullet counts more than a skills-list mention) · structure 20 (sections, date format, order) · length 15 (page norms for your level and region).",
  quality: "Quantified bullets 30 · action-verb openers 20 · bullet length 15 · outcomes vs duties 15 · hygiene 10 (no pronouns or buzzwords) · a specific summary 10.",
  region: "Starts at 100. Deductions for personal details and conventions the region's recruiters read as dated or risky (by employer type), over-length for your level, and expected signals that are missing (e.g. CGPA for freshers in services hiring).",
  story: "Judged for your stage. Students and fresh graduates: projects 40 · internships 25 · presentation 20 · continuity 15. 1–3 years: projects 20 · internships 5 · presentation 10 · continuity 20 · stability 25 · move 20. 3+ years: projects 10 · continuity 25 · stability 30 · move 35. Projects are read for purpose, originality, real use, numbers and depth. Unexplained gaps (India: 6+ months) and roles under a year count against you until you explain them; paid or unpaid never matters.",
};
const ATS_NOTE = "Estimate — real ATS systems don't publish scores; this models common parsing and keyword-filter behaviour.";

export const REGION_WEIGHTS: Record<Region, Record<ScoreKey, number>> = {
  india: { match: 0.35, ats: 0.2, quality: 0.15, region: 0.1, story: 0.2 },
  international: { match: 0.35, ats: 0.2, quality: 0.2, region: 0.1, story: 0.15 },
};

export function HowWeScoreSheet({ open, onOpenChange, weights }: { open: boolean; onOpenChange: (o: boolean) => void; weights: Record<string, number> }) {
  return (
    <Sheet open={open} onOpenChange={onOpenChange}>
      <SheetContent side="right" className="w-full max-w-md overflow-y-auto border-l border-rule-section bg-rail p-8">
        <SheetHeader className="p-0">
          <SheetTitle className="text-[22px] font-medium tracking-[-0.018em]">How we score</SheetTitle>
          <SheetDescription className="text-[13.5px] leading-relaxed text-ink-3">
            The language model only extracts evidence and must quote your resume word for word. Unverifiable quotes are
            downgraded. Every number below is then computed by code, so the same inputs give the same score.
          </SheetDescription>
        </SheetHeader>
        <dl className="mt-6">
          {KEYS.filter((k) => weights[k] !== undefined).map((k) => (
            <div key={k} className="border-t border-rule-section py-4">
              <dt className="flex justify-between text-[14px] text-ink">{NAME[k]}<span className="figure text-gold">{Math.round(weights[k] * 100)}%</span></dt>
              <dd className="mt-2 text-[13px] leading-[1.7] text-ink-3">{RUBRIC[k]}</dd>
            </div>
          ))}
        </dl>
        <p className="border-t border-rule-section pt-4 text-[12.5px] leading-relaxed text-ink-3">{ATS_NOTE}</p>
      </SheetContent>
    </Sheet>
  );
}

/** Overall score and the sub-scores as one strip; a tile filters the Fixes list to that score. Story only appears
 * when the analysis has one (saved analyses from before the career profile have four). */
export function ScoreBoard({ before, after, region, focus, onFocus, onHowWeScore }: {
  before: ScoreReport; after?: ScoreReport; region: Region; focus: ScoreKey | "all";
  onFocus: (k: ScoreKey | "all") => void; onHowWeScore: () => void;
}) {
  const shown = after ?? before;
  const keys = KEYS.filter((k) => before.subscores[k]);
  return (
    <section aria-label="Scores" className="card-lit edge-lit p-5 sm:p-6">
      <div className="grid gap-5 md:grid-cols-[minmax(0,190px)_minmax(0,1fr)] md:items-center">
        <button type="button" onClick={() => onFocus("all")} className="text-left" aria-pressed={focus === "all"}>
          <span className="block text-[14px] text-ink-3">Overall · {region === "india" ? "India" : "International"}</span>
          <span className="figure mt-1 block text-[60px] leading-[0.95] font-light tracking-[-0.02em] text-ink">{shown.overall}</span>
          {after && <span className="figure mt-1 block text-[13.5px] text-ink-3">was {before.overall} <Delta value={after.overall - before.overall} /></span>}
        </button>
        <div className={cn("grid grid-cols-2 gap-2.5", keys.length > 4 ? "sm:grid-cols-3 lg:grid-cols-5" : "lg:grid-cols-4")}>
          {keys.map((k) => {
            const b = before.subscores[k]?.score ?? 0;
            const a = after?.subscores[k]?.score;
            return (
              <button
                key={k}
                type="button"
                aria-pressed={focus === k}
                onClick={() => onFocus(focus === k ? "all" : k)}
                className={cn(
                  "tile flex flex-col items-start gap-1 px-4 py-3.5 text-left transition-[border-color,box-shadow] duration-300",
                  focus === k ? "border-[rgba(217,189,139,0.45)]! shadow-[0_10px_26px_-14px_rgba(217,189,139,0.45)]" : "hover:border-[rgba(217,189,139,0.25)]!",
                )}
              >
                <span className="text-[13px] text-ink-3">{SHORT[k]}</span>
                <span className="flex items-baseline gap-2">
                  <span className="figure text-[24px] font-medium text-ink">{a ?? b}</span>
                  {a !== undefined && <Delta value={a - b} />}
                </span>
              </button>
            );
          })}
        </div>
      </div>
      <div className="mt-4 flex flex-wrap items-center justify-between gap-x-6 gap-y-2 border-t border-rule-section pt-3.5">
        {shown.knockouts.length > 0 ? (
          <p className="flex items-start gap-2 text-[13px] leading-relaxed text-ink-2">
            <AlertTriangle className="mt-0.5 size-3.5 shrink-0 text-down" aria-hidden />
            <span><span className="text-down">{shown.knockouts.length} must-have{shown.knockouts.length > 1 ? "s" : ""} with no evidence</span>, a common reason screeners reject outright.</span>
          </p>
        ) : (
          <p className="text-[13px] text-ink-3">Every must-have requirement has some evidence.</p>
        )}
        <button type="button" onClick={onHowWeScore} className="text-[13px] text-gold-dim hover:text-gold">How scoring works</button>
      </div>
    </section>
  );
}
