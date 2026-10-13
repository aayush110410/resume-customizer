export interface Segment { text: string; hit: boolean }

const escape = (s: string) => s.replace(/[.*+?^${}()|[\]\\]/g, "\\$&");

/** Splits text into segments, marking JD terms. Longest terms win; a term never matches inside a longer word. */
export function highlight(text: string, terms: string[]): Segment[] {
  const clean = [...new Set(terms.map((t) => t.trim()).filter((t) => t.length > 1 || /[a-z]/i.test(t)))].sort((a, b) => b.length - a.length);
  if (!clean.length) return [{ text, hit: false }];
  const rx = new RegExp(`(?<![\\w.+#])(${clean.map(escape).join("|")})(?![\\w+#])`, "gi");
  const out: Segment[] = [];
  let last = 0;
  for (const m of text.matchAll(rx)) {
    if (m.index! > last) out.push({ text: text.slice(last, m.index), hit: false });
    out.push({ text: m[0], hit: true });
    last = m.index! + m[0].length;
  }
  if (last < text.length) out.push({ text: text.slice(last), hit: false });
  return out.length ? out : [{ text, hit: false }];
}
