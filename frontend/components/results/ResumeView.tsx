import { Chip, Label } from "@/components/ledger";
import type { Bullet, Entry, FabricationFlag, ResumeDoc, TailorItem } from "@/lib/types";
import { highlight } from "@/lib/highlight";
import { cn } from "@/lib/utils";

function Marked({ text, terms }: { text: string; terms: string[] }) {
  return (
    <>
      {highlight(text, terms).map((s, i) =>
        s.hit ? <mark key={i} className="rounded-[4px] bg-[rgba(217,189,139,0.14)] px-0.5 text-gold-hi">{s.text}</mark> : <span key={i}>{s.text}</span>,
      )}
    </>
  );
}

type Revert = ((targetId: string) => void) | undefined;

function UseOriginal({ id, onRevert }: { id: string; onRevert: Revert }) {
  if (!onRevert) return null;
  return (
    <button type="button" onClick={() => onRevert(id)} className="ml-2 text-[12px] text-gold-dim underline underline-offset-4 hover:text-gold">
      Use original
    </button>
  );
}

function Bullets({ bullets, flags, onRevert, terms = [] }: { bullets: Bullet[]; flags: Map<string, FabricationFlag>; onRevert?: Revert; terms?: string[] }) {
  return (
    <ul className="mt-1.5 flex flex-col gap-1.5">
      {bullets.map((b) => {
        const f = flags.get(b.id);
        return (
          <li key={b.id} className="grid grid-cols-[10px_1fr] gap-2 text-[13.5px] leading-[1.6] text-ink-2">
            <span className="mt-[9px] size-1 bg-gold-dim" aria-hidden />
            <span className={cn(f && "decoration-gold-dim underline decoration-dotted underline-offset-4")}>
              <Marked text={b.text} terms={terms} />
              {f && <span className="ml-2 inline-flex items-center"><Chip tone="gold" title={`${f.reason}: ${f.tokens.join(", ")}`}>Needs your confirmation · {f.tokens.join(", ")}</Chip><UseOriginal id={b.id} onRevert={onRevert} /></span>}
            </span>
          </li>
        );
      })}
    </ul>
  );
}

function EntryBlock({ e, flags, onRevert, terms }: { e: Entry; flags: Map<string, FabricationFlag>; onRevert?: Revert; terms: string[] }) {
  const dates = [e.start, e.end].filter(Boolean).join(" – ");
  return (
    <div className="border-t border-rule-section py-3">
      <div className="flex flex-wrap items-baseline justify-between gap-x-4">
        <span className="text-[15px] font-medium text-ink">{e.title}{e.organization && <span className="font-normal text-ink-3"> · {e.organization}</span>}</span>
        <span className="figure text-[12.5px] text-ink-3">{[e.location, dates].filter(Boolean).join(" · ")}</span>
      </div>
      {e.bullets.length > 0 && <Bullets bullets={e.bullets} flags={flags} onRevert={onRevert} terms={terms} />}
    </div>
  );
}

/** The tailored resume as a document; amber-flagged lines contain facts we could not find in the original. */
/** `terms` are the JD's keywords: every place the resume uses one is marked, so the match is visible at a glance. */
export function ResumeView({ resume, flags = [], onRevert, terms = [] }: { resume: ResumeDoc; flags?: FabricationFlag[]; onRevert?: Revert; terms?: string[] }) {
  const byId = new Map(flags.map((f) => [f.target_id, f]));
  const c = resume.contact;
  return (
    <article className="flex flex-col gap-7">
      <header className="border-b border-rule pb-5">
        <h3 className="text-[30px] font-medium tracking-[-0.018em]">{c.name}</h3>
        <p className="mt-1 text-[13px] text-ink-3">{[c.email, c.phone, c.location, ...c.links].filter(Boolean).join("  ·  ")}</p>
      </header>
      {resume.summary && (
        <section>
          <Label>Summary</Label>
          <p className="mt-2 max-w-[75ch] text-[13.5px] leading-[1.75] text-ink-2"><Marked text={resume.summary} terms={terms} /></p>
          {byId.get("summary") && <div className="mt-2 flex items-center"><Chip tone="gold">Needs your confirmation · {byId.get("summary")!.tokens.join(", ")}</Chip><UseOriginal id="summary" onRevert={onRevert} /></div>}
        </section>
      )}
      {resume.skills.length > 0 && (
        <section>
          <Label>Skills</Label>
          <dl className="mt-2">
            {resume.skills.map((g) => (
              <div key={g.name} className="grid gap-1 border-t border-rule-section py-2 sm:grid-cols-[160px_1fr]">
                <dt className="text-[13px] text-ink-3">{g.name}</dt><dd className="text-[13.5px] text-ink-2"><Marked text={g.items.join(", ")} terms={terms} /></dd>
              </div>
            ))}
          </dl>
          {byId.get("skills") && <div className="mt-2 flex items-center"><Chip tone="gold">Not in your original resume · {byId.get("skills")!.tokens.join(", ")}</Chip><UseOriginal id="skills" onRevert={onRevert} /></div>}
        </section>
      )}
      {(["experience", "projects", "education"] as const).map((k) =>
        resume[k].length ? (
          <section key={k}><Label>{k}</Label><div className="mt-1">{resume[k].map((e) => <EntryBlock key={e.id} e={e} flags={byId} onRevert={onRevert} terms={terms} />)}</div></section>
        ) : null,
      )}
      {resume.achievements.length > 0 && <section><Label>Achievements</Label><Bullets bullets={resume.achievements} flags={byId} onRevert={onRevert} terms={terms} /></section>}
      {resume.other_sections.map((o) => <section key={o.id}><Label>{o.name}</Label><Bullets bullets={o.bullets} flags={byId} onRevert={onRevert} /></section>)}
    </article>
  );
}

/** While the writer streams, show each rewritten line as it lands. */
export function StreamingPreview({ items }: { items: TailorItem[] }) {
  const lines = items.filter((i) => i.type !== "change");
  return (
    <div aria-live="polite" className="flex flex-col">
      <Label>Rewriting · {lines.length} lines so far</Label>
      <ul className="mt-2">
        {lines.map((i, n) => (
          <li key={n} className="animate-in fade-in slide-in-from-bottom-1 border-t border-rule-section py-2.5 text-[13.5px] leading-[1.6] text-ink-2 duration-500">
            <span className="tracked mr-3 text-[10.5px]">{i.type === "bullet" ? i.source_id : i.type}</span>
            {i.type === "summary" ? i.text : i.type === "bullet" ? i.text : i.type === "skills" ? i.groups.map((g) => g.items.join(", ")).join(" · ") : null}
          </li>
        ))}
      </ul>
    </div>
  );
}
