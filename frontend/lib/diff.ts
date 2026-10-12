import { diffWords } from "diff";
import type { Bullet, Entry, ResumeDoc, SectionKey } from "@/lib/types";

export interface DiffRow { id: string; label?: string; before: string | null; after: string | null; moved: number; changed: boolean }
export interface DiffSection { key: SectionKey | "other"; title: string; rows: DiffRow[] }

function bulletRows(before: Bullet[], after: Bullet[], label?: string): DiffRow[] {
  const oldIndex = new Map(before.map((b, i) => [b.id, i]));
  const oldText = new Map(before.map((b) => [b.id, b.text]));
  const rows: DiffRow[] = after.map((b, i) => {
    const prev = oldText.get(b.id) ?? null;
    return { id: b.id, label, before: prev, after: b.text, moved: (oldIndex.get(b.id) ?? i) - i, changed: prev !== b.text };
  });
  const kept = new Set(after.map((b) => b.id));
  return rows.concat(before.filter((b) => !kept.has(b.id)).map((b) => ({ id: b.id, label, before: b.text, after: null, moved: 0, changed: true })));
}

function entryRows(before: Entry[], after: Entry[]): DiffRow[] {
  const prev = new Map(before.map((e) => [e.id, e]));
  return after.flatMap((e) => bulletRows(prev.get(e.id)?.bullets ?? [], e.bullets, `${e.title} — ${e.organization}`));
}

/** Aligns two versions of the same resume by stable bullet IDs, so reorders and rewrites are both visible. */
export function alignResumes(original: ResumeDoc, tailored: ResumeDoc): DiffSection[] {
  const sections: DiffSection[] = [
    {
      key: "summary", title: "Summary",
      rows: [{ id: "summary", before: original.summary, after: tailored.summary, moved: 0, changed: (original.summary ?? "") !== (tailored.summary ?? "") }],
    },
  ];
  const oldSkills = new Map(original.skills.map((g) => [g.name, g.items.join(", ")]));
  const names = [...new Set([...tailored.skills.map((g) => g.name), ...original.skills.map((g) => g.name)])];
  const newSkills = new Map(tailored.skills.map((g) => [g.name, g.items.join(", ")]));
  sections.push({
    key: "skills", title: "Skills",
    rows: names.map((n) => ({
      id: `skills:${n}`, label: n, before: oldSkills.get(n) ?? null, after: newSkills.get(n) ?? null, moved: 0,
      changed: oldSkills.get(n) !== newSkills.get(n),
    })),
  });
  for (const [key, title] of [["experience", "Experience"], ["projects", "Projects"], ["education", "Education"]] as const) {
    sections.push({ key, title, rows: entryRows(original[key], tailored[key]) });
  }
  sections.push({ key: "achievements", title: "Achievements", rows: bulletRows(original.achievements, tailored.achievements) });
  const kept = new Map(tailored.other_sections.map((o) => [o.id, o]));
  sections.push({
    key: "other", title: "Other sections",
    rows: original.other_sections.flatMap((o) => bulletRows(o.bullets, kept.get(o.id)?.bullets ?? [], o.name)),
  });
  return sections.filter((s) => s.rows.length > 0);
}

export function wordDiff(a: string, b: string): { value: string; added?: boolean; removed?: boolean }[] {
  return diffWords(a, b).map((p) => ({ value: p.value, added: p.added, removed: p.removed }));
}
