<!-- version: 2 -->
Task: for every requirement below, decide how well this resume proves it. Code has already searched the resume; you add only what code cannot see: the same skill in different words. Scores are computed later by code from your answers, so follow the procedure exactly.

Hiring context:
$context_brief

CODE FINDINGS (already verified against the resume):
$code_findings

PROCEDURE — for each requirement, apply the first step that fits, then stop:
1. If CODE FINDINGS says DECIDED, copy that status exactly.
2. Look for ONE bullet (by its [id]) where the candidate DOES the required thing. Different words for the same thing count:
   "Spring Boot" proves Java · "Jenkins pipelines" proves CI/CD · "trained 3 interns" proves mentoring · "EKS" proves Kubernetes.
   - The bullet shows them doing it (built, designed, led, migrated, reduced…) → "strong".
   - The bullet only mentions it, or describes a duty without doing it → "partial".
3. Else, if the skills list, summary or certifications name it → "partial" (quote the exact item).
4. Else, if a bullet shows a close alternative a recruiter would accept as a bridge (GCP for AWS, RabbitMQ for Kafka, MySQL for PostgreSQL, Flask for Django) → "transferable".
5. Else → "missing". quote = null, bullet_ids = [].

Hard rules:
- quote: copy the characters exactly from the resume (no [id] tag, at most 200 characters). Never paraphrase. If you cannot copy it, you have no evidence.
- bullet_ids: only ids that appear in square brackets in the resume. "strong" always needs a bullet id.
- Soft skills (communication, ownership, teamwork) need a bullet that demonstrates them; adjectives in a summary are not evidence.
- When unsure between two statuses, choose the lower one.
- rationale: one plain sentence a recruiter would agree with.
- Return exactly one match per requirement id.

gaps: one per must/should requirement you judged "missing", "partial" or "transferable": a concrete action, and a suggested_bullet the candidate could adapt ONLY if true, with [placeholders] for every number or detail you do not know (e.g. "Containerised [N] services with Docker, cutting deploy time by [X]%").

recruiter: as $recruiter_persona doing a 7-second first scan of this resume for this job — decision ("shortlist" | "maybe" | "reject"), first_impression (1–2 candid sentences about what stands out and what is missing), reasons (2–4 short points).

tips: up to 5 tips from this list that matter most for THIS candidate and job; return each tip_id with advice personalised to this resume (at most 2 concrete sentences). Use only these tip_ids:
$tips_json

Requirements:
$requirements_json

$resume_block
