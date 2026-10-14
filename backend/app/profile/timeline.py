"""The candidate's dated history: stints (jobs, internships, apprenticeships…) and the gaps between them.

Dates are read with their precision. A year-only bound ("2022") widens to the whole year, so a gap measured
across it is a lower bound and a stint with one is never called short: imprecise dates never create a flag.
"""

import re
from datetime import date

from app.knowledge.models import Knowledge, StoryRules
from app.schemas import CareerGap, Entry, ResumeDoc, Stint, StintKind
from app.text_utils import normalize

MONTHS = {
    m: i for i, m in enumerate(["jan", "feb", "mar", "apr", "may", "jun", "jul", "aug", "sep", "oct", "nov", "dec"], 1)
}
ONGOING = re.compile(r"present|current|now|till date|to date|ongoing", re.I)
_YEAR = re.compile(r"(?:19|20)\d{2}")
_YM = re.compile(r"\b((?:19|20)\d{2})[-/.](\d{1,2})\b")  # 2021-05
_MY = re.compile(r"\b(\d{1,2})[-/.]((?:19|20)\d{2})\b")  # 05/2021
_BREAK = re.compile(r"\s*career break\b", re.I)
_SHORT_YEAR = re.compile(r"'(\d{2})\b")
_MON_YY = re.compile(r"\b([a-z]{3,9})[\s\-/.']+(\d{2})\b")
_MM_YY = re.compile(r"^(\d{1,2})[-/.](\d{2})$")
_KINDS: list[tuple[StintKind, re.Pattern[str]]] = [
    ("virtual_program", re.compile(r"\bforage\b|job simulation|virtual (experience|internship)", re.I)),
    ("apprenticeship", re.compile(r"\bapprentice(ship)?\b|\bnats\b|\bnaps\b", re.I)),
    ("internship", re.compile(r"\bintern(ship)?\b", re.I)),
    ("trainee", re.compile(r"\btrainee\b|\bget\b", re.I)),
    ("freelance", re.compile(r"\bfreelanc\w*|\bcontract(or)?\b|\bself[- ]employed\b", re.I)),
]


def parse_date(value: str | None, today: date) -> tuple[date, bool] | None:
    """(first day of the month, whether the month is known); None when there is no year."""
    if not value or not value.strip():
        return None
    v = value.strip().lower()
    if ONGOING.search(v):
        return date(today.year, today.month, 1), True
    if (m := _YM.search(v)) and 1 <= int(m.group(2)) <= 12:
        return date(int(m.group(1)), int(m.group(2)), 1), True
    if (m := _MY.search(v)) and 1 <= int(m.group(1)) <= 12:
        return date(int(m.group(2)), int(m.group(1)), 1), True
    year = _YEAR.search(v)
    if not year:  # two-digit years: "Jun 21", "Jun-21", "June '21", "06/21"
        if (m := _MON_YY.search(v)) and m.group(1)[:3] in MONTHS:
            return date(_century(int(m.group(2)), today), MONTHS[m.group(1)[:3]], 1), True
        if (m := _MM_YY.match(v)) and 1 <= int(m.group(1)) <= 12:
            return date(_century(int(m.group(2)), today), int(m.group(1)), 1), True
    y = int(year.group(0)) if year else (_century(int(m.group(1)), today) if (m := _SHORT_YEAR.search(v)) else None)
    if y is None:
        return None
    month = next((MONTHS[w[:3]] for w in re.findall(r"[a-z]+", v) if w[:3] in MONTHS), 0)
    return date(y, month or 1, 1), bool(month)


def _century(yy: int, today: date) -> int:
    return 2000 + yy if yy <= today.year % 100 + 5 else 1900 + yy


def month_key(d: date) -> str:
    return f"{d.year:04d}-{d.month:02d}"


def month_label(key: str) -> str:
    """ "2021-06" → "Jun 2021"."""
    return f"{list(MONTHS)[int(key[5:7]) - 1].capitalize()} {key[:4]}"


def _index(d: date) -> int:
    return d.year * 12 + d.month - 1


