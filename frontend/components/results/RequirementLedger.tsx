import { Chip, Label, StatusChip } from "@/components/ledger";
import type { Evidence, JDAnalysis } from "@/lib/types";

const IMPORTANCE = { must: "Must", should: "Should", nice: "Nice" } as const;

export function RequirementLedger({ jd, evidence }: { jd: JDAnalysis; evidence: Evidence }) {
  const byId = new Map(evidence.matches.map((m) => [m.requirement_id, m]));
  return (
    <section aria-label="Requirements">
      <div className="flex flex-wrap items-baseline justify-between gap-2">
        <h3 className="text-xl font-medium tracking-tight">Requirement ledger</h3>
        <span className="text-sm text-ink-3">
          {jd.title}{jd.company ? ` · ${jd.company}` : ""} · {jd.employer_type.replace("_", " ")} · {jd.seniority}
        </span>
      </div>
      <div className="mt-4 hidden grid-cols-[minmax(0,1.1fr)_64px_92px_minmax(0,1.6fr)] gap-4 border-b border-rule pb-2 md:grid">
        <Label>Requirement</Label><Label>Weight</Label><Label>Status</Label><Label>Evidence from your resume</Label>
      </div>
      <ul>
        {jd.requirements.map((r) => {
          const m = byId.get(r.id);
          return (
            <li key={r.id} className="grid gap-x-4 gap-y-1.5 border-b border-rule-section py-3 md:grid-cols-[minmax(0,1.1fr)_64px_92px_minmax(0,1.6fr)]">
              <span className="text-sm text-ink">{r.text}</span>
              <span className="text-sm text-ink-3">{IMPORTANCE[r.importance]}</span>
              <span>{m ? <StatusChip status={m.status} /> : <StatusChip status="missing" />}</span>
              <span className="text-sm leading-relaxed text-ink-2">
                {m?.quote ? <q className="text-ink-2">{m.quote}</q> : <span className="text-ink-3">{m?.rationale ?? "Not assessed"}</span>}
                {m && !m.verified && <span className="ml-2"><Chip tone="gold" title="The quoted text couldn't be found in your resume, so this was downgraded">unverified</Chip></span>}
              </span>
            </li>
          );
        })}
      </ul>
    </section>
  );
}
