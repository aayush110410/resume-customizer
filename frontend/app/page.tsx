"use client";

import { useEffect, useState } from "react";
import { FileText, Menu, Pencil } from "lucide-react";
import { Grain } from "@/components/Grain";
import { Sidebar } from "@/components/Sidebar";
import { Sheet, SheetContent, SheetTitle } from "@/components/ui/sheet";
import { HistoryDrawer } from "@/components/HistoryDrawer";
import { InputPanel } from "@/components/input/InputPanel";
import { CardTitle, LedgerTabs, OutlineButton } from "@/components/ledger";
import { StageTimeline } from "@/components/progress/StageTimeline";
import { CoverLetterPanel } from "@/components/results/CoverLetterPanel";
import { DiffView } from "@/components/results/DiffView";
import { DownloadMenu } from "@/components/results/DownloadMenu";
import { InsightsRail } from "@/components/results/InsightsRail";
import { RequirementLedger } from "@/components/results/RequirementLedger";
import { ResumeView, StreamingPreview } from "@/components/results/ResumeView";
import { HowWeScoreSheet, REGION_WEIGHTS, ScoreBoard } from "@/components/results/ScoreBoard";
import { VersionsPanel } from "@/components/results/VersionsPanel";
import { getMeta } from "@/lib/api";
import { messageFor } from "@/lib/errors";
import { retryLast, runAnalyzeAndTailor } from "@/lib/flow";
import { loadSampleResume, SAMPLE_JD } from "@/lib/sample";
import { useAppStore } from "@/lib/store";
import type { Meta } from "@/lib/types";

type Tab = "analysis" | "resume" | "changes" | "letter" | "versions";

const HOW = [
  ["JD match", "Every requirement in the job, checked against a verbatim quote from your resume."],
  ["ATS", "Whether screening software can read your file and finds the job's keywords in context."],
  ["Content quality", "Quantified impact, strong verbs, outcome-led bullets: what recruiters skim for."],
  ["Region fit", "Indian recruiter norms by employer type, or what changes when you apply abroad."],
];

function HowItWorks() {
  return (
    <section className="card edge-lit p-5">
      <CardTitle meta="4 scores">What we check</CardTitle>
      <dl className="mt-3">
        {HOW.map(([k, v]) => (
          <div key={k} className="border-t border-rule-section py-3">
            <dt className="text-[14px] text-ink">{k}</dt>
            <dd className="mt-1 text-[13px] leading-[1.65] text-ink-3">{v}</dd>
          </div>
        ))}
      </dl>
    </section>
  );
}

function InputSummary({ onEdit }: { onEdit: () => void }) {
  const { inputs, analysis, busy } = useAppStore();
  const title = analysis?.jd.title ?? inputs.jd.trim().split("\n")[0]?.slice(0, 80);
  return (
    <section className="card edge-lit flex flex-wrap items-center gap-4 p-4 sm:px-5">
      <span aria-hidden="true" className="grid h-10 w-10 flex-none place-items-center rounded-[11px] border border-[rgba(217,189,139,0.28)] bg-[rgba(217,189,139,0.14)] text-gold">
        <FileText className="h-[18px] w-[18px]" />
      </span>
      <div className="min-w-0 flex-1">
        <div className="truncate text-[15px] text-ink">{title || "Job description"}</div>
        <div className="truncate text-[12.5px] text-ink-3">
          {inputs.file?.name ?? "resume"} · {(analysis?.region ?? inputs.region) === "india" ? "India" : "International"}
        </div>
      </div>
      <OutlineButton onClick={onEdit} disabled={busy !== "idle"}><Pencil className="size-3.5" aria-hidden />Edit inputs</OutlineButton>
    </section>
  );
}

