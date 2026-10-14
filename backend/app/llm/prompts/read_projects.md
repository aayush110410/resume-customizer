<!-- version: 1 -->
Task: read each project in this resume and copy out the facts a recruiter looks for. Code scores the projects from your answers, so copy, don't judge.

For EVERY project id in angle brackets (like <prj0>), return one object:
- project_id: the id exactly.
- purpose: the words from the resume that say what it does and for whom (verbatim, ≤ 160 characters), or null.
- users: the words that say who used it or how many (verbatim), or null.
- scale: the words that carry a size or result number (verbatim), or null.
- links: URLs or domains written in the project, exactly as written. [] if none.
- tutorial_pattern: if the project is one of these common tutorial builds, the matching item copied from this list, else null:
  $tutorial_list
- extension: if it is a tutorial build, the words that say what the candidate added beyond the tutorial (verbatim), else null.
- custom_names: names the candidate coined for their own system, library, framework or component (e.g. "Zephyr", "Nimbus"). NOT public libraries, products or companies (React, Kafka, Razorpay are not custom names). For each: name (exact), what (2–6 words saying what it is, only if the resume says it), quote (the resume words that say it, verbatim), else what and quote null.

Hard rules:
- Every text field is copied character for character from the resume, or null. Never paraphrase, never infer.
- When unsure, use null.

$resume_block
