<!-- version: 1 -->
Task: analyse the job description into atomic, weighted requirements that an expert recruiter would screen for.

Rules:
- is_job_description: false if the text is not a job description (e.g. a resume, an article, random text). Still fill the other fields as best you can.
- requirements: atomic, one skill or qualification each ("Python and Go" → two requirements); 6–25 items; skip EEO statements, benefits, perks and company boilerplate.
  - importance: "must" = required / must / mandatory / minimum / "X+ years", and the core duties of the role; "should" = preferred / strong plus / desirable; "nice" = bonus / good to have / exposure to.
  - type: hard_skill | soft_skill | experience | education | certification | domain | tool.
  - keywords: the canonical term plus common variants a resume might use (e.g. "Kubernetes", "k8s").
- ats_keywords: up to 30 hard skills, tools, certifications and domain terms exactly as written in the JD, most important first.
- min_years: minimum years of experience required, else null. seniority: fresher | junior | mid | senior | executive.
- role_family: exactly one of: $role_family_keys.
- employer_type: product_startup | it_services | gcc | consulting_mba | bfsi | psu_govt | other.
  Cues: "GCC", "global capability / in-house / captive centre" → gcc; clients, onsite, delivery, IT services brands → it_services; banks, NBFCs, insurers, asset managers → bfsi; PSU, government, public sector → psu_govt; consulting firms and MBA-track management roles → consulting_mba; product companies and startups → product_startup.
- location; suggested_region: "india" if the job is in India (or pay is in INR / LPA), else "international".
- spelling: "uk" for British spellings (organise, analyse, colour), "us" for American, else "unknown".
- Leave every "id" field as an empty string.

$jd_block
