"use client";

import { useState } from "react";
import { Loader2 } from "lucide-react";
import { OutlineButton, Segmented, ToggleChip } from "@/components/ledger";
import { ResumeDropzone } from "@/components/input/ResumeDropzone";
import { runAnalyzeAndTailor } from "@/lib/flow";
import { loadSampleResume, SAMPLE_JD } from "@/lib/sample";
import { useAppStore } from "@/lib/store";
import { SECTION_KEYS, type Meta, type Region, type SectionKey, type Tone } from "@/lib/types";
import { cn } from "@/lib/utils";
import { LIMITS, validateInputs } from "@/lib/validation";

export const SECTION_LABEL: Record<SectionKey, string> = {
  summary: "Summary", skills: "Skills", experience: "Experience", projects: "Projects", education: "Education", achievements: "Achievements",
};
export const TONES: { value: Tone; label: string }[] = [
  { value: "conservative", label: "Light touch" }, { value: "balanced", label: "Balanced" }, { value: "bold", label: "Bold" },
];
export const REGIONS: { value: Region; label: string }[] = [{ value: "india", label: "India" }, { value: "international", label: "International" }];

export function InputPanel({ meta, onSubmitted }: { meta?: Meta; onSubmitted?: () => void }) {
  const { inputs, setInput, busy } = useAppStore();
  const [touched, setTouched] = useState(false);
  const errors = validateInputs(inputs);
  const shown = touched ? errors : {};
  const running = busy !== "idle";
  const jdLen = inputs.jd.trim().length;
  const words = inputs.jd.trim() ? inputs.jd.trim().split(/\s+/).length : 0;

  const submit = () => {
    setTouched(true);
    if (errors.jd || errors.file) return;
    void runAnalyzeAndTailor();
    onSubmitted?.();
    if (window.innerWidth < 1024) document.getElementById("results")?.scrollIntoView({ behavior: "smooth" });
  };
  const loadSample = async () => {
    setInput("jd", SAMPLE_JD);
    setInput("file", await loadSampleResume());
    setInput("region", "india");
  };
  const toggleSection = (k: SectionKey) =>
    setInput("sections", inputs.sections.includes(k) ? inputs.sections.filter((s) => s !== k) : [...inputs.sections, k]);
  const writers = meta?.models.filter((m) => m.role === "writer") ?? [];

  return (
    <form onSubmit={(e) => { e.preventDefault(); submit(); }} className="card-lit edge-lit flex flex-col gap-6 p-5 sm:p-7 xl:grid xl:grid-cols-[minmax(0,1.3fr)_minmax(0,1fr)] xl:gap-x-10" noValidate>
      <div className="flex items-center justify-between gap-3 xl:col-span-2">
        <h2 className="text-[22px] font-medium tracking-[-0.018em]">New analysis</h2>
        <OutlineButton tone="gold" onClick={loadSample}>Try a sample</OutlineButton>
      </div>

      <section className="flex flex-col gap-2.5 xl:row-span-1">
        <div className="flex items-baseline justify-between">
          <label htmlFor="jd" className="text-[14px] text-ink-3">Job description</label>
          <span className={cn("figure text-[12px]", jdLen > LIMITS.jdMax ? "text-down" : "text-ink-3")}>
            {words} words · {jdLen.toLocaleString("en-IN")} chars
          </span>
        </div>
        <textarea
          id="jd"
          value={inputs.jd}
          onChange={(e) => setInput("jd", e.target.value)}
          onBlur={() => inputs.jd && setTouched(true)}
          placeholder="Paste the full job posting: role, responsibilities, requirements…"
          aria-invalid={!!shown.jd}
          aria-describedby={shown.jd ? "jd-error" : undefined}
          className={cn(
            "min-h-56 w-full flex-1 resize-y rounded-[14px] xl:min-h-[440px] border bg-[rgba(0,0,0,0.22)] px-4 py-3 text-[13.5px] leading-[1.65] text-ink placeholder:text-ink-3/80",
            "focus:border-gold/60 focus:outline-none",
            shown.jd ? "border-down/60" : "border-rule-control",
          )}
        />
        {shown.jd && <p id="jd-error" className="text-[12.5px] text-down">{shown.jd}</p>}
      </section>

      <div className="flex flex-col gap-6">
      <section className="flex flex-col gap-2.5">
        <span className="text-[14px] text-ink-3">Resume</span>
        <ResumeDropzone file={inputs.file} onFile={(f) => setInput("file", f)} error={shown.file} />
        {shown.file && <p className="text-[12.5px] text-down">{shown.file}</p>}
      </section>

      <section className="flex flex-col gap-2.5">
        <span className="text-[14px] text-ink-3">Hiring market</span>
        <Segmented label="Hiring market" value={inputs.region} options={REGIONS} onChange={(v) => setInput("region", v)} />
        <p className="text-[12.5px] leading-relaxed text-ink-3">
          {inputs.region === "india"
            ? "Indian recruiter norms, by the employer type in the JD."
            : "For applying abroad: personal details, work authorisation, Indian terms."}
        </p>
      </section>

      <section className="flex flex-col gap-2.5">
        <span className="text-[14px] text-ink-3">Sections to tailor</span>
        <div className="flex flex-wrap gap-2">
          {SECTION_KEYS.map((k) => (
            <ToggleChip key={k} on={inputs.sections.includes(k)} onClick={() => toggleSection(k)}>{SECTION_LABEL[k]}</ToggleChip>
          ))}
        </div>
      </section>

      <details className="group border-t border-rule-section pt-4">
        <summary className="eyebrow cursor-pointer list-none hover:text-ink">Advanced · tone and model</summary>
        <div className="mt-4 flex flex-col gap-4">
          <Segmented label="Tone" value={inputs.tone} options={TONES} onChange={(v) => setInput("tone", v)} />
          <label className="flex flex-col gap-2 text-[14px] text-ink-3">
            Writing model
            <select
              value={inputs.model ?? ""}
              onChange={(e) => setInput("model", e.target.value || null)}
              className="min-h-10 rounded-full border border-rule-control bg-shell px-3 text-[13px] text-ink focus:border-gold/60 focus:outline-none"
            >
              <option value="">Automatic (best available)</option>
              {writers.map((m) => <option key={m.id} value={m.id}>{m.id}</option>)}
            </select>
          </label>
        </div>
      </details>

      <button type="submit" disabled={running || inputs.sections.length === 0} className="gold-cta flex min-h-12 w-full items-center justify-center gap-2 text-[12px] font-semibold tracking-[0.22em] uppercase">
        {running && <Loader2 className="size-4 animate-spin" aria-hidden />}
        {busy === "analyzing" ? "Analysing" : busy === "tailoring" ? "Tailoring" : "Analyse & tailor"}
      </button>
      </div>
    </form>
  );
}
