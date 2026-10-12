import { describe, expect, it } from "vitest";
import { alignResumes, wordDiff } from "@/lib/diff";
import type { Bullet, ResumeDoc } from "@/lib/types";

const b = (id: string, text: string): Bullet => ({ id, text, kind: "other" });
const doc = (summary: string, bullets: Bullet[], other = true): ResumeDoc => ({
  contact: { name: "A", email: null, phone: null, location: null, links: [] },
  summary, skills: [{ name: "Lang", items: ["Go"] }],
  experience: [{ id: "exp0", title: "SE", organization: "X", location: null, start: null, end: null, bullets }],
  projects: [], education: [], achievements: [],
  other_sections: other ? [{ id: "oth0", name: "Declaration", bullets: [b("oth0.b0", "I declare")] }] : [],
  total_years_experience: 2, level: "junior",
});

describe("alignResumes", () => {
  const orig = doc("Old", [b("exp0.b0", "A"), b("exp0.b1", "B"), b("exp0.b2", "C")]);
  const tail = doc("New", [b("exp0.b2", "C better"), b("exp0.b0", "A"), b("exp0.b1", "B")], false);
  const sections = alignResumes(orig, tail);

  it("aligns reordered bullets and reports movement", () => {
    const rows = sections.find((s) => s.key === "experience")!.rows;
    expect(rows.map((r) => r.id)).toEqual(["exp0.b2", "exp0.b0", "exp0.b1"]);
    expect(rows[0]).toMatchObject({ moved: 2, changed: true, before: "C", after: "C better" });
    expect(rows[1]).toMatchObject({ moved: -1, changed: false });
  });
  it("marks summary rewrite and unchanged skills", () => {
    expect(sections[0].rows[0]).toMatchObject({ id: "summary", changed: true, before: "Old", after: "New" });
    expect(sections.find((s) => s.key === "skills")!.rows[0]).toMatchObject({ changed: false });
  });
  it("shows removed sections as deletions", () => {
    expect(sections.find((s) => s.key === "other")!.rows[0]).toMatchObject({ id: "oth0.b0", after: null, changed: true });
  });
});

describe("wordDiff", () => {
  it("marks added and removed words", () => {
    const parts = wordDiff("Built APIs", "Designed APIs");
    expect(parts.filter((p) => p.removed).map((p) => p.value.trim())).toEqual(["Built"]);
    expect(parts.filter((p) => p.added).map((p) => p.value.trim())).toEqual(["Designed"]);
  });
});
