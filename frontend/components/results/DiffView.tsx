"use client";

import { useState } from "react";
import { ArrowDown, ArrowUp } from "lucide-react";
import { Label, Segmented } from "@/components/ledger";
import { alignResumes, wordDiff, type DiffRow } from "@/lib/diff";
import type { ChangeItem, ResumeDoc } from "@/lib/types";
import { cn } from "@/lib/utils";

function Inline({ row }: { row: DiffRow }) {
  if (row.after === null) return <span className="text-down line-through decoration-down/60">{row.before}</span>;
  if (row.before === null) return <span className="text-up">{row.after}</span>;
  return (
    <>
      {wordDiff(row.before, row.after).map((p, i) => (
        <span key={i} className={cn(p.added && "bg-up/10 text-up", p.removed && "text-down/80 line-through decoration-down/50")}>{p.value}</span>
      ))}
    </>
  );
}

export function DiffView({ before, after, changes = [], onlyChanged = true }: {
  before: ResumeDoc; after: ResumeDoc; changes?: ChangeItem[]; onlyChanged?: boolean;
}) {
  const [mode, setMode] = useState<"inline" | "split">("inline");
  const why = new Map(changes.map((c) => [c.target_id, c]));
  const sections = alignResumes(before, after)
    .map((s) => ({ ...s, rows: onlyChanged ? s.rows.filter((r) => r.changed || r.moved) : s.rows }))
    .filter((s) => s.rows.length);
  const total = sections.reduce((n, s) => n + s.rows.length, 0);

  return (
    <div className="flex flex-col gap-6">
      <div className="flex flex-wrap items-center justify-between gap-3">
        <span className="text-[13.5px] text-ink-3"><span className="figure text-ink">{total}</span> lines changed or moved</span>
        <div className="w-56"><Segmented label="Diff layout" value={mode} onChange={setMode} options={[{ value: "inline", label: "Inline" }, { value: "split", label: "Side by side" }]} /></div>
      </div>
      {total === 0 && <p className="text-[13.5px] text-ink-3">No differences.</p>}
      {sections.map((s) => (
        <section key={s.key}>
          <Label>{s.title}</Label>
          <ul className="mt-1">
            {s.rows.map((r) => {
              const c = why.get(r.id) ?? (r.id === "summary" ? why.get("summary") : r.id.startsWith("skills:") ? why.get("skills") : undefined);
              return (
                <li key={r.id} className="border-t border-rule-section py-3">
                  {r.label && <div className="mb-1 text-[12px] text-ink-3">{r.label}</div>}
                  <div className="flex gap-3">
                    {r.moved !== 0 && (
                      <span className="figure mt-0.5 inline-flex h-fit shrink-0 items-center gap-0.5 border border-gold-dim/50 px-1.5 text-[11px] text-gold" title={`Moved ${Math.abs(r.moved)} position(s)`}>
                        {r.moved > 0 ? <ArrowUp className="size-3" aria-hidden /> : <ArrowDown className="size-3" aria-hidden />}{Math.abs(r.moved)}
                      </span>
                    )}
                    {mode === "inline" ? (
                      <p className="text-[13.5px] leading-[1.65] text-ink-2"><Inline row={r} /></p>
                    ) : (
                      <div className="grid flex-1 gap-3 sm:grid-cols-2">
                        <p className="text-[13.5px] leading-[1.65] text-ink-3">{r.before ?? "—"}</p>
                        <p className="text-[13.5px] leading-[1.65] text-ink">{r.after ?? <span className="text-down">Removed</span>}</p>
                      </div>
                    )}
                  </div>
                  {c && <p className="mt-1.5 text-[12.5px] leading-relaxed text-gold-dim">Why: {c.why}</p>}
                </li>
              );
            })}
          </ul>
        </section>
      ))}
    </div>
  );
}
