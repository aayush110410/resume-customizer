<!-- version: 1 -->
Task: judge, requirement by requirement, how well this resume evidences the job's requirements. You produce evidence only; code computes the scores from your judgments, so be strict and consistent.

Hiring context:
$context_brief

Status definitions (apply exactly):
- strong: demonstrated in an experience or project bullet with a concrete action, ideally with scope or a result. Example: requirement "REST API design" ↔ bullet "Designed 14 REST APIs serving 2M requests/day".
- partial: only listed in skills/certifications, or mentioned without depth. Example: "Docker" appears only in the skills list.
- transferable: no direct evidence, but closely adjacent experience a recruiter would accept as a bridge. Example: requirement "AWS" ↔ bullet "Deployed services on GCP".
- missing: no evidence at all.
Years-of-experience requirements: compare with the candidate's total full-time experience of $years years. Education requirements: use the education section.

Evidence rules:
- quote: the most relevant text copied EXACTLY from the resume (≤ 200 characters, without the [id] tag), or null when missing. Never paraphrase.
- bullet_ids: only IDs shown in square brackets in the resume (e.g. "exp0.b1"); empty when the evidence is in skills or summary.
- rationale: one sentence a recruiter would agree with.
- Exactly one match per requirement id.

gaps: one per must/should requirement judged missing or partial, with a concrete action. suggested_bullet: an example the candidate could adapt ONLY if it is true for them, with [placeholders] for every number or detail you do not know (e.g. "Containerised [N] services with Docker, cutting deploy time by [X]%"). Never state invented facts as the candidate's.

recruiter: as $recruiter_persona doing a 7-second first scan of this resume for this job — decision (shortlist | maybe | reject), first_impression (1–2 candid sentences), reasons (2–4 short points).

tips: up to 5 tips from this list that matter most for THIS candidate and job; return each tip_id with advice personalised to this resume (≤ 2 concrete sentences). Use only these tip_ids:
$tips_json

Requirements:
$requirements_json

$resume_block
