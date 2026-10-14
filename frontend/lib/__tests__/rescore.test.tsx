import { renderToString } from "react-dom/server";
import { beforeEach, describe, expect, it, vi } from "vitest";
import type { Analysis, RescoreResponse, ResumeDoc } from "@/lib/types";

let release: (r: RescoreResponse) => void = () => {};
vi.mock("@/lib/api", () => ({
  rescore: () => new Promise<RescoreResponse>((res) => { release = res; }),
  analyze: vi.fn(), tailor: vi.fn(), coverLetter: vi.fn(),
}));
vi.mock("@/lib/history", () => ({ saveSession: vi.fn(async () => {}), loadSession: vi.fn() }));
vi.mock("sonner", () => ({ toast: { error: vi.fn() } }));

const { useAppStore } = await import("@/lib/store");
const { runRescore } = await import("@/lib/flow");
const { ResumeView } = await import("@/components/results/ResumeView");

const resume = (level: ResumeDoc["level"]): ResumeDoc => ({
  contact: { name: "T", email: null, phone: null, location: null, links: [] }, summary: null, skills: [],
  experience: [{ id: "brk1", title: "Career break: exam preparation", organization: "", location: null, start: "Aug 2022", end: "Dec 2023", bullets: [] }],
  projects: [], education: [], achievements: [], other_sections: [], total_years_experience: 2, level,
});
const analysis = (overall: number): Analysis => ({
  region: "india", resume: resume("junior"), resume_text: "", jd: {} as Analysis["jd"], evidence: {} as Analysis["evidence"],
  layout: {} as Analysis["layout"], insights: {} as Analysis["insights"], prompt_version: "t", models: {},
  scores: { overall, weights: {}, subscores: {}, knockouts: [] },
  profile: { stage: "early", study_year: null, grad_year: null, stints: [], gaps: [], moves: [], projects: [], questions: [], answers: {}, rules_only: false, as_of: "2026-10" },
});
const response = (overall: number): RescoreResponse => ({
  profile: analysis(overall).profile!, scores: { overall, weights: {}, subscores: {}, knockouts: [] },
  insights: {} as RescoreResponse["insights"], level: "mid",
});

beforeEach(() => useAppStore.setState({ sessionId: "A", analysis: analysis(50) }));

describe("runRescore", () => {
  it("applies scores and the answered level to the open session", async () => {
    const pending = runRescore({});
    release(response(60));
    await pending;
    const a = useAppStore.getState().analysis!;
    expect(a.scores.overall).toBe(60);
    expect(a.resume.level).toBe("mid");
  });

  it("drops a response that arrives after the user opened another session", async () => {
    const pending = runRescore({});
    useAppStore.setState({ sessionId: "B", analysis: analysis(70) });
    release(response(60));
    expect(await pending).toBeUndefined();
    expect(useAppStore.getState().analysis!.scores.overall).toBe(70);
  });
});

describe("ResumeView", () => {
  it("renders an entry without an organisation without a dangling separator", () => {
    const html = renderToString(<ResumeView resume={resume("junior")} flags={[]} terms={[]} />);
    expect(html).toContain("Career break: exam preparation");
    expect(html).not.toMatch(/exam preparation<span[^>]*> · <\/span>/);
  });
});
