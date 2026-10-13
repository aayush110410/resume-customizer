import { CardTitle, Chip } from "@/components/ledger";
import type { Insights } from "@/lib/types";
import { cn } from "@/lib/utils";

const VERDICT = { shortlist: "Shortlist", maybe: "Maybe", reject: "Reject" } as const;

export function InsightsRail({ insights }: { insights: Insights }) {
  const v = insights.recruiter;
  return (
    <div className="flex flex-col gap-5">
      <section aria-label="Recruiter's first scan" className="card edge-lit p-5">
        <CardTitle meta="7-second scan">Recruiter&apos;s view</CardTitle>
        <div className={cn("mt-3 text-[29px] font-medium tracking-[-0.018em]",
          v.decision === "shortlist" ? "text-up" : v.decision === "reject" ? "text-down" : "text-gold")}>
          {VERDICT[v.decision]}
        </div>
        <p className="mt-2 text-[13.5px] leading-[1.7] text-ink-2">{v.first_impression}</p>
        <ul className="mt-3">
          {v.reasons.map((r, i) => <li key={i} className="border-t border-rule-section py-2 text-[13px] leading-relaxed text-ink-3">{r}</li>)}
        </ul>
      </section>

      <section aria-label="What to fix first" className="card edge-lit p-5">
        <CardTitle meta="est. overall gain">Fix first</CardTitle>
        <ol className="mt-2">
          {insights.actions.map((a, i) => (
            <li key={i} className="ledger-row border-t border-rule-section py-3">
              <div className="grid grid-cols-[1fr_auto] gap-3">
                <span className="text-[13.5px] leading-snug text-ink">{a.title}</span>
                <span className="figure text-[13px] text-up">+{a.est_gain}</span>
              </div>
              <p className="mt-1 text-[12.5px] leading-relaxed text-ink-3">{a.detail}</p>
              {a.suggested_bullet && (
                <div className="mt-2 flex flex-col items-start gap-1.5">
                  <Chip tone="gold">Add only if true</Chip>
                  <p className="text-[12.5px] leading-relaxed text-ink-2">{a.suggested_bullet}</p>
                </div>
              )}
            </li>
          ))}
        </ol>
      </section>

      {insights.missing_keywords.length > 0 && (
        <section aria-label="Missing keywords" className="card edge-lit p-5">
          <CardTitle meta={`${insights.missing_keywords.length} missing`}>JD keywords</CardTitle>
          <div className="mt-3 flex flex-wrap gap-2">{insights.missing_keywords.map((k) => <Chip key={k}>{k}</Chip>)}</div>
          <p className="mt-2 text-[12px] text-ink-3">Add only the ones you genuinely have, inside a bullet.</p>
        </section>
      )}

      {insights.tips.length > 0 && (
        <section aria-label="Hiring-market tips" className="card edge-lit p-5">
          <CardTitle meta="for this role">Market notes</CardTitle>
          <ul className="mt-2">
            {insights.tips.map((t) => <li key={t.tip_id} className="border-t border-rule-section py-3 text-[13px] leading-[1.7] text-ink-2">{t.advice}</li>)}
          </ul>
        </section>
      )}
    </div>
  );
}
