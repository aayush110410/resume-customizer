"use client";

import { useState } from "react";
import { AlertTriangle } from "lucide-react";
import { Delta, Label } from "@/components/ledger";
import { Sheet, SheetContent, SheetDescription, SheetHeader, SheetTitle } from "@/components/ui/sheet";
import type { Region, ScoreKey, ScoreReport } from "@/lib/types";
import { cn } from "@/lib/utils";

const KEYS: ScoreKey[] = ["match", "ats", "quality", "region"];
const NAME: Record<ScoreKey, string> = { match: "JD match", ats: "ATS", quality: "Content quality", region: "Region fit" };
const RUBRIC: Record<ScoreKey, string> = {
  match: "Each JD requirement is weighted must 3 · should 2 · nice 1 and credited strong 1.0 · partial 0.6 · transferable 0.4 · missing 0, from evidence the model must quote verbatim. A years-of-experience shortfall scales the result down (to at most −25%). A missing must-have is flagged as a knockout risk.",
  ats: "Parseability 30 (columns, tables, images, hidden text, contact info) · keyword coverage 35 (in a bullet counts more than a skills-list mention) · structure 20 (sections, date format, order) · length 15 (page norms for your level and region).",
  quality: "Quantified bullets 30 · action-verb openers 20 · bullet length 15 · outcomes vs duties 15 · hygiene 10 (no pronouns or buzzwords) · a specific summary 10.",
  region: "Starts at 100. Deductions for personal details and conventions the region's recruiters read as dated or risky (by employer type), over-length for your level, and expected signals that are missing (e.g. CGPA for freshers in services hiring).",
};
const ATS_NOTE = "Estimate — real ATS systems don't publish scores; this models common parsing and keyword-filter behaviour.";

export const REGION_WEIGHTS: Record<Region, Record<ScoreKey, number>> = {
  india: { match: 0.4, ats: 0.25, quality: 0.2, region: 0.15 },
  international: { match: 0.4, ats: 0.25, quality: 0.25, region: 0.1 },
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
          {KEYS.map((k) => (
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

export function ScoreBoard({ before, after, region }: { before: ScoreReport; after?: ScoreReport; region: Region }) {
  const [focus, setFocus] = useState<ScoreKey>("match");
  const [open, setOpen] = useState(false);
  const [all, setAll] = useState(false);
  const shown = after ?? before;
  const explanations = shown.subscores[focus]?.explanations ?? [];

  return (
    <section aria-label="Scores" className="card-lit edge-lit flex flex-col gap-6 p-5 sm:p-7">
      <div className="flex flex-wrap items-end justify-between gap-6">
        <div>
          <Label>Overall · {region === "india" ? "India" : "International"} weighting</Label>
          <div className="mt-2 flex items-baseline gap-4">
            <span className="figure text-[64px] leading-[0.9] font-light tracking-[-0.02em] text-ink">{shown.overall}</span>
            {after && (
              <span className="figure text-[17px] text-ink-3">
                from {before.overall} <Delta value={after.overall - before.overall} />
              </span>
            )}
          </div>
        </div>
        <button type="button" onClick={() => setOpen(true)} className="text-[13px] text-gold-dim underline-offset-4 hover:text-gold hover:underline">
          How we score
        </button>
      </div>

      {shown.knockouts.length > 0 && (
        <div role="alert" className="flex gap-3 rounded-[14px] border border-down/30 bg-[rgba(224,121,107,0.06)] px-4 py-3 text-[13.5px] leading-relaxed text-ink-2">
          <AlertTriangle className="mt-0.5 size-4 shrink-0 text-down" aria-hidden />
          <p><span className="text-down">Knockout risk.</span> No evidence for must-have: {shown.knockouts.join("; ")}. Many screeners reject on this alone.</p>
        </div>
      )}

      <div role="tablist" aria-label="Score breakdown" className="grid grid-cols-2 gap-3 sm:grid-cols-4">
        {KEYS.map((k) => {
          const b = before.subscores[k]?.score ?? 0;
          const a = after?.subscores[k]?.score;
          return (
            <button
              key={k}
              role="tab"
              aria-selected={focus === k}
              onClick={() => setFocus(k)}
              className={cn(
                "tile flex flex-col items-start gap-1.5 px-4 py-4 text-left transition-[border-color,box-shadow] duration-300",
                focus === k ? "border-[rgba(217,189,139,0.45)]! shadow-[0_10px_26px_-14px_rgba(217,189,139,0.45)]" : "hover:border-[rgba(217,189,139,0.25)]!",
              )}
            >
              <span className="text-[13px] text-ink-3">{NAME[k]} <span className="figure text-ink-3/80">· {Math.round(shown.weights[k] * 100)}%</span></span>
              <span className="flex items-baseline gap-2">
                <span className="figure text-[24px] font-medium text-ink">{a ?? b}</span>
                {a !== undefined && <Delta value={a - b} />}
              </span>
            </button>
          );
        })}
      </div>

      <div>
        <div className="flex items-baseline justify-between gap-4">
          <Label>What moved {NAME[focus]}</Label>
          {focus === "ats" && <span className="text-[12px] text-ink-3">{ATS_NOTE}</span>}
        </div>
        {explanations.length === 0 ? (
          <p className="mt-3 text-[13.5px] text-ink-3">Nothing lost here.</p>
        ) : (
          <ul className="mt-2">
            {explanations.slice(0, all ? undefined : 3).map((e, i) => (
              <li key={i} className="ledger-row grid grid-cols-[1fr_auto] gap-x-4 gap-y-1 border-t border-rule-section py-3">
                <span className="text-[13.5px] leading-snug text-ink-2">{e.detail}</span>
                <span className="figure text-right text-[13px] text-down">{e.impact ? Math.round(e.impact * 10) / 10 : ""}</span>
                {e.fix && <span className="col-span-2 text-[12.5px] leading-relaxed text-ink-3">{e.fix}</span>}
              </li>
            ))}
          </ul>
        )}
        {explanations.length > 3 && (
          <button type="button" onClick={() => setAll((v) => !v)} className="mt-2 text-[13px] text-gold-dim hover:text-gold">
            {all ? "Show fewer" : `Show all ${explanations.length}`}
          </button>
        )}
      </div>

      <HowWeScoreSheet open={open} onOpenChange={setOpen} weights={shown.weights} />
    </section>
  );
}
