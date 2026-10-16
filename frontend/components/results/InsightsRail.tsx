import { CardTitle } from "@/components/ledger";
import type { Insights } from "@/lib/types";
import { cn } from "@/lib/utils";

const VERDICT = { shortlist: "Shortlist", maybe: "Maybe", reject: "Reject" } as const;

export function InsightsRail({ insights }: { insights: Insights }) {
  const v = insights.recruiter;
  return (
    <div className="flex flex-col gap-5">
      <section aria-label="Recruiter's first scan" className="card p-5">
        <CardTitle>First impression</CardTitle>
        <p className={cn("mt-3 text-2xl font-medium tracking-tight",
          v.decision === "shortlist" ? "text-up" : v.decision === "reject" ? "text-down" : "text-gold")}>
          {VERDICT[v.decision]}
        </p>
        <p className="mt-2 text-sm leading-relaxed text-ink-2">{v.first_impression}</p>
      </section>

      {insights.tips.length > 0 && (
        <section aria-label="Hiring-market notes" className="card p-5">
          <CardTitle>Market notes</CardTitle>
          <ul className="mt-2">
            {insights.tips.map((t) => <li key={t.tip_id} className="border-t border-rule-section py-3 text-sm leading-relaxed text-ink-2">{t.advice}</li>)}
          </ul>
        </section>
      )}
    </div>
  );
}
