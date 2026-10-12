"use client";

import { useAppStore } from "@/lib/store";
import { STAGES, type StageId } from "@/lib/types";
import { cn } from "@/lib/utils";

const NAMES: Record<StageId, string> = {
  parsing: "Read", understanding: "Understand", matching: "Match", scoring: "Score",
  tailoring: "Tailor", verifying: "Verify", rescoring: "Re-score",
};

/** The pipeline as a ruled route: each station lights as the stream reaches it. */
export function StageTimeline() {
  const stages = useAppStore((s) => s.stages);
  if (Object.values(stages).every((s) => s === "idle")) return null;
  return (
    <ol aria-label="Progress" className="grid grid-cols-4 gap-y-4 sm:grid-cols-7">
      {STAGES.map((id, i) => {
        const st = stages[id];
        return (
          <li key={id} className="relative flex flex-col gap-2" aria-current={st === "active" ? "step" : undefined}>
            <div className="flex items-center">
              <span
                className={cn(
                  "relative z-10 size-2.5 rounded-full border",
                  st === "done" && "border-gold bg-gold",
                  st === "active" && "border-gold bg-transparent after:absolute after:-inset-1.5 after:animate-ping after:rounded-full after:border after:border-gold/60",
                  st === "error" && "border-down bg-down",
                  st === "idle" && "border-rule-control",
                )}
              />
              {i < STAGES.length - 1 && <span className={cn("h-px flex-1", st === "done" ? "bg-gold/50" : "bg-rule")} />}
            </div>
            <span className={cn("pr-2 text-[11px] font-semibold tracking-[0.12em] uppercase", st === "idle" ? "text-ink-3/70" : st === "error" ? "text-down" : "text-ink-2")}>
              {NAMES[id]}
            </span>
          </li>
        );
      })}
    </ol>
  );
}
