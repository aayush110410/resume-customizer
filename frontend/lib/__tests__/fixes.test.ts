import { describe, expect, it } from "vitest";
import { buildFixes, keywordGain } from "@/lib/fixes";
import type { Insights, ScoreReport } from "@/lib/types";

const scores = {
  overall: 60, knockouts: [], weights: { match: 0.4, ats: 0.25, quality: 0.2, region: 0.15 },
  subscores: {
    match: { key: "match", score: 50, explanations: [{ signal: "requirement_missing", impact: -20, detail: "Kafka (must-have): missing", fix: "x" }] },
    ats: { key: "ats", score: 80, explanations: [
      { signal: "multi_column", impact: -10, detail: "Two columns", fix: "Use one column" },
      { signal: "missing_keywords", impact: -14, detail: "JD keywords not found: Kafka", fix: "Add them" },
      { signal: "acronym_form", impact: 0, detail: "Only one form", fix: "Write both" },
    ] },
    quality: { key: "quality", score: 70, explanations: [{ signal: "weak_opener", impact: -5, detail: "Weak openers", fix: null }] },
    region: { key: "region", score: 90, explanations: [{ signal: "dob", impact: -5, detail: "Date of birth", fix: "Remove it" }] },
  },
} as unknown as ScoreReport;

const insights = {
  actions: [{ title: "No Kafka evidence", detail: "Add a Kafka bullet", est_gain: 8, source: "match", suggested_bullet: "Built [N] consumers" }],
  tips: [], missing_keywords: [], recruiter: { decision: "maybe", first_impression: "", reasons: [] },
} as unknown as Insights;

describe("buildFixes", () => {
  it("merges match gaps from insights with every scored deduction that has a fix, highest gain first", () => {
    const fixes = buildFixes(scores, insights);
    expect(fixes.map((f) => [f.source, f.title, f.gain])).toEqual([
      ["match", "No Kafka evidence", 8],
      ["ats", "Two columns", 2.5],
      ["region", "Date of birth", 0.8],
    ]);
    expect(fixes[0].suggested_bullet).toBe("Built [N] consumers");
  });
});

describe("keywordGain", () => {
  it("is shown once, with the keyword chips, instead of as a fix row", () => {
    expect(buildFixes(scores, insights).some((f) => f.title.startsWith("JD keywords"))).toBe(false);
    expect(keywordGain(scores)).toBe(3.5);
  });
});
