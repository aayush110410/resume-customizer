import type { Answer, Profile, Question } from "@/lib/types";

/** Only answers to questions still on screen go to the server (it rejects unknown ids). */
export function pendingAnswers(questions: Question[], answers: Record<string, Answer>): Record<string, Answer> {
  const ids = new Set(questions.map((q) => q.id));
  return Object.fromEntries(Object.entries(answers).filter(([id]) => ids.has(id)));
}

export function answerSummary(profile: Profile): string {
  const answered = profile.questions.filter((q) => profile.answers[q.id]).length;
  return `${answered} of ${profile.questions.length} confirmed`;
}

const STAGE: Record<Profile["stage"], string> = {
  student: "student", fresh_grad: "fresh graduate", early: "1–3 years into work", mid: "3–7 years into work", senior: "7+ years into work",
};

export function stageLine(p: Profile): string {
  if (p.stage !== "student") return STAGE[p.stage];
  const n = p.study_year;
  const year = n ? `${n}${n === 1 ? "st" : n === 2 ? "nd" : n === 3 ? "rd" : "th"}-year ` : "";
  return `${year}student${p.grad_year ? `, graduating ${p.grad_year}` : ""}`;
}
