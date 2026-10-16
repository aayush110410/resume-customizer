"use client";

import { useEffect, useState } from "react";
import { FileSearch, Menu, Pencil, Plus } from "lucide-react";
import { InputPanel } from "@/components/input/InputPanel";
import { LedgerTabs, OutlineButton } from "@/components/ledger";
import { StageTimeline } from "@/components/progress/StageTimeline";
import { ClarifyCard } from "@/components/results/ClarifyCard";
import { CoverLetterPanel } from "@/components/results/CoverLetterPanel";
import { DiffView } from "@/components/results/DiffView";
import { DownloadMenu } from "@/components/results/DownloadMenu";
import { FixesPanel } from "@/components/results/FixesPanel";
import { InsightsRail } from "@/components/results/InsightsRail";
import { RequirementLedger } from "@/components/results/RequirementLedger";
import { ResumeView, StreamingPreview } from "@/components/results/ResumeView";
import { HowWeScoreSheet, REGION_WEIGHTS, ScoreBoard } from "@/components/results/ScoreBoard";
import { StoryTimeline } from "@/components/results/StoryTimeline";
import { VersionsPanel } from "@/components/results/VersionsPanel";
import { Sidebar } from "@/components/Sidebar";
import { Sheet, SheetContent, SheetTitle } from "@/components/ui/sheet";
import { getMeta } from "@/lib/api";
import { messageFor } from "@/lib/errors";
import { retryLast, runAnalyzeAndTailor } from "@/lib/flow";
import { useAppStore } from "@/lib/store";
import type { Meta, ScoreKey } from "@/lib/types";

type Tab = "fixes" | "evidence" | "resume" | "changes" | "letter" | "versions";
const EMPLOYER: Record<string, string> = {
  product_startup: "Product / startup", it_services: "IT services", gcc: "GCC", consulting_mba: "Consulting",
  bfsi: "BFSI", psu_govt: "PSU / Govt", other: "Other",
};

