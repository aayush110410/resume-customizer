"use client";

import { useEffect, useState } from "react";
import { History } from "lucide-react";
import { HistoryDrawer } from "@/components/HistoryDrawer";
import { InputPanel } from "@/components/input/InputPanel";
import { Label, LedgerTabs, OutlineButton } from "@/components/ledger";
import { StageTimeline } from "@/components/progress/StageTimeline";
import { CoverLetterPanel } from "@/components/results/CoverLetterPanel";
import { DiffView } from "@/components/results/DiffView";
import { DownloadMenu } from "@/components/results/DownloadMenu";
import { InsightsRail } from "@/components/results/InsightsRail";
import { RequirementLedger } from "@/components/results/RequirementLedger";
import { ResumeView, StreamingPreview } from "@/components/results/ResumeView";
import { ScoreBoard } from "@/components/results/ScoreBoard";
import { VersionsPanel } from "@/components/results/VersionsPanel";
import { getMeta } from "@/lib/api";
import { messageFor } from "@/lib/errors";
import { runAnalyzeAndTailor } from "@/lib/flow";
import { useAppStore } from "@/lib/store";
import type { Meta } from "@/lib/types";

type Tab = "analysis" | "resume" | "changes" | "letter" | "versions";

function EmptyState() {
  const rows = [
    ["JD match", "Every requirement in the job, checked against a verbatim quote from your resume."],
    ["ATS", "Whether screening software can read your file and finds the job's keywords in context."],
    ["Content quality", "Quantified impact, strong verbs, outcome-led bullets: what recruiters skim for."],
    ["Region fit", "Indian recruiter norms by employer type, or what changes when you apply abroad."],
  ];
  return (
    <div className="flex max-w-2xl flex-col gap-8 py-6">
      <h1 className="text-[40px] leading-[1.05] font-medium tracking-[-0.018em] text-balance">
        See exactly what your resume is missing for this job, and fix it without inventing a thing.
      </h1>
      <dl>
        {rows.map(([k, v]) => (
          <div key={k} className="grid gap-1 border-t border-rule py-4 sm:grid-cols-[180px_1fr]">
            <dt className="text-[15px] text-ink">{k}</dt>
            <dd className="text-[13.5px] leading-[1.7] text-ink-3">{v}</dd>
          </div>
        ))}
      </dl>
      <p className="text-[13.5px] leading-[1.7] text-ink-3">
        Paste a job description and upload your resume on the left, or use <span className="text-gold-dim">Try a sample</span> to see a full run.
      </p>
    </div>
  );
}

export default function Home() {
  const s = useAppStore();
  const [meta, setMeta] = useState<Meta>();
  const [tab, setTab] = useState<Tab>("analysis");
  const [history, setHistory] = useState(false);
  useEffect(() => { getMeta().then(setMeta).catch(() => undefined); }, []);

  const version = s.versions.find((v) => v.id === s.activeVersionId);
  const analysis = s.analysis;
  const scores = analysis?.scores ?? s.partial.scores;
  const insights = analysis?.insights ?? s.partial.insights;
  const jd = analysis?.jd ?? s.partial.jd;
  const evidence = analysis?.evidence ?? s.partial.evidence;
  const started = s.busy !== "idle" || !!scores || !!s.error;
  const streaming = s.busy === "tailoring" && s.streamingItems.length > 0;

  return (
    <div className="mx-auto flex w-full max-w-[1560px] flex-1 flex-col px-4 sm:px-5">
      <header className="flex min-h-16 items-center justify-between gap-4 border-b border-rule">
        <div className="flex items-baseline gap-3">
          <span className="text-[24px] font-medium tracking-[0.02em]">Shortlist</span>
          <span className="hidden text-[13px] text-ink-3 sm:inline">Resume customizer · India-first</span>
        </div>
        <OutlineButton onClick={() => setHistory(true)}><History className="size-4" aria-hidden />History</OutlineButton>
      </header>

      <div className="grid flex-1 gap-x-10 lg:grid-cols-[340px_minmax(0,1fr)] xl:grid-cols-[340px_minmax(0,1fr)_320px]">
        <aside className="border-rule py-8 lg:border-r lg:pr-10"><InputPanel meta={meta} /></aside>

        <main id="results" className="flex min-w-0 scroll-mt-4 flex-col gap-8 py-8">
          {!started && <EmptyState />}
          {started && <StageTimeline />}
          {s.error && (
            <div role="alert" className="flex flex-wrap items-center justify-between gap-3 border border-down/40 px-4 py-3">
              <p className="text-[13.5px] text-ink-2">{messageFor(s.error.code)}</p>
              {s.error.retryable && <OutlineButton onClick={() => void runAnalyzeAndTailor()}>Try again</OutlineButton>}
            </div>
          )}
          {s.warnings.includes("NOT_A_JD") && <p className="text-[13.5px] text-gold">{messageFor("NOT_A_JD")}</p>}
          {scores && <ScoreBoard before={scores} after={version?.scores} region={analysis?.region ?? s.inputs.region} />}

          {(jd || streaming) && (
            <>
              <LedgerTabs
                label="Results"
                value={tab}
                onChange={setTab}
                tabs={[
                  { value: "analysis", label: "Evidence" },
                  { value: "resume", label: "Tailored resume", badge: version?.flags.length ? <span className="figure text-gold">{version.flags.length}</span> : undefined },
                  { value: "changes", label: "Changes" },
                  { value: "letter", label: "Cover letter" },
                  { value: "versions", label: "Versions", badge: s.versions.length ? <span className="figure text-ink-3">{s.versions.length}</span> : undefined },
                ]}
              />
              <div role="tabpanel" id={`panel-${tab}`} aria-labelledby={`tab-${tab}`} className="min-h-[320px]">
                {tab === "analysis" && jd && evidence && <RequirementLedger jd={jd} evidence={evidence} />}
                {tab === "analysis" && jd && !evidence && <p className="text-[13.5px] text-ink-3">Matching evidence…</p>}
                {tab === "resume" && (streaming ? <StreamingPreview items={s.streamingItems} /> : version ? (
                  <div className="flex flex-col gap-6">
                    <div className="flex flex-wrap items-center justify-between gap-3">
                      <p className="text-[13px] text-ink-3">
                        {version.flags.length ? `${version.flags.length} line(s) contain facts we couldn't find in your original. Confirm or edit them before sending.` : "Every fact traced back to your original resume."}
                      </p>
                      <DownloadMenu request={{ kind: "resume", region: analysis!.region, resume: version.resume }} />
                    </div>
                    <ResumeView resume={version.resume} flags={version.flags} />
                  </div>
                ) : <p className="text-[13.5px] text-ink-3">The tailored resume appears here once analysis finishes.</p>)}
                {tab === "changes" && (version && analysis ? <DiffView before={analysis.resume} after={version.resume} changes={version.changes} /> : <p className="text-[13.5px] text-ink-3">No tailored version yet.</p>)}
                {tab === "letter" && <CoverLetterPanel />}
                {tab === "versions" && <VersionsPanel />}
              </div>
            </>
          )}
        </main>

        <aside className="border-rule py-8 lg:col-span-2 lg:border-t xl:col-span-1 xl:border-t-0 xl:border-l xl:pl-8">
          {insights ? <InsightsRail insights={insights} /> : started ? (
            <div className="flex flex-col gap-3"><Label>Recruiter&apos;s 7-second scan</Label><p className="text-[13.5px] text-ink-3">Arrives with the scores.</p></div>
          ) : null}
        </aside>
      </div>
      <HistoryDrawer open={history} onOpenChange={setHistory} />
    </div>
  );
}
