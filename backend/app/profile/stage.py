"""Where the candidate is: a student in year N, a fresh graduate, or 1–3 / 3–7 / 7+ years into work."""

import math
import re
from datetime import date

from app.profile.timeline import ONGOING, course_years, is_school, parse_date
from app.schemas import ResumeDoc, Stage, Stint

_PURSUING = re.compile(r"pursuing|expected|ongoing|present|current", re.I)
FULL_TIME = ("job", "trainee", "freelance")


def full_time_months(stints: list[Stint], today: date) -> int:
    """Months of full-time work, overlaps counted once (internships, apprenticeships and simulations excluded)."""
    spans = []
    for st in stints:
        if st.kind in FULL_TIME and st.start:
            s = int(st.start[:4]) * 12 + int(st.start[5:]) - 1
            e = int(st.end[:4]) * 12 + int(st.end[5:]) - 1 if st.end else today.year * 12 + today.month - 1
            spans.append((s, e))
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
    worked = full_time_months(stints, today)
    grad_year = None
    for edu in resume.education:
        if is_school(edu):
            continue
        parsed = parse_date(edu.end, today) if edu.end and not ONGOING.search(edu.end) else None
        if parsed:
            end = parsed[0] if parsed[1] else date(parsed[0].year, 6, 1)  # year-only graduation → June
            grad_year = max(grad_year or 0, end.year)
            months_left = (end.year * 12 + end.month) - (today.year * 12 + today.month)
            if months_left > 0 and worked < 12:
                length = course_years(edu.title)
                year = length - math.ceil(months_left / 12) + 1
                return "student", min(max(year, 1), length), end.year
        elif _PURSUING.search(f"{edu.end or ''} {edu.title}") and worked < 12:
            return "student", None, None
    years = worked / 12
    stage: Stage = "fresh_grad" if years < 1 else "early" if years < 3 else "mid" if years < 7 else "senior"
    return stage, None, grad_year
