"""Where the candidate is: a student in year N, a fresh graduate, or 1–3 / 3–7 / 7+ years into work."""

import math
import re
from datetime import date

from app.profile.timeline import ONGOING, course_years, is_school, narrow_bounds, parse_date, study_span
from app.schemas import ResumeDoc, Stage, Stint

_PURSUING = re.compile(r"pursuing|expected|ongoing|present|current", re.I)
FULL_TIME = ("job", "trainee", "freelance")


def full_time_months(resume: ResumeDoc, stints: list[Stint], today: date, started_before: int | None = None) -> int:
    """Months of full-time work, overlaps counted once and year-only dates read narrowly (internships,
    apprenticeships and simulations excluded). `started_before` keeps only work begun before that month index."""
    kinds = {st.entry_id: st.kind for st in stints}
    spans = []
    for e in resume.experience:
        b = narrow_bounds(e, today) if kinds.get(e.id) in FULL_TIME else None
        if b and (started_before is None or b[0] < started_before):
            spans.append(b)
    total, cursor = 0, -1
    for s, e in sorted(spans):
        s = max(s, cursor + 1)
        if e >= s:
            total += e - s + 1
            cursor = e
    return total


def detect_stage(resume: ResumeDoc, stints: list[Stint], today: date) -> tuple[Stage, int | None, int | None]:
    """(stage, study year, graduation year). A student is someone whose degree ends after today and who has
    under a year of full-time work; the study year counts back from graduation by the course length."""
    worked = full_time_months(resume, stints, today)
    grad_year = None
    for edu in resume.education:
        if is_school(edu):
            continue
        parsed = parse_date(edu.end, today) if edu.end and not ONGOING.search(edu.end) else None
        if parsed:
            end = parsed[0] if parsed[1] else date(parsed[0].year, 6, 1)  # year-only graduation → June
            grad_year = max(grad_year or 0, end.year)
            months_left = (end.year * 12 + end.month) - (today.year * 12 + today.month)
            # work begun during this degree (freelancing, part-time) does not make a student a professional
            span = study_span(edu, today)
            before = full_time_months(resume, stints, today, span[0]) if span else worked
            if months_left > 0 and before < 12:
                length = course_years(edu.title)
                year = length - math.ceil(months_left / 12) + 1
                return "student", min(max(year, 1), length), end.year
        elif _PURSUING.search(f"{edu.end or ''} {edu.title}") and worked < 12:
            return "student", None, None
    years = worked / 12
    stage: Stage = "fresh_grad" if years < 1 else "early" if years < 3 else "mid" if years < 7 else "senior"
    return stage, None, grad_year
