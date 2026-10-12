<!-- version: 1 -->
Task: convert the resume below into the structured schema. This is extraction, not editing.

Rules:
- Copy every bullet VERBATIM. Only repair line-break hyphenation and re-join a bullet wrapped across lines. Do not fix grammar, shorten, reword or merge separate bullets.
- Section mapping:
  - Work experience, internships, apprenticeships, articleship → experience (internships keep "Intern" in the title).
  - Projects (academic, personal, capstone, live projects) → projects.
  - Degrees and schooling (incl. 10th/12th) → education: degree in title, institute in organization, CGPA/percentage/rank kept verbatim as a bullet.
  - Positions of responsibility, awards, achievements, certifications, publications, extra-curriculars, case competitions → achievements, one bullet each.
  - Declaration, personal details (date of birth, father's name, marital status, address, languages known), hobbies, references → other_sections, using the resume's heading as name.
  - Skills → skills groups using the resume's own grouping, else a single group named "Skills".
- contact: name, email, phone, city, and profile links (LinkedIn, GitHub, portfolio).
- summary: the summary / objective / profile paragraph verbatim, or null.
- Bullet kind: "impact" if it states an outcome or result (a metric, a change, something delivered and its effect); "duty" if it describes a responsibility or activity without a result; "other" for non-work lines.
- Dates: copy as written (e.g. "Jan 2022", "2020", "Present").
- total_years_experience: full-time professional experience only, in years with one decimal; exclude internships, education and overlapping periods.
- level: fresher (< 1 year), junior (1–3), mid (3–7), senior (7–12), executive (12+).
- Leave every "id" field as an empty string.

$resume_block
