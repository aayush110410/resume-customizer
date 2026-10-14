import { renderToString } from "react-dom/server";
import { describe, expect, it } from "vitest";
import { ScoreBoard } from "@/components/results/ScoreBoard";
import { answerSummary, chosenAnswers, pendingAnswers, sameAnswers } from "@/lib/clarify";
import type { Profile, Question, ScoreReport } from "@/lib/types";

const q = (id: string): Question => ({ id, kind: "gap", target_id: id, prompt: id, options: [], allow_text: false, impact: 0 });
const profile = (answers: Record<string, string>): Profile => ({
  stage: "early", study_year: null, grad_year: null, stints: [], gaps: [], moves: [], projects: [],
  questions: [q("stage"), q("gap:2024-06"), q("stint:exp1"), q("name:zephyr"), q("intern:exp2")],
  answers: Object.fromEntries(Object.entries(answers).map(([k, v]) => [k, { value: v, text: null, state_on_resume: false }])),
  rules_only: false, as_of: "2026-10",
});

describe("clarify helpers", () => {
  it("sends only answers to questions that are still asked", () => {
    const ans = { "gap:2024-06": { value: "health", text: null, state_on_resume: false }, "gap:1999-01": { value: "x", text: null, state_on_resume: false } };
    expect(Object.keys(pendingAnswers([q("stage"), q("gap:2024-06")], ans))).toEqual(["gap:2024-06"]);
  });
  it("ignores typed text until an option is picked, and compares answers regardless of key order", () => {
    const a = (value: string, text: string | null = null) => ({ value, text, state_on_resume: false });
    const local = { "name:zephyr": a("", "lead sync"), "gap:2024-06": a("health"), stage: a("mid") };
    const saved = { stage: a("mid"), "gap:2024-06": a("health") };
    expect(Object.keys(chosenAnswers(local)).sort()).toEqual(["gap:2024-06", "stage"]);
    expect(sameAnswers(chosenAnswers(local), saved)).toBe(true);
    expect(sameAnswers({ stage: a("early") }, saved)).toBe(false);
  });
  it("summarises progress", () => {
    expect(answerSummary(profile({ stage: "early", "gap:2024-06": "health", "stint:exp1": "contract" }))).toBe("3 of 5 confirmed");
  });
});

const sub = (key: string, score: number) => ({ key, score, explanations: [] });
const report = (keys: string[]): ScoreReport => ({
  overall: 70, weights: Object.fromEntries(keys.map((k) => [k, 1 / keys.length])),
  subscores: Object.fromEntries(keys.map((k) => [k, sub(k, 70)])) as ScoreReport["subscores"], knockouts: [],
});

describe("ScoreBoard", () => {
  it("shows a Story tile only when the analysis has one (older saved analyses have four scores)", () => {
    const props = { region: "india" as const, focus: "all" as const, onFocus: () => {}, onHowWeScore: () => {} };
    expect(renderToString(<ScoreBoard before={report(["match", "ats", "quality", "region"])} {...props} />)).not.toContain(">Story<");
    expect(renderToString(<ScoreBoard before={report(["match", "ats", "quality", "region", "story"])} {...props} />)).toContain(">Story<");
  });
});