export default function Home() {
  const s = useAppStore();
  const [meta, setMeta] = useState<Meta>();
  const [tab, setTab] = useState<Tab>("fixes");
  const [focus, setFocus] = useState<ScoreKey | "all">("all");
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
  const running = s.busy !== "idle";
  const streaming = s.busy === "tailoring" && s.streamingItems.length > 0;
  const region = analysis?.region ?? s.inputs.region;
  const showForm = editing || !started;

  const newAnalysis = () => {
    s.reset();
    s.setInput("jd", "");
    s.setInput("file", null);
    setTab("fixes");
    setFocus("all");
    setEditing(true);
  };
  const focusScore = (k: ScoreKey | "all") => { setFocus(k); setTab("fixes"); };
  const sidebar = (onNavigate?: () => void) => <Sidebar onNew={newAnalysis} onHowWeScore={() => setHow(true)} onNavigate={onNavigate} />;

  return (
    <div className="flex min-h-screen justify-center p-0 lg:p-3">
      <div className="flex w-full flex-col border-rule bg-shell lg:grid lg:h-[calc(100vh-24px)] lg:grid-cols-[246px_minmax(0,1fr)] lg:overflow-hidden lg:rounded-sm lg:border">
        <aside aria-label="Navigation" className="hidden border-r border-rule-section bg-rail lg:block lg:overflow-y-auto">
          {sidebar()}
        </aside>

        <div className="sticky top-0 z-30 flex items-center gap-3 border-b border-rule-section bg-shell px-4 py-3 lg:hidden">
          <button type="button" onClick={() => setNav(true)} aria-label="Open menu" className="grid h-11 w-11 flex-none place-items-center rounded-lg border border-rule-control text-ink-3 transition-colors hover:border-gold hover:text-ink">
            <Menu className="h-4 w-4" />
          </button>
          <FileSearch className="h-4 w-4 text-gold" aria-hidden />
          <span className="text-lg">Shortlist</span>
        </div>

        <div id="work" className="min-h-0 lg:overflow-y-auto">
          <div className={showForm ? "mx-auto max-w-6xl p-4 sm:p-6 lg:px-8 lg:py-7" : "grid gap-5 p-4 sm:p-6 lg:px-8 lg:py-7 xl:grid-cols-[minmax(0,1fr)_340px]"}>
            {showForm ? (
              <InputPanel meta={meta} onSubmitted={() => setEditing(false)} />
            ) : (
              <>
                <main id="results" className="flex min-w-0 scroll-mt-4 flex-col gap-5">
                  <header className="flex flex-wrap items-end justify-between gap-4 pt-1">
                    <div className="min-w-0">
                      <h1 className="text-2xl leading-tight font-medium tracking-tight text-balance">
                        {(jd?.title ?? s.inputs.jd.trim().split("\n")[0]?.slice(0, 90) ?? "Analysis").replace(/-(?=\w)/g, "\u2011")}
                      </h1>
                      <p className="mt-1.5 text-sm text-ink-3">
                        {[jd?.company, jd?.location, jd && EMPLOYER[jd.employer_type], s.inputs.file?.name, region === "india" ? "Scored for India" : "Scored for international hiring"]
                          .filter(Boolean).join("  ·  ")}
                      </p>
                    </div>
                    <div className="flex gap-2">
                      <OutlineButton onClick={() => setEditing(true)} disabled={running}><Pencil className="size-3.5" aria-hidden />Edit</OutlineButton>
                      <OutlineButton tone="gold" onClick={newAnalysis} disabled={running}><Plus className="size-3.5" aria-hidden />New</OutlineButton>
                    </div>
                  </header>

                  {(running || s.error) && <StageTimeline />}
                  {s.error && (
                    <div role="alert" className="card flex flex-wrap items-center justify-between gap-3 border-down/30! p-4">
                      <p className="text-sm text-ink-2">{messageFor(s.error.code)}</p>
                      {s.error.retryable && <OutlineButton onClick={() => void retryLast()}>Try again</OutlineButton>}
                    </div>
                  )}
                  {analysis && analysis.jd.suggested_region !== analysis.region && !running && (
                    <div className="card flex flex-wrap items-center justify-between gap-3 p-4">
                      <p className="text-sm text-ink-2">
                        This job looks {analysis.jd.suggested_region === "india" ? "India-based" : "based outside India"}{analysis.jd.location ? ` (${analysis.jd.location})` : ""}.
                      </p>
                      <OutlineButton tone="gold" onClick={() => { s.setInput("region", analysis.jd.suggested_region); void runAnalyzeAndTailor(); }}>
                        Score for {analysis.jd.suggested_region === "india" ? "India" : "International"}
                      </OutlineButton>
                    </div>
                  )}
                  {s.warnings.includes("NOT_A_JD") && <p className="text-sm text-gold">{messageFor("NOT_A_JD")}</p>}

                  {scores && (
                    <ScoreBoard before={scores} after={version?.scores} region={region} focus={focus} onFocus={focusScore} onHowWeScore={() => setHow(true)} />
                  )}
                  {analysis?.profile && !running && <ClarifyCard key={s.sessionId} profile={analysis.profile} />}

                  {(jd || streaming) && (
                    <section className="card flex flex-col gap-5 p-5 sm:p-6">
                      <LedgerTabs
                        label="Results"
                        value={tab}
                        onChange={setTab}
                        tabs={[
                          { value: "fixes", label: "Fixes" },
                          { value: "evidence", label: "Evidence" },
                          { value: "resume", label: "Tailored resume", badge: version?.flags.length ? <span className="tabular-nums">{version.flags.length}</span> : undefined },
                          { value: "changes", label: "Changes" },
                          { value: "letter", label: "Cover letter" },
                          { value: "versions", label: "Versions", badge: s.versions.length > 1 ? <span className="tabular-nums">{s.versions.length}</span> : undefined },
                        ]}
                      />
                      <div role="tabpanel" id={`panel-${tab}`} aria-labelledby={`tab-${tab}`} className="min-h-[280px]">
                        {tab === "fixes" && (scores && insights ? (
                          <div className="flex flex-col gap-5">
                            {focus === "story" && analysis?.profile && <StoryTimeline profile={analysis.profile} />}
                            <FixesPanel scores={version?.scores ?? scores} insights={insights} focus={focus} onFocus={setFocus} />
                          </div>
                        ) : <p className="text-sm text-ink-3">Fixes appear once scoring finishes.</p>)}
                        {tab === "evidence" && (jd && evidence ? <RequirementLedger jd={jd} evidence={evidence} /> : <p className="text-sm text-ink-3">Matching evidence…</p>)}
                        {tab === "resume" && (streaming ? <StreamingPreview items={s.streamingItems} /> : version ? (
                          <div className="flex flex-col gap-6">
                            <div className="flex flex-wrap items-center justify-between gap-3">
                              <p className="max-w-xl text-sm text-ink-3">
                                {version.flags.length ? `${version.flags.length} line(s) state something we couldn't find in your original. Check each, or use the original.` : "Every fact traces back to your original resume."} Highlighted words are terms from the job description.
                              </p>
                              <DownloadMenu request={{ kind: "resume", region: analysis!.region, resume: version.resume }} />
                            </div>
                            <ResumeView resume={version.resume} flags={version.flags} onRevert={(id) => s.revertFlag(version.id, id)}
                              terms={jd ? [...jd.ats_keywords, ...jd.requirements.flatMap((q) => q.keywords)] : []} />
                          </div>
                        ) : <p className="text-sm text-ink-3">The tailored resume appears once analysis finishes.</p>)}
                        {tab === "changes" && (version && analysis ? <DiffView before={analysis.resume} after={version.resume} changes={version.changes} /> : <p className="text-sm text-ink-3">No tailored version yet.</p>)}
                        {tab === "letter" && <CoverLetterPanel />}
                        {tab === "versions" && <VersionsPanel />}
                      </div>
                    </section>
                  )}
                </main>

                <aside aria-label="Insights" className="flex min-w-0 flex-col gap-5 xl:pt-[74px]">
                  {insights && <InsightsRail insights={insights} />}
                </aside>
              </>
            )}
          </div>
        </div>
      </div>

      <Sheet open={nav} onOpenChange={setNav}>
        <SheetContent side="left" className="w-[86%] max-w-xs border-r border-rule-section bg-rail p-0">
          <SheetTitle className="sr-only">Menu</SheetTitle>
          {sidebar(() => setNav(false))}
        </SheetContent>
      </Sheet>
      <HowWeScoreSheet open={how} onOpenChange={setHow} weights={scores?.weights ?? REGION_WEIGHTS[region]} />
    </div>
  );
}
