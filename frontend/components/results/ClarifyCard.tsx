"use client";

import { useState } from "react";
import { CardTitle, Delta, OutlineButton, Segmented } from "@/components/ledger";
import { answerSummary, chosenAnswers, pendingAnswers, sameAnswers, stageLine } from "@/lib/clarify";
import { runNewVersion, runRescore } from "@/lib/flow";
import { useAppStore } from "@/lib/store";
import type { Answer, Profile } from "@/lib/types";
import { useHydrated } from "@/lib/useHydrated";

/** Things only the candidate knows (why a gap, what a short role was, what "Zephyr" is). Answers re-score in code
 * on the server — no model call — and carry into the next tailored version. */
export function ClarifyCard({ profile }: { profile: Profile }) {
  const hydrated = useHydrated();
  const versions = useAppStore((s) => s.versions);
  const busy = useAppStore((s) => s.busy);
  const [answers, setAnswers] = useState<Record<string, Answer>>(profile.answers);
  const [open, setOpen] = useState(profile.questions.length > 1 && Object.keys(profile.answers).length === 0);
  const [saving, setSaving] = useState(false);
  const [result, setResult] = useState<{ before: number; after: number }>();
  const dirty = !sameAnswers(chosenAnswers(answers), profile.answers);

  const set = (id: string, patch: Partial<Answer>) =>
    setAnswers((a) => {
      const prev: Answer = a[id] ?? { value: "", text: null, state_on_resume: false };
      return { ...a, [id]: { ...prev, ...patch } };
    });

  const submit = async () => {
    setSaving(true);
    const r = await runRescore(pendingAnswers(profile.questions, chosenAnswers(answers)));
    setSaving(false);
    if (r) {
      setResult(r);
      setOpen(false);
    }
  };

  if (!open) {
    return (
      <section aria-label="Confirm a few things" className="card flex flex-wrap items-center justify-between gap-3 px-5 py-4">
        <p className="text-[13.5px] text-ink-2">
          We read you as <span className="text-ink">{stageLine(profile)}</span>
          <span className="text-ink-3">  ·  {answerSummary(profile)}</span>
          {result && (
            <span className="figure ml-3 text-ink-3">
              overall {result.before} → <span className="text-ink">{result.after}</span> <Delta value={result.after - result.before} />
            </span>
          )}
        </p>
        <div className="flex gap-2">
          {result && versions.length > 0 && (
            <OutlineButton disabled={busy !== "idle"} onClick={() => void runNewVersion(versions.at(-1)!.settings)}>
              Apply to tailored resume
            </OutlineButton>
          )}
          <OutlineButton tone="gold" disabled={!hydrated} onClick={() => setOpen(true)}>
            {Object.keys(profile.answers).length ? "Edit answers" : "Confirm a few things"}
          </OutlineButton>
        </div>
      </section>
    );
  }

  return (
    <section aria-label="Confirm a few things" className="card edge-lit flex flex-col gap-1 p-5 sm:p-6">
      <CardTitle meta={answerSummary(profile)}>Confirm a few things</CardTitle>
      <p className="max-w-2xl text-[13px] leading-relaxed text-ink-3">
        Only you know these. Answers re-score instantly, without the AI, and the next tailored version uses them.
      </p>
      <ol className="mt-3">
        {profile.questions.map((q) => {
          const a = answers[q.id];
          return (
            <li key={q.id} className="flex flex-col gap-3 border-t border-rule-section py-4">
              <div className="flex flex-wrap items-baseline justify-between gap-2">
                <p className="text-[14px] text-ink">{q.prompt}</p>
                {q.impact > 0 && <span className="figure text-[12.5px] text-gold">up to +{q.impact} overall</span>}
              </div>
              <Segmented label={q.prompt} value={a?.value ?? ""} options={q.options} onChange={(v) => set(q.id, { value: v })} />
              {q.allow_text && (
                <input
                  aria-label={`${q.prompt} (in a few words)`}
                  maxLength={80}
                  value={a?.text ?? ""}
                  onChange={(e) => set(q.id, { text: e.target.value || null })}
                  placeholder={q.kind === "custom_name" ? "What it does, in a few words" : "In a few words (optional)"}
                  className="min-h-10 max-w-md rounded-full border border-rule-control bg-shell px-4 text-[13px] text-ink placeholder:text-ink-4 focus:border-gold/60 focus:outline-none"
                />
              )}
              {q.kind === "gap" && (
                <label className="flex items-center gap-2.5 text-[13px] text-ink-2">
                  <input
                    type="checkbox"
                    checked={a?.state_on_resume ?? false}
                    onChange={(e) => set(q.id, { state_on_resume: e.target.checked })}
                    className="size-4 accent-[var(--color-gold)]"
                  />
                  Add it to my tailored resume as a one-line career break
                </label>
              )}
            </li>
          );
        })}
      </ol>
      <div className="flex flex-wrap items-center gap-3 border-t border-rule-section pt-4">
        <OutlineButton tone="gold" disabled={!hydrated || saving || !dirty} onClick={() => void submit()}>
          {saving ? "Updating…" : "Update scores"}
        </OutlineButton>
        <OutlineButton disabled={saving} onClick={() => setOpen(false)}>Later</OutlineButton>
      </div>
    </section>
  );
}