export default function Home() {
  const s = useAppStore();
  const [meta, setMeta] = useState<Meta>();
  const [tab, setTab] = useState<Tab>("analysis");
  const [history, setHistory] = useState(false);
  const [how, setHow] = useState(false);
  const [nav, setNav] = useState(false);
  const [editing, setEditing] = useState(false);
  useEffect(() => { getMeta().then(setMeta).catch(() => undefined); }, []);

  const version = s.versions.find((v) => v.id === s.activeVersionId);
  const analysis = s.analysis;
  const scores = analysis?.scores ?? s.partial.scores;
  const insights = analysis?.insights ?? s.partial.insights;
  const jd = analysis?.jd ?? s.partial.jd;
  const evidence = analysis?.evidence ?? s.partial.evidence;
  const started = s.busy !== "idle" || !!scores || !!s.error;
  const streaming = s.busy === "tailoring" && s.streamingItems.length > 0;
  const region = analysis?.region ?? s.inputs.region;
  const loadSample = async () => {
    s.setInput("jd", SAMPLE_JD);
    s.setInput("file", await loadSampleResume());
    s.setInput("region", "india");
    setEditing(true);
  };
  const sidebar = (onNavigate?: () => void) => (
    <Sidebar onHistory={() => setHistory(true)} onHowWeScore={() => setHow(true)} onSample={() => void loadSample()} onNavigate={onNavigate} />
  );
  const stage = Object.entries(s.stages).find(([, v]) => v === "active")?.[0];

  return (
    <div className="flex min-h-screen justify-center p-0 lg:p-3">
      <div className="relative flex w-full flex-col border-rule shell-lit lg:grid lg:h-[calc(100vh-24px)] lg:grid-cols-[246px_minmax(0,1fr)] lg:grid-rows-[auto_minmax(0,1fr)] lg:overflow-hidden lg:rounded-[3px] lg:border lg:shadow-[0_50px_140px_rgba(0,0,0,0.75)]">
        <Grain />
        <aside aria-label="Navigation" className="hidden border-r border-rule-section rail-lit lg:row-span-full lg:block lg:overflow-y-auto">
          {sidebar()}
        </aside>

        <header className="relative z-[25] grid grid-cols-[auto_minmax(0,1fr)_auto] items-center gap-x-2.5 border-b border-rule-section px-4 py-2.5 max-lg:sticky max-lg:top-0 max-lg:bg-shell sm:gap-x-4 sm:px-6 sm:py-3 lg:px-7">
          <button type="button" onClick={() => setNav(true)} aria-label="Open navigation" className="grid h-11 w-11 flex-none place-items-center rounded-[10px] border border-rule-control text-ink-3 transition-colors hover:border-gold hover:text-ink lg:hidden">
            <Menu className="h-4 w-4" />
          </button>
          <div className="min-w-0 lg:col-start-2">
            <div className="flex h-11 min-w-0 items-center gap-3 rounded-full border border-rule-control px-4 sm:h-12 sm:px-5 lg:max-w-[640px]">
              <span className={stage ? "size-2 flex-none animate-pulse rounded-full bg-gold" : "size-2 flex-none rounded-full bg-up/70"} aria-hidden />
              <span className="truncate text-[13.5px] text-ink-2">
                {stage ? `Working · ${stage}` : analysis ? `${analysis.jd.title}${analysis.jd.company ? ` · ${analysis.jd.company}` : ""}` : "Paste a job description and upload a resume to begin"}
              </span>
            </div>
          </div>
          <div className="flex items-center justify-end gap-2 sm:gap-3 lg:col-start-3 lg:pl-6">
            <span className="hidden min-h-11 items-center gap-2 rounded-full border border-rule-control px-4 text-[12.5px] text-ink-3 sm:flex">
              <span className="h-3 w-px bg-rule-mono" aria-hidden />{region === "india" ? "India hiring" : "International"}
            </span>
            <OutlineButton tone="gold" className="min-h-11" onClick={() => setHistory(true)} disabled={s.busy !== "idle"}>History</OutlineButton>
          </div>
        </header>

        <div id="work" className="relative z-[1] min-h-0 lg:overflow-y-auto">
          <div className="grid gap-5 p-4 sm:p-6 lg:px-7 xl:grid-cols-[minmax(0,1fr)_358px]">
            <main id="results" className="flex min-w-0 scroll-mt-4 flex-col gap-5">
              {!started && (
                <h1 className="max-w-3xl pt-2 text-[34px] leading-[1.08] font-medium tracking-[-0.02em] text-balance sm:text-[40px]">
                  See exactly what your resume is missing for this job, and fix it without inventing a thing.
                </h1>
              )}
              {editing || !started ? <InputPanel meta={meta} onSubmitted={() => setEditing(false)} /> : <InputSummary onEdit={() => setEditing(true)} />}
              {started && <StageTimeline />}
              {s.error && (
                <div role="alert" className="card flex flex-wrap items-center justify-between gap-3 border-down/30! p-4">
                  <p className="text-[13.5px] text-ink-2">{messageFor(s.error.code)}</p>
                  {s.error.retryable && <OutlineButton onClick={() => void retryLast()}>Try again</OutlineButton>}
                </div>
              )}
              {analysis && analysis.jd.suggested_region !== analysis.region && s.busy === "idle" && (
                <div className="card flex flex-wrap items-center justify-between gap-3 p-4">
                  <p className="text-[13.5px] text-ink-2">
                    This job looks {analysis.jd.suggested_region === "india" ? "India-based" : "based outside India"}{analysis.jd.location ? ` (${analysis.jd.location})` : ""}. Score it for the {analysis.jd.suggested_region === "india" ? "Indian" : "international"} market instead?
                  </p>
                  <OutlineButton tone="gold" onClick={() => { s.setInput("region", analysis.jd.suggested_region); void runAnalyzeAndTailor(); }}>
                    Switch to {analysis.jd.suggested_region === "india" ? "India" : "International"}
                  </OutlineButton>
                </div>
              )}
              {s.warnings.includes("NOT_A_JD") && <p className="text-[13.5px] text-gold">{messageFor("NOT_A_JD")}</p>}
              {scores && <ScoreBoard before={scores} after={version?.scores} region={region} />}

              {(jd || streaming) && (
                <section className="card edge-lit flex flex-col gap-5 p-5 sm:p-7">
                  <LedgerTabs
                    label="Results"
                    value={tab}
                    onChange={setTab}
                    tabs={[
                      { value: "analysis", label: "Evidence" },
                      { value: "resume", label: "Tailored resume", badge: version?.flags.length ? <span className="figure">{version.flags.length}</span> : undefined },
                      { value: "changes", label: "Changes" },
                      { value: "letter", label: "Cover letter" },
                      { value: "versions", label: "Versions", badge: s.versions.length ? <span className="figure">{s.versions.length}</span> : undefined },
                    ]}
                  />
                  <div role="tabpanel" id={`panel-${tab}`} aria-labelledby={`tab-${tab}`} className="min-h-[320px]">
                    {tab === "analysis" && jd && evidence && <RequirementLedger jd={jd} evidence={evidence} />}
                    {tab === "analysis" && jd && !evidence && <p className="text-[13.5px] text-ink-3">Matching evidence…</p>}
                    {tab === "resume" && (streaming ? <StreamingPreview items={s.streamingItems} /> : version ? (
                      <div className="flex flex-col gap-6">
                        <div className="flex flex-wrap items-center justify-between gap-3">
                          <p className="max-w-xl text-[13px] text-ink-3">
                            {version.flags.length ? `${version.flags.length} line(s) contain facts we couldn't find in your original. Check each one, or choose Use original. Anything left is included in your download.` : "Every fact traced back to your original resume."}
                          </p>
                          <DownloadMenu request={{ kind: "resume", region: analysis!.region, resume: version.resume }} />
                        </div>
                        <ResumeView resume={version.resume} flags={version.flags} onRevert={(id) => s.revertFlag(version.id, id)} />
                      </div>
                    ) : <p className="text-[13.5px] text-ink-3">The tailored resume appears here once analysis finishes.</p>)}
                    {tab === "changes" && (version && analysis ? <DiffView before={analysis.resume} after={version.resume} changes={version.changes} /> : <p className="text-[13.5px] text-ink-3">No tailored version yet.</p>)}
                    {tab === "letter" && <CoverLetterPanel />}
                    {tab === "versions" && <VersionsPanel />}
                  </div>
                </section>
              )}
            </main>

            <aside aria-label="Insights" className="flex min-w-0 flex-col gap-5">
              {insights ? <InsightsRail insights={insights} /> : started ? (
                <section className="card edge-lit p-5">
                  <CardTitle meta="7-second scan">Recruiter&apos;s view</CardTitle>
                  <p className="mt-3 text-[13.5px] text-ink-3">Arrives with the scores.</p>
                </section>
              ) : <HowItWorks />}
            </aside>
          </div>
        </div>
      </div>

      <Sheet open={nav} onOpenChange={setNav}>
        <SheetContent side="left" className="w-[86%] max-w-[320px] border-r border-rule-section bg-rail p-0">
          <SheetTitle className="sr-only">Navigation</SheetTitle>
          {sidebar(() => setNav(false))}
        </SheetContent>
      </Sheet>
      <HistoryDrawer open={history} onOpenChange={setHistory} />
      <HowWeScoreSheet open={how} onOpenChange={setHow} weights={scores?.weights ?? REGION_WEIGHTS[region]} />
    </div>
  );
}
