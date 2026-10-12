import { beforeEach, describe, expect, it } from "vitest";
import { useAppStore } from "@/lib/store";

beforeEach(() => useAppStore.getState().reset());

describe("useAppStore", () => {
  it("ignores events from a stale run", () => {
    const s = useAppStore.getState();
    const old = s.startRun();
    const cur = s.startRun();
    s.applyEvent(old, { event: "stage", data: { id: "parsing", status: "done" } });
    expect(useAppStore.getState().stages.parsing).toBe("idle");
    s.applyEvent(cur, { event: "stage", data: { id: "parsing", status: "done" } });
    expect(useAppStore.getState().stages.parsing).toBe("done");
  });

  it("accumulates tailor items and clears them on a new run", () => {
    const s = useAppStore.getState();
    const run = s.startRun();
    s.applyEvent(run, { event: "item", data: { type: "summary", text: "S" } });
    s.applyEvent(run, { event: "item", data: { type: "change", target_id: "summary", what: "w", why: "y" } });
    expect(useAppStore.getState().streamingItems).toHaveLength(2);
    s.startRun();
    expect(useAppStore.getState().streamingItems).toHaveLength(0);
  });

  it("records a stream error with its retryable flag and marks the active stage as error", () => {
    const s = useAppStore.getState();
    const run = s.startRun();
    s.applyEvent(run, { event: "stage", data: { id: "matching", status: "active" } });
    s.applyEvent(run, { event: "error", data: { code: "LLM_UNAVAILABLE", message: "busy", retryable: true } });
    const st = useAppStore.getState();
    expect(st.error).toEqual({ code: "LLM_UNAVAILABLE", message: "busy", retryable: true });
    expect(st.stages.matching).toBe("error");
  });

  it("stores partial analysis pieces and the final analysis", () => {
    const s = useAppStore.getState();
    const run = s.startRun();
    s.applyEvent(run, { event: "warning", data: { code: "NOT_A_JD", message: "m" } });
    s.applyEvent(run, { event: "scores", data: { overall: 70, weights: {}, subscores: {}, knockouts: [] } });
    expect(useAppStore.getState().partial.scores?.overall).toBe(70);
    expect(useAppStore.getState().warnings).toEqual(["NOT_A_JD"]);
  });
});

describe("review fixes", () => {
  const resume = (text: string, summary = "S") => ({
    contact: { name: "A", email: null, phone: null, location: null, links: [] }, summary,
    skills: [{ name: "L", items: ["Go"] }],
    experience: [{ id: "exp0", title: "SE", organization: "X", location: null, start: null, end: null, bullets: [{ id: "exp0.b0", text, kind: "other" as const }] }],
    projects: [], education: [], achievements: [], other_sections: [], total_years_experience: 2, level: "junior" as const,
  });

  it("hydrate clears any running state", () => {
    const s = useAppStore.getState();
    const run = s.startRun();
    s.setBusy("tailoring");
    s.applyEvent(run, { event: "item", data: { type: "summary", text: "x" } });
    s.hydrate({ id: "h", created_at: "2026-10-12T00:00:00Z", analysis: { region: "india" } as never, versions: [], cover_letter: "" });
    const st = useAppStore.getState();
    expect(st.busy).toBe("idle");
    expect(st.streamingItems).toEqual([]);
    expect(st.runId).toBeGreaterThan(run);
  });

  it("revertFlag restores the original text and drops the flag", () => {
    const s = useAppStore.getState();
    s.setAnalysis({ resume: resume("Cut latency 30%", "Old summary") } as never);
    s.addVersion({
      id: "v1", created_at: "", settings: { sections: ["experience"], tone: "balanced", model: null }, model: "m", changes: [],
      scores: {} as never, resume: resume("Cut latency 45%", "New 7 years"),
      flags: [{ target_id: "exp0.b0", tokens: ["45%"], reason: "r" }, { target_id: "summary", tokens: ["7"], reason: "r" }],
    });
    s.revertFlag("v1", "exp0.b0");
    s.revertFlag("v1", "summary");
    const v = useAppStore.getState().versions[0];
    expect(v.resume.experience[0].bullets[0].text).toBe("Cut latency 30%");
    expect(v.resume.summary).toBe("Old summary");
    expect(v.flags).toEqual([]);
  });
});
