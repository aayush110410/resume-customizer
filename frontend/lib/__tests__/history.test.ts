import "fake-indexeddb/auto";
import { beforeEach, describe, expect, it } from "vitest";
import { clear } from "idb-keyval";
import { deleteSession, listSessions, loadSession, saveSession, type SessionRecord } from "@/lib/history";

const rec = (i: number): SessionRecord =>
  ({
    id: `s${i}`, created_at: new Date(Date.UTC(2026, 9, 12, 0, i)).toISOString(), jd_title: `Role ${i}`, region: "india",
    analysis: { scores: { overall: 50 + (i % 10) } }, versions: [{ scores: { overall: 70 } }], cover_letter: "",
  }) as unknown as SessionRecord;

beforeEach(() => clear());

describe("history", () => {
  it("prunes to the 20 newest sessions, newest first", async () => {
    for (let i = 0; i < 22; i++) await saveSession(rec(i));
    const list = await listSessions();
    expect(list).toHaveLength(20);
    expect(list[0]).toMatchObject({ id: "s21", jd_title: "Role 21", best_overall: 70 });
    expect(list.at(-1)!.id).toBe("s2");
  });
  it("round-trips and deletes a session", async () => {
    await saveSession(rec(1));
    expect((await loadSession("s1"))?.versions).toHaveLength(1);
    await deleteSession("s1");
    expect(await loadSession("s1")).toBeUndefined();
  });
});
