import { Source_Serif_4 } from "next/font/google";
import type { Contact } from "@/lib/types";

const serif = Source_Serif_4({ subsets: ["latin"], weight: ["400", "600"] });

/** The letter as it will print: letterhead, then each block of the plain-text letter. */
export function LetterPreview({ text, contact }: { text: string; contact: Contact }) {
  const blocks = text.split(/\n\s*\n/).map((b) => b.trim()).filter(Boolean);
  const details = [contact.email, contact.phone, contact.location, ...contact.links].filter(Boolean);
  return (
    <article
      aria-label="Cover letter preview"
      className={`${serif.className} mx-auto w-full max-w-[720px] rounded-sm bg-paper px-7 py-9 text-base leading-relaxed text-paper-ink shadow-lg sm:px-14 sm:py-12`}
    >
      <header className="border-b border-paper-rule pb-3">
        <h3 className="text-2xl leading-tight font-semibold tracking-tight">{contact.name}</h3>
        {details.length > 0 && <p className="mt-1 text-xs text-paper-muted">{details.join("  ·  ")}</p>}
      </header>
      <div className="mt-6 flex flex-col gap-[1.05em]">
        {blocks.map((b, i) => (
          <p key={i} className={b.startsWith("Subject:") ? "font-semibold" : "whitespace-pre-line"}>{b}</p>
        ))}
      </div>
    </article>
  );
}
