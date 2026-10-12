<!-- version: 1 -->
Task: tailor this resume to the job, truthfully. You may only edit these sections: $sections.

Hiring context:
$context_brief

Tone: $tone_rule
Spelling: follow the JD's convention ($spelling); keep the candidate's numbers, currency and units exactly as written.

Truthfulness contract (absolute):
- Rephrase, reorder, emphasise, and mirror the JD's wording ONLY for skills and experience the evidence shows the candidate has.
- Never add employers, titles, dates, degrees, tools, technologies, metrics or numbers that are not in the resume. Keep every number exactly as written.
- Missing requirements are handled elsewhere; do not paper over them.

How to edit:
- Bullets: lead with a strong past-tense action verb; state scope and result when the original contains them; 1–2 lines each; within each entry, order bullets by relevance to the must-have requirements. Rewrite every bullet you return; you may return a bullet unchanged if it is already strong.
- Summary (if editable): 40–70 words, no first person, no clichés or objective statements; who the candidate is, years, domain, 1–2 strongest evidenced proofs that match this JD.
- Skills (if editable): put JD-matched skills first; you may regroup and rename groups; never add a skill the resume does not contain.

Output format: JSON Lines only — one JSON object per line, no prose, no code fences. Allowed objects:
{"type":"summary","text":"…"}
{"type":"skills","groups":[{"name":"…","items":["…"]}]}
{"type":"bullet","entry_id":"exp0","source_id":"exp0.b2","text":"…","addresses":["r1"]}
{"type":"change","target_id":"exp0.b2","what":"…","why":"…","requirement_ids":["r1"]}
- entry_id is the entry ID shown in angle brackets (e.g. <exp0>); achievements use entry_id "ach". source_id is the bullet ID in square brackets. Emit bullets for an entry in the new order.
- After each summary/skills/bullet line you changed, emit one change line (target_id = "summary", "skills" or the bullet ID) explaining what changed and why, citing requirement IDs.

Requirements:
$requirements_json

Evidence per requirement (from an earlier review):
$evidence_json

$resume_block
