"use client";

import { useState } from "react";
import { Delta, Label, OutlineButton, Segmented, ToggleChip } from "@/components/ledger";
import { REGIONS, SECTION_LABEL, TONES } from "@/components/input/InputPanel";
import { DiffView } from "@/components/results/DiffView";
import { Dialog, DialogContent, DialogDescription, DialogHeader, DialogTitle } from "@/components/ui/dialog";
import { runNewVersion } from "@/lib/flow";
import { useAppStore } from "@/lib/store";
import { SECTION_KEYS, type SectionKey, type Tone } from "@/lib/types";
import { cn } from "@/lib/utils";

export function VersionsPanel() {
  const { versions, activeVersionId, setActiveVersion, analysis, busy, inputs } = useAppStore();
  const [open, setOpen] = useState(false);
  const [sections, setSections] = useState<SectionKey[]>(inputs.sections);
  const [tone, setTone] = useState<Tone>("bold");
  const [compare, setCompare] = useState<string[]>([]);
  if (!analysis) return null;
  const base = analysis.scores.overall;
  const pair = compare.map((id) => versions.find((v) => v.id === id)).filter(Boolean);

  const toggleCompare = (id: string) =>
    setCompare((c) => (c.includes(id) ? c.filter((x) => x !== id) : [...c.slice(-1), id]));

  return (
    <div className="flex flex-col gap-6">
      <div className="flex flex-wrap items-center justify-between gap-3">
        <p className="text-[13.5px] text-ink-3">Each version re-tailors the same analysis with different sections or tone. Pick two to compare.</p>
        <OutlineButton onClick={() => setOpen(true)} disabled={busy !== "idle"}>New version</OutlineButton>
      </div>
      <ul>
        {versions.map((v, i) => (
          <li key={v.id} className={cn("ledger-row relative grid grid-cols-[auto_1fr_auto] items-center gap-4 border-t border-rule-section py-3",
            v.id === activeVersionId && "bg-gold/[0.04]")}>
            {v.id === activeVersionId && <span className="absolute inset-y-0 left-0 w-0.5 bg-gold" aria-hidden />}
            <input type="checkbox" aria-label={`Compare version ${i + 1}`} checked={compare.includes(v.id)} onChange={() => toggleCompare(v.id)}
              className="size-4 accent-[#d9bd8b]" />
            <button type="button" onClick={() => setActiveVersion(v.id)} className="text-left">
              <div className="text-[14px] text-ink">Version {i + 1} · {TONES.find((t) => t.value === v.settings.tone)?.label}</div>
              <div className="text-[12px] text-ink-3">{v.settings.sections.map((s) => SECTION_LABEL[s]).join(", ")} · {v.flags.length} to confirm</div>
            </button>
            <span className="flex items-baseline gap-2"><span className="figure text-[17px] text-ink">{v.scores.overall}</span><Delta value={v.scores.overall - base} /></span>
          </li>
        ))}
      </ul>

      {pair.length === 2 && (
        <section className="flex flex-col gap-4 border-t border-rule pt-6">
          <Label>Comparing version {versions.indexOf(pair[0]!) + 1} → {versions.indexOf(pair[1]!) + 1}</Label>
          <div className="grid grid-cols-2 border-y border-rule sm:grid-cols-5">
            {(["overall", "match", "ats", "quality", "region"] as const).map((k) => {
              const a = k === "overall" ? pair[0]!.scores.overall : pair[0]!.scores.subscores[k].score;
              const b = k === "overall" ? pair[1]!.scores.overall : pair[1]!.scores.subscores[k].score;
              return (
                <div key={k} className="flex flex-col gap-1 border-l border-rule px-3 py-3 first:border-l-0">
                  <span className="text-[12px] text-ink-3 capitalize">{k}</span>
                  <span className="figure text-[15px] text-ink">{a} → {b} <Delta value={b - a} /></span>
                </div>
              );
            })}
          </div>
          <DiffView before={pair[0]!.resume} after={pair[1]!.resume} changes={pair[1]!.changes} />
        </section>
      )}

      <Dialog open={open} onOpenChange={setOpen}>
        <DialogContent className="border border-rule bg-rail p-7 sm:max-w-lg">
          <DialogHeader>
            <DialogTitle className="text-[21px] font-medium tracking-[-0.018em]">New version</DialogTitle>
            <DialogDescription className="text-[13.5px] text-ink-3">
              Reuses this analysis ({REGIONS.find((r) => r.value === analysis.region)?.label}). Only the rewrite runs again.
            </DialogDescription>
          </DialogHeader>
          <div className="mt-2 flex flex-col gap-5">
            <div className="flex flex-wrap gap-2">
              {SECTION_KEYS.map((k) => (
                <ToggleChip key={k} on={sections.includes(k)} onClick={() => setSections((s) => (s.includes(k) ? s.filter((x) => x !== k) : [...s, k]))}>
                  {SECTION_LABEL[k]}
                </ToggleChip>
              ))}
            </div>
            <Segmented label="Tone" value={tone} options={TONES} onChange={setTone} />
            <OutlineButton
              disabled={!sections.length}
              className="border-gold/60 text-gold"
              onClick={() => { setOpen(false); void runNewVersion({ sections, tone, model: inputs.model }); }}
            >
              Generate version
            </OutlineButton>
          </div>
        </DialogContent>
      </Dialog>
    </div>
  );
}
