import type { Insights, ScoreKey, ScoreReport } from "@/lib/types";

export interface Fix { source: ScoreKey; title: string; detail: string; gain: number; suggested_bullet: string | null }

/** One ranked list of everything worth fixing: requirement gaps (with example bullets) plus every scored deduction. */
export function buildFixes(scores: ScoreReport, insights: Insights): Fix[] {
  const gaps: Fix[] = insights.actions
    .filter((a) => a.source === "match")
    .map((a) => ({ source: "match", title: a.title, detail: a.detail, gain: a.est_gain, suggested_bullet: a.suggested_bullet }));
  const deductions: Fix[] = (["ats", "quality", "region", "story"] as const).flatMap((key) =>
    (scores.subscores[key]?.explanations ?? [])
      .filter((e) => e.impact < 0 && e.fix && e.signal !== "missing_keywords")
      .map((e) => ({
        source: key, title: e.detail, detail: e.fix!, suggested_bullet: null,
        gain: Math.round((scores.weights[key] ?? 0) * -e.impact * 10) / 10,
      })),
  );
  return [...gaps, ...deductions].sort((a, b) => b.gain - a.gain);
}

/** Estimated overall gain from adding the missing JD keywords (shown with the keyword chips). */
export function keywordGain(scores: ScoreReport): number {
  const e = scores.subscores.ats?.explanations.find((x) => x.signal === "missing_keywords");
  return e ? Math.round(scores.weights.ats * -e.impact * 10) / 10 : 0;
}
