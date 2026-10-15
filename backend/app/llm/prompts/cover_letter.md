<!-- version: 2 -->
Task: write the body of a cover letter for this candidate and job. Code adds the date, recipient, subject line, greeting and sign-off, so write only the four parts below. Return JSON only.

Hiring context:
$context_brief

Regional conventions:
$conventions

Tone: $tone_rule
Length: $word_budget words in total across all parts.

Parts:
- opening (2 sentences): the role ($jd_title at $company), the candidate's current title and employer, total experience, and the two or three skills that match the job best.
- proof (exactly 2 paragraphs, 2–3 sentences each): each proves one of the job's must-have requirements with one concrete achievement from the evidence below. Keep every number exactly as written. Use the verb the resume uses: "developed" stays developed, never "designed and led".
- motivation (1–2 sentences): why this company, using only what the job description says about the company or product.
- closing (1–2 sentences): ask for a conversation. $notice_rule $auth_rule

Hard rules:
- Only facts from the resume. Never add a tool, employer, number, team size or result the resume doesn't state.
- No clichés: not "I am writing to", "express my interest", "I am confident", "passionate", "team player", "hardworking", "seamless", "perfect fit", "kindly".
- No outcome the resume doesn't state: not ", ensuring high availability", not ", improving performance".
- Describe the work in the resume's own words; don't borrow the job description's terms for it.
- No greeting, no sign-off, no contact details (they are in the letterhead), no placeholders like [Company], no markdown.
- First person, plain business English, short sentences.

Strongest evidence for the job's must-haves (requirement → resume quote):
$proof_json

$about_block

$resume_block
