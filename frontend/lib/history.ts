import { del, entries, get, set } from "idb-keyval";
import type { Analysis, Region, TailoredVersion } from "@/lib/types";

export interface SessionRecord {
  id: string; created_at: string; jd_title: string; region: Region;
  analysis: Analysis; versions: TailoredVersion[]; cover_letter: string;
}
export interface SessionSummary { id: string; created_at: string; jd_title: string; region: Region; best_overall: number }

const PREFIX = "session:";
const MAX_SESSIONS = 20;

async function all(): Promise<SessionRecord[]> {
  const rows = await entries<string, SessionRecord>();
  return rows.filter(([k]) => String(k).startsWith(PREFIX)).map(([, v]) => v).sort((a, b) => b.created_at.localeCompare(a.created_at));
}

/** Browser-only history (no login): keeps the newest 20 sessions. */
export async function saveSession(s: SessionRecord): Promise<void> {
  await set(PREFIX + s.id, s);
  const stale = (await all()).slice(MAX_SESSIONS);
  await Promise.all(stale.map((r) => del(PREFIX + r.id)));
}

export async function listSessions(): Promise<SessionSummary[]> {
  return (await all()).map((s) => ({
    id: s.id, created_at: s.created_at, jd_title: s.jd_title, region: s.region,
    best_overall: Math.max(s.analysis.scores.overall, ...s.versions.map((v) => v.scores.overall)),
  }));
}

export const loadSession = (id: string) => get<SessionRecord>(PREFIX + id);
export const deleteSession = (id: string) => del(PREFIX + id);
