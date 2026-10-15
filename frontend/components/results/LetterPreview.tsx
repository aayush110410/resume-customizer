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
      className={`${serif.className} mx-auto w-full max-w-[720px] rounded-[4px] bg-[#f7f3eb] px-7 py-9 text-[15px] leading-[1.65] text-[#211d18] shadow-[0_40px_90px_-40px_rgba(0,0,0,0.9)] sm:px-14 sm:py-12`}
    >
      <header className="border-b border-[#cbbfa9] pb-3">
        <h3 className="text-[25px] leading-tight font-semibold tracking-[-0.01em]">{contact.name}</h3>
        {details.length > 0 && <p className="mt-1 text-[12.5px] text-[#6b6254]">{details.join("  ·  ")}</p>}
      </header>
      <div className="mt-6 flex flex-col gap-[1.05em]">
        {blocks.map((b, i) => (
          <p key={i} className={b.startsWith("Subject:") ? "font-semibold" : "whitespace-pre-line"}>{b}</p>
        ))}
      </div>
    </article>
  );
}
