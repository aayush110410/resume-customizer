<!-- version: 2 -->
Task: rewrite the resume lines below, each by its own instruction. Code has already decided the order and the skills. Do not reorder, merge, split, add or drop lines.

Hiring context:
$context_brief

Tone: $tone_rule
Spelling: $spelling

TRUTH RULES (absolute — a rewrite that breaks one is discarded):
- Keep every number exactly as written ("keep" lists them).
- New words may only be the JD terms listed under "use" for that line. Never add a tool, technology, employer, metric, team size or result that the original line does not state.
- The verb must say what the original says was done: "developing" may become "Developed" or "Built", never "Designed" or "Led".
- Do not append outcome clauses ("…, improving reliability", "…, ensuring uptime") unless the original states that outcome. Code deletes unsupported ones.
- Lines marked MUST REWRITE must come back changed. Any other line that is already strong may be returned unchanged.

HOW TO REWRITE A LINE:
1. Open with a strong past-tense verb: Built, Designed, Led, Reduced, Migrated, Automated, Launched, Scaled, Delivered, Optimised. If "weak opener" is named, it must go.
2. Lead with the outcome or scale when the original has one; then what was done; then how.
3. Use each term under "use" in place of the resume's wording given before the arrow.
4. One sentence, 12–30 words, no "I/my/we", no buzzwords (passionate, dynamic, hardworking, synergy, result-oriented).
$summary_block
LINES (rewrite every one, in this order):
$lines

OUTPUT: JSON Lines only — one JSON object per line, no prose, no code fences.
$summary_format{"type":"bullet","entry_id":"<entry id>","source_id":"<line id>","text":"<rewritten line>","addresses":["<requirement ids from 'proves'>"]}
{"type":"change","target_id":"<line id>","what":"<what changed, ≤ 12 words>","why":"<why it helps for this job, ≤ 15 words>","requirement_ids":["…"]}
Emit one bullet object per line above. After each line you actually changed, emit one change object.
