import { CardTitle } from "@/components/ledger";
import { stageLine } from "@/lib/clarify";
import type { MoveKind, Profile, Stint } from "@/lib/types";
import { cn } from "@/lib/utils";

const MOVE: Record<MoveKind, string> = {
  services_to_product: "services → product",
  startup_to_mnc: "startup → large company",
  mnc_to_mega: "MNC → mega-MNC",
  field_switch: "field switch",
};
const KIND: Partial<Record<Stint["kind"], string>> = {
  internship: "Internship", apprenticeship: "Apprenticeship", trainee: "Trainee", freelance: "Freelance", virtual_program: "Simulation",
};

const idx = (key: string) => Number(key.slice(0, 4)) * 12 + Number(key.slice(5, 7)) - 1;

/** The candidate's history on one axis: roles as bars, gaps hatched, short roles outlined; then the move this
 * application represents and how each project reads. */
export function StoryTimeline({ profile }: { profile: Profile }) {
  const dated = profile.stints.filter((s) => s.start);
  const now = idx(profile.as_of);
  const starts = [...dated.map((s) => idx(s.start!)), ...profile.gaps.map((g) => idx(g.start))];
  const from = starts.length ? Math.min(...starts) : now;
  const span = Math.max(1, now - from + 1);
  const pos = (start: string, end: string | null) => {
    const a = idx(start), b = end ? idx(end) : now;
    return { left: `${((a - from) / span) * 100}%`, width: `${(Math.max(1, b - a + 1) / span) * 100}%` };
  };
  const years = Array.from({ length: Math.floor(now / 12) - Math.floor(from / 12) + 1 }, (_, i) => Math.floor(from / 12) + i);
  const targets = profile.moves.filter((m) => m.target);

  return (
    <section aria-label="Career story" className="card flex flex-col gap-5 p-5">
      <CardTitle meta={stageLine(profile)}>Career story</CardTitle>

      {targets.map((m) => (
        <p key={m.kind} className="text-sm leading-relaxed text-ink-2">
          This application is a <span className="text-gold">{MOVE[m.kind]}</span>: {m.from_label} → {m.to_label}.
        </p>
      ))}

      {dated.length > 0 && (
        <div className="flex flex-col gap-2" role="list" aria-label="Timeline">
          {dated.map((s) => (
            <div key={s.entry_id} role="listitem" className="grid grid-cols-[minmax(0,150px)_minmax(0,1fr)] items-center gap-3">
              <span className="truncate text-xs text-ink-3" title={`${s.title}, ${s.organization}`}>
                {s.organization}{KIND[s.kind] ? ` · ${KIND[s.kind]}` : ""}
              </span>
              <span className="relative h-2.5 rounded-full bg-gold/5">
                <span
                  className={cn(
                    "absolute inset-y-0 rounded-full",
                    s.kind === "job" || s.kind === "trainee" || s.kind === "freelance" ? "bg-gold-dim" : "bg-ink-3/60",
                    s.kind === "virtual_program" && "bg-transparent border border-dashed border-ink-3",
                    s.short && "ring-1 ring-down",
                  )}
                  style={pos(s.start!, s.end)}
                  title={`${s.title} · ${s.months ?? "?"} months${s.short ? " · under a year" : ""}`}
                />
              </span>
            </div>
          ))}
          {profile.gaps.length > 0 && (
            <div role="listitem" className="grid grid-cols-[minmax(0,150px)_minmax(0,1fr)] items-center gap-3">
              <span className="text-xs text-down">Gaps</span>
              <span className="relative h-2.5">
                {profile.gaps.map((g) => (
                  <span
                    key={g.id}
                    className="absolute inset-y-0 rounded-full bg-[repeating-linear-gradient(135deg,var(--color-down)_0_3px,transparent_3px_6px)] opacity-70"
                    style={pos(g.start, g.end)}
                    title={`${g.months}-month gap${profile.answers[g.id] ? " · explained" : ""}`}
                  />
                ))}
              </span>
            </div>
          )}
          <div className="grid grid-cols-[minmax(0,150px)_minmax(0,1fr)] gap-3">
            <span />
            <span className="relative h-4">
              {years.map((y) => (
                <span key={y} className="tabular-nums absolute text-xs text-ink-4" style={{ left: `${((Math.max(y * 12, from) - from) / span) * 100}%` }}>
                  {y}
                </span>
              ))}
            </span>
          </div>
        </div>
      )}

      {profile.projects.length > 0 && (
        <ul className="flex flex-col">
          {profile.projects.map((p) => (
            <li key={p.project_id} className="flex items-baseline gap-3 border-t border-rule-section py-3">
              <span className="tabular-nums w-8 shrink-0 text-base text-ink">{p.score}</span>
              <span className="min-w-0 text-sm leading-relaxed text-ink-2">
                <span className="text-ink">{p.title}</span>
                {p.notes[0] ? <span className="text-ink-3">: {p.notes[0]}</span> : <span className="text-ink-3">: reads as real work.</span>}
              </span>
            </li>
          ))}
        </ul>
      )}
      {profile.rules_only && <p className="text-xs text-ink-3">Project details were checked with basic rules this time.</p>}
    </section>
  );
}
