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
