import "fake-indexeddb/auto";
import { beforeEach, describe, expect, it, vi } from "vitest";
import type { StreamEvent } from "@/lib/types";

const calls = { analyze: 0, tailor: 0 };
vi.mock("sonner", () => ({ toast: { error: vi.fn(), success: vi.fn() } }));
vi.mock("@/lib/api", () => ({
  analyze: vi.fn(async (_f: File, jd: string, _r: string, onEvent: (e: StreamEvent) => void, signal: AbortSignal) => {
    calls.analyze++;
    if (jd.startsWith("slow")) await new Promise((r) => setTimeout(r, 30));
    if (signal.aborted) throw new DOMException("aborted", "AbortError");
    onEvent({ event: "done", data: { analysis: { region: "india", jd: { title: jd }, scores: { overall: 50 }, resume: {} } } });
  }),
  tailor: vi.fn(async (a: { jd: { title: string } }, _s: unknown, onEvent: (e: StreamEvent) => void) => {
    calls.tailor++;
    onEvent({ event: "done", data: { version: { id: `v-${a.jd.title}`, scores: { overall: 70 } } } });
  }),
  coverLetter: vi.fn(),
}));

import { retryLast, runAnalyzeAndTailor } from "@/lib/flow";
import { useAppStore } from "@/lib/store";

const file = new File(["x"], "cv.pdf", { type: "application/pdf" });

beforeEach(() => {
  calls.analyze = calls.tailor = 0;
  useAppStore.getState().reset();
  useAppStore.getState().setInput("file", file);
});

describe("flow", () => {
  it("a re-submit wins: the slow first run never writes into the new session", async () => {
    useAppStore.getState().setInput("jd", "slow-old");
    const first = runAnalyzeAndTailor();
    useAppStore.getState().setInput("jd", "new");
    await runAnalyzeAndTailor();
    await first;
    const st = useAppStore.getState();
    expect(st.analysis?.jd.title).toBe("new");
    expect(st.versions.map((v) => v.id)).toEqual(["v-new"]);
    expect(st.busy).toBe("idle");
  });

  it("retry re-runs only tailoring when the analysis already exists", async () => {
    useAppStore.getState().setInput("jd", "new");
    useAppStore.getState().setAnalysis({ region: "india", jd: { title: "kept" }, scores: { overall: 50 } } as never);
    await retryLast();
    expect(calls.analyze).toBe(0);
    expect(calls.tailor).toBe(1);
  });
});
