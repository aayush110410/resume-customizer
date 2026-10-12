import { create } from "zustand";
import {
  DEFAULT_SECTIONS,
  STAGES,
  type AppErrorInfo,
  type Analysis,
  type Evidence,
  type Insights,
  type JDAnalysis,
  type Region,
  type ResumeDoc,
  type SectionKey,
  type ScoreReport,
  type StageId,
  type StageStatus,
  type StreamEvent,
  type TailoredVersion,
  type TailorItem,
  type Tone,
} from "@/lib/types";

interface Partial_ {
  resume?: ResumeDoc;
  jd?: JDAnalysis;
  evidence?: Evidence;
  scores?: ScoreReport;
  insights?: Insights;
}

export interface Inputs {
  jd: string;
  file: File | null;
  region: Region;
  sections: SectionKey[];
  tone: Tone;
  model: string | null;
}
export type Busy = "idle" | "analyzing" | "tailoring" | "letter";

interface AppState {
  inputs: Inputs;
  busy: Busy;
  sessionId?: string;
  sessionStartedAt?: string;
  setInput: <K extends keyof Inputs>(key: K, value: Inputs[K]) => void;
  setBusy: (b: Busy) => void;
  setAnalysis: (a: Analysis) => void;
  setCoverLetter: (t: string) => void;
  resetSession: () => void;
  hydrate: (h: { id: string; created_at: string; analysis: Analysis; versions: TailoredVersion[]; cover_letter: string }) => void;
  runId: number;
  stages: Record<StageId, StageStatus>;
  partial: Partial_;
  analysis?: Analysis;
  streamingItems: TailorItem[];
  versions: TailoredVersion[];
  activeVersionId?: string;
  coverLetter: string;
  error?: AppErrorInfo;
  warnings: string[];
  startRun: () => number;
  applyEvent: (runId: number, e: StreamEvent) => void;
  addVersion: (v: TailoredVersion) => void;
  setActiveVersion: (id: string) => void;
  revertFlag: (versionId: string, targetId: string) => void;
  setError: (e: AppErrorInfo | undefined) => void;
  reset: () => void;
}

const idleStages = () => Object.fromEntries(STAGES.map((s) => [s, "idle"])) as Record<StageId, StageStatus>;
const perRun = () => ({ stages: idleStages(), streamingItems: [] as TailorItem[], error: undefined, warnings: [] as string[] });

const newId = () => (typeof crypto !== "undefined" && "randomUUID" in crypto ? crypto.randomUUID().slice(0, 8) : String(Date.now()));

export const useAppStore = create<AppState>()((set, get) => ({
  inputs: { jd: "", file: null, region: "india", sections: DEFAULT_SECTIONS, tone: "balanced", model: null },
  busy: "idle",
  setInput: (key, value) => set((s) => ({ inputs: { ...s.inputs, [key]: value } })),
  setBusy: (busy) => set({ busy }),
  setAnalysis: (analysis) => set({ analysis }),
  setCoverLetter: (coverLetter) => set({ coverLetter }),
  resetSession: () =>
    set({ sessionId: newId(), sessionStartedAt: new Date().toISOString(), partial: {}, analysis: undefined, versions: [],
          activeVersionId: undefined, coverLetter: "" }),
  hydrate: (h) =>
    set({ sessionId: h.id, sessionStartedAt: h.created_at, analysis: h.analysis, partial: {}, versions: h.versions,
          activeVersionId: h.versions.at(-1)?.id, coverLetter: h.cover_letter, ...perRun(), runId: get().runId + 1, busy: "idle",
          inputs: { ...get().inputs, region: h.analysis.region } }),
  runId: 0,
  partial: {},
  versions: [],
  coverLetter: "",
  ...perRun(),

  startRun: () => {
    const runId = get().runId + 1;
    set({ runId, ...perRun() });
    return runId;
  },

  applyEvent: (runId, { event, data }) => {
    if (runId !== get().runId) return; // a newer run owns the screen
    const d = data as Record<string, unknown>;
    switch (event) {
      case "stage":
        set((s) => ({ stages: { ...s.stages, [d.id as StageId]: d.status as StageStatus } }));
        break;
      case "resume":
      case "jd":
      case "evidence":
      case "scores":
      case "insights":
        set((s) => ({ partial: { ...s.partial, [event]: data } }));
        break;
      case "warning":
        set((s) => ({ warnings: [...s.warnings, d.code as string] }));
        break;
      case "item":
        set((s) => ({ streamingItems: [...s.streamingItems, data as TailorItem] }));
        break;
      case "token":
        set((s) => ({ coverLetter: s.coverLetter + (d.text as string) }));
        break;
      case "error":
        set((s) => ({
          error: data as AppErrorInfo,
          stages: Object.fromEntries(
            Object.entries(s.stages).map(([k, v]) => [k, v === "active" ? "error" : v]),
          ) as Record<StageId, StageStatus>,
        }));
        break;
    }
  },

  addVersion: (v) => set((s) => ({ versions: [...s.versions, v], activeVersionId: v.id })),
  setActiveVersion: (id) => set({ activeVersionId: id }),
  revertFlag: (versionId, targetId) =>
    set((s) => {
      const original = s.analysis?.resume;
      if (!original) return {};
      const originalText = new Map(
        [...original.experience, ...original.projects, ...original.education, ...original.other_sections]
          .flatMap((e) => e.bullets).concat(original.achievements).map((b) => [b.id, b.text]),
      );
      return {
        versions: s.versions.map((v) => {
          if (v.id !== versionId) return v;
          const r = structuredClone(v.resume);
          if (targetId === "summary") r.summary = original.summary;
          else if (targetId === "skills") r.skills = original.skills;
          else
            for (const b of [...r.experience, ...r.projects, ...r.education, ...r.other_sections].flatMap((e) => e.bullets).concat(r.achievements))
              if (b.id === targetId && originalText.has(b.id)) b.text = originalText.get(b.id)!;
          return { ...v, resume: r, flags: v.flags.filter((f) => f.target_id !== targetId) };
        }),
      };
    }),
  setError: (error) => set({ error }),
  reset: () => set({ runId: 0, partial: {}, analysis: undefined, versions: [], activeVersionId: undefined, coverLetter: "", ...perRun() }),
}));