def _from_index(i: int) -> date:
    return date(i // 12, i % 12 + 1, 1)


def stint_kind(entry: Entry) -> StintKind:
    text = f"{entry.title} {entry.organization}"
    return next((kind for kind, rx in _KINDS if rx.search(text)), "job")


def _bounds(entry: Entry, today: date) -> tuple[int, int, bool, bool] | None:
    """Widest month-index interval for an entry: (start, end, start month known, end month known)."""
    start = parse_date(entry.start, today)
    if not start:
        return None
    end = parse_date(entry.end, today) if entry.end else (date(today.year, today.month, 1), True)
    if not end:
        return None
    s = _index(start[0])
    e = _index(end[0]) + (0 if end[1] else 11)  # year-only end → December
    return (s, e, start[1], end[1]) if e >= s else None


def narrow_bounds(entry: Entry, today: date) -> tuple[int, int] | None:
    """Narrowest reading of an entry's dates (year-only start → December, year-only end → January): the least
    time the candidate can have spent there. Used for experience, where overstating is the risk."""
    start = parse_date(entry.start, today)
    end = parse_date(entry.end, today) if entry.end else (date(today.year, today.month, 1), True)
    if not start or not end:
        return None
    s = _index(start[0]) + (0 if start[1] else 11)
    e = _index(end[0])
    return (s, e) if e >= s else None


def build_stints(resume: ResumeDoc, kb: Knowledge, rules: StoryRules, today: date) -> list[Stint]:
    """Experience entries in chronological order. Employer kind and field are filled by the caller."""
    del kb  # employer kind and field come from app.profile.employers
    out = []
    for entry in resume.experience:
        if _BREAK.match(entry.title):
            continue  # a stated career break is context, not a role
        kind = stint_kind(entry)
        b = _bounds(entry, today)
        ongoing = not entry.end or bool(ONGOING.search(entry.end or ""))
        stint = Stint(entry_id=entry.id, organization=entry.organization, title=entry.title, kind=kind)
        if b:
            s, e, start_exact, end_exact = b
            precise = start_exact and end_exact
            stint.start, stint.end = month_key(_from_index(s)), None if ongoing else month_key(_from_index(e))
            stint.precise = precise
            stint.months = e - s + 1 if precise else None
            stint.short = (
                precise and not ongoing and kind in ("job", "trainee") and stint.months < rules.short_stint_months
            )
        out.append(stint)
    # Tenure is per employer: a trainee stint that turns into a role at the same company is one stay, not a hop.
    groups: dict[str, list[Stint]] = {}
    for st in out:
        if st.kind in ("job", "trainee"):
            groups.setdefault(_employer_key(st.organization), []).append(st)
    for same in groups.values():
        if len(same) > 1:
            ongoing = any(st.start and st.end is None for st in same)
            total = sum(st.months or 0 for st in same)
            for st in same:
                st.short = st.precise and not ongoing and total < rules.short_stint_months
    return sorted(out, key=lambda st: st.start or "9999")


_ORG_SUFFIX = re.compile(r"\b(ltd|limited|pvt|private|inc|llp|llc|corp|corporation|co)\b\.?")


def _employer_key(organization: str) -> str:
    return " ".join(_ORG_SUFFIX.sub(" ", normalize(organization)).replace(",", " ").split())


_SCHOOL = re.compile(
    r"\b(10th|12th|class (x|xii|10|12)|ssc|hsc|secondary|cbse|icse|matric\w*|intermediate|high school|puc)\b", re.I
)
_COURSE = [
    (5, re.compile(r"\bb\.?\s?arch|dual degree|integrated", re.I)),
    (4, re.compile(r"\bb\.?\s?tech|\bb\.?\s?e\b|bachelor of (technology|engineering)", re.I)),
    (
        2,
        re.compile(
            r"\bm\.?\s?tech|\bm\.?\s?e\b|\bm\.?\s?sc|\bmca\b|\bmba\b|\bpgdm\b|\bpgp\b|master|\bm\.?\s?com\b|\bm\.?\s?s\b",
            re.I,
        ),
    ),
]


def course_years(title: str) -> int:
    """Typical length of the degree named in an education title (3 for other bachelor's and diplomas)."""
    return next((n for n, rx in _COURSE if rx.search(title)), 3)


def is_school(entry: Entry) -> bool:
    return bool(_SCHOOL.search(f"{entry.title} {entry.organization}"))


def study_span(entry: Entry, today: date) -> tuple[int, int, bool, bool] | None:
    """Months spent on a degree; a missing start is inferred from the course length (and is not exact)."""
    if b := _bounds(entry, today):
        return b
    end = parse_date(entry.end, today)
    if not end:
        return None
    e = _index(end[0]) + (0 if end[1] else 11)
    return e - course_years(entry.title) * 12 + 1, e, False, end[1]


def find_gaps(resume: ResumeDoc, stints: list[Stint], rules: StoryRules, today: date) -> list[CareerGap]:
    """Breaks of at least `rules.gap_months` in work and study (school years excluded), up to today."""
    if any(st.kind != "virtual_program" and not st.start for st in stints):
        return []  # an undated role could sit in any break: judging gaps would accuse a working candidate
    by_id = {e.id: e for e in resume.experience}
    activity = []  # (start, end, entry id, start exact, end exact)
    for st in stints:
        if st.kind != "virtual_program" and st.entry_id in by_id and (b := _bounds(by_id[st.entry_id], today)):
            activity.append((*b[:2], st.entry_id, *b[2:]))
    for e in resume.experience:  # a career break the resume already states covers its own months
        if _BREAK.match(e.title) and (b := _bounds(e, today)):
            activity.append((*b[:2], e.id, *b[2:]))
    for edu in resume.education:
        if not is_school(edu) and (b := study_span(edu, today)):
            activity.append((*b[:2], edu.id, *b[2:]))
    if not activity:
        return []
    activity.sort()
    gaps = []

    def hole(start: int, end: int, after_id: str, precise: bool):
        if end - start + 1 >= rules.gap_months:
            k = month_key(_from_index(start))
            gaps.append(
                CareerGap(
                    id=f"gap:{k}",
                    after_entry_id=after_id,
                    start=k,
                    end=month_key(_from_index(end)),
                    months=end - start + 1,
                    precise=precise,
                )
            )

    _, cursor, after, _, cursor_exact = activity[0]
    for s, e, entry_id, s_exact, e_exact in activity[1:]:
        if s > cursor + 1:
            hole(cursor + 1, s - 1, after, cursor_exact and s_exact)
        if e > cursor:
            cursor, after, cursor_exact = e, entry_id, e_exact
    if cursor < _index(today):
        hole(cursor + 1, _index(today), after, cursor_exact)
    return gaps
