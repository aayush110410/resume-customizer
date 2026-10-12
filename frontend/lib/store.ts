import { create } from "zustand";
import {
  STAGES,
  type AppErrorInfo,
  type Analysis,
  type Evidence,
  type Insights,
  type JDAnalysis,
  type ResumeDoc,
  type ScoreReport,
  type StageId,
  type StageStatus,
  type StreamEvent,
  type TailoredVersion,
  type TailorItem,
} from "@/lib/types";

interface Partial_ {
  resume?: ResumeDoc;
  jd?: JDAnalysis;
  evidence?: Evidence;
  scores?: ScoreReport;
  insights?: Insights;
}

interface AppState {
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
  setError: (e: AppErrorInfo | undefined) => void;
  reset: () => void;
}

const idleStages = () => Object.fromEntries(STAGES.map((s) => [s, "idle"])) as Record<StageId, StageStatus>;
const perRun = () => ({ stages: idleStages(), streamingItems: [] as TailorItem[], error: undefined, warnings: [] as string[] });

export const useAppStore = create<AppState>()((set, get) => ({
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
  setError: (error) => set({ error }),
  reset: () => set({ runId: 0, partial: {}, analysis: undefined, versions: [], activeVersionId: undefined, coverLetter: "", ...perRun() }),
}));
