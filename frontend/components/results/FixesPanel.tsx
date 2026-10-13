import { Chip, Delta } from "@/components/ledger";
import { buildFixes, keywordGain } from "@/lib/fixes";
import type { Insights, ScoreKey, ScoreReport } from "@/lib/types";
import { cn } from "@/lib/utils";

const SOURCE: Record<ScoreKey, string> = { match: "JD match", ats: "ATS", quality: "Content", region: "Region fit" };

export function FixesPanel({ scores, insights, focus, onFocus }: {
  scores: ScoreReport; insights: Insights; focus: ScoreKey | "all"; onFocus: (k: ScoreKey | "all") => void;
}) {
  const all = buildFixes(scores, insights);
  const shown = focus === "all" ? all : all.filter((f) => f.source === focus);
  const filters: (ScoreKey | "all")[] = ["all", "match", "ats", "quality", "region"];
  return (
    <div className="flex flex-col gap-5">
      <div className="flex flex-wrap gap-2" role="group" aria-label="Filter fixes">
        {filters.map((k) => {
          const n = k === "all" ? all.length : all.filter((f) => f.source === k).length;
          return (
            <button
              key={k}
              type="button"
              aria-pressed={focus === k}
              onClick={() => onFocus(k)}
              className={cn(
                "min-h-9 rounded-full border px-3.5 text-[13px] transition-colors duration-300",
                focus === k ? "border-[rgba(217,189,139,0.28)] bg-[rgba(217,189,139,0.14)] text-gold" : "border-rule-control text-ink-3 hover:text-ink",
              )}
            >
              {k === "all" ? "All" : SOURCE[k]} <span className="figure text-ink-3">{n}</span>
            </button>
          );
        })}
      </div>

      {insights.missing_keywords.length > 0 && (focus === "all" || focus === "ats") && (
        <div className="grid grid-cols-[minmax(0,1fr)_auto] gap-x-6 rounded-[14px] border border-rule-control px-4 py-3.5">
          <div className="min-w-0">
            <p className="text-[14px] text-ink">{insights.missing_keywords.length} job keywords never appear in your resume</p>
            <p className="mt-1 text-[13px] text-ink-3">Add the ones you genuinely have, inside an experience or project bullet.</p>
            <div className="mt-2.5 flex flex-wrap gap-1.5">{insights.missing_keywords.map((k) => <Chip key={k}>{k}</Chip>)}</div>
          </div>
          <div className="flex flex-col items-end gap-1 pt-0.5">
            <Delta value={keywordGain(scores)} />
            <span className="text-[11.5px] text-ink-3">ATS</span>
          </div>
        </div>
      )}

      {shown.length === 0 ? (
        <p className="text-[13.5px] text-ink-3">Nothing to fix here.</p>
      ) : (
        <ol>
          {shown.map((f, i) => (
            <li key={`${f.source}-${i}`} className="ledger-row grid grid-cols-[minmax(0,1fr)_auto] gap-x-6 border-t border-rule-section py-3.5">
              <div className="min-w-0">
                <p className="text-[14px] leading-snug text-ink">{f.title}</p>
                <p className="mt-1 text-[13px] leading-relaxed text-ink-3">{f.detail}</p>
                {f.suggested_bullet && (
                  <p className="mt-2 flex flex-wrap items-start gap-2 text-[13px] leading-relaxed text-ink-2">
                    <Chip tone="gold">Add only if true</Chip>
                    <span>{f.suggested_bullet}</span>
                  </p>
                )}
              </div>
              <div className="flex flex-col items-end gap-1 pt-0.5">
                <Delta value={f.gain} />
                <span className="text-[11.5px] text-ink-3">{SOURCE[f.source]}</span>
              </div>
            </li>
          ))}
        </ol>
      )}
    </div>
  );
}
