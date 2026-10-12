"""ATS estimate: parseability + keyword coverage + structure + length. Fully deterministic."""

import re

from app.knowledge.models import Knowledge, RegionPack
from app.resume_ops import iter_bullets
from app.schemas import Explanation, JDAnalysis, LayoutReport, ResumeDoc, SubScore
from app.scoring.aggregate import round_half_up
from app.text_utils import contains_term

EMAIL = re.compile(r"[\w.+-]+@[\w-]+\.[\w.-]+")
PHONE_CANDIDATE = re.compile(r"\+?\d[\d\s().-]{8,18}\d")
_ONGOING = re.compile(r"^(present|current|now|till date|ongoing)$", re.I)
_MONTHS = {
    m: i for i, m in enumerate(["jan", "feb", "mar", "apr", "may", "jun", "jul", "aug", "sep", "oct", "nov", "dec"], 1)
}
_DATE_FORMATS = (
    ("month_year", re.compile(r"^[A-Za-z]{3,9}\.?\s+'?\d{2,4}$")),
    ("mm_yyyy", re.compile(r"^\d{1,2}[/-]\d{4}$")),
    ("year", re.compile(r"^\d{4}$")),
)


def _has_phone(text: str) -> bool:
    return any(len(re.sub(r"\D", "", m)) >= 10 for m in PHONE_CANDIDATE.findall(text))


def _keyword_hits(text: str, resume: ResumeDoc, jd: JDAnalysis, kb: Knowledge) -> dict[str, float]:
    bullets = "\n".join(b.text for _, _, b in iter_bullets(resume, ["experience", "projects"]))
    hits = {}
    for kw in dict.fromkeys(jd.ats_keywords):
        forms = kb.synonyms.variants(kw)
        if any(contains_term(bullets, f) for f in forms):
            hits[kw] = 1.0
        elif any(contains_term(text, f) for f in forms):
            hits[kw] = 0.7
        else:
            hits[kw] = 0.0
    return hits


def missing_keywords(text: str, jd: JDAnalysis, kb: Knowledge) -> list[str]:
    return [
        kw for kw in dict.fromkeys(jd.ats_keywords) if not any(contains_term(text, f) for f in kb.synonyms.variants(kw))
    ]


def _date_format(value: str) -> str | None:
    value = value.strip()
    if _ONGOING.match(value):
        return None
    return next((name for name, rx in _DATE_FORMATS if rx.match(value)), "other")


def _year_month(value: str | None) -> tuple[int, int] | None:
    if not value:
        return None
    year = re.search(r"(\d{4})", value)
    if not year:
        return None
    month = _MONTHS.get(value.strip()[:3].lower(), 0)
    return int(year.group(1)), month


def score_ats(
    text: str, layout: LayoutReport, resume: ResumeDoc, jd: JDAnalysis, region: RegionPack, kb: Knowledge
) -> SubScore:
    ex: list[Explanation] = []

    def lose(points: float, signal: str, detail: str, fix: str) -> float:
        ex.append(Explanation(signal=signal, impact=-points, detail=detail, fix=fix))
        return points

    # Parseability (30)
    parse = 30.0
    if layout.multi_column:
        parse -= lose(
            10,
            "multi_column",
            "Multi-column layout: many ATS read straight across columns and scramble text.",
            "Use a single-column layout.",
        )
    if layout.has_tables:
        parse -= lose(
            6, "tables", "Tables detected: ATS often drop or reorder table cells.", "Replace tables with plain lines."
        )
    if layout.image_count:
        parse -= lose(
            4,
            "images",
            f"{layout.image_count} image(s) detected (photo, icons or logos) — ATS ignore them.",
            "Remove images and icons; write contact details as text.",
        )
    if layout.hidden_chars:
        parse -= lose(
            10,
            "hidden_text",
            "Hidden or tiny text detected — reads as keyword stuffing to recruiters.",
            "Delete invisible or microscopic text.",
        )
    if not EMAIL.search(text):
        parse -= lose(5, "no_email", "No email address found in the text.", "Add your email as plain text at the top.")
    if not _has_phone(text):
        parse -= lose(
            5, "no_phone", "No phone number found in the text.", "Add a phone number with country code, e.g. +91."
        )
    parse = max(0.0, parse)

    # Keywords (35)
    hits = _keyword_hits(text, resume, jd, kb)
    keywords = 35.0 * (sum(hits.values()) / len(hits) if hits else 1.0)
    missing = [k for k, h in hits.items() if h == 0]
    listed_only = [k for k, h in hits.items() if h == 0.7]
    if missing:
        ex.append(
            Explanation(
                signal="missing_keywords",
                impact=-35 * len(missing) / len(hits),
                detail="JD keywords not found: " + ", ".join(missing),
                fix="Add the ones you genuinely have, in context inside a bullet.",
            )
        )
    if listed_only:
        ex.append(
            Explanation(
                signal="keywords_listed_only",
                impact=-35 * 0.3 * len(listed_only) / len(hits),
                detail="Only in your skills list, never used in a bullet: " + ", ".join(listed_only),
                fix="Show each of these in an experience or project bullet.",
            )
        )
    for kw, h in hits.items():
        forms = kb.synonyms.variants(kw)
        short = [f for f in forms if " " not in f and len(f) <= 5]
        long_ = [f for f in forms if " " in f]
        if (
            h
            and short
            and long_
            and not (any(contains_term(text, f) for f in short) and any(contains_term(text, f) for f in long_))
        ):
            ex.append(
                Explanation(
                    signal="acronym_form",
                    impact=0,
                    detail=f"Only one form of “{kw}” appears.",
                    fix=f"Write both forms once, e.g. “{long_[0].title()} ({short[0].upper()})”.",
                )
            )

    # Structure (20)
    structure = 0.0
    if resume.experience or resume.projects:
        structure += 6
    else:
        lose(6, "no_experience_section", "No experience or projects section found.", "Add Experience or Projects.")
    if resume.education:
        structure += 4
    else:
        lose(4, "no_education", "No education section found.", "Add an Education section.")
    if resume.skills:
        structure += 4
    else:
        lose(4, "no_skills", "No skills section found.", "Add a Skills section listing tools and technologies.")
    dates = [d for e in resume.experience + resume.projects for d in (e.start, e.end) if d]
    formats = {f for f in map(_date_format, dates) if f}
    if resume.experience and not dates:
        lose(3, "no_dates", "Experience entries have no dates.", "Add start and end dates, e.g. “Jan 2023 – Present”.")
    elif len(formats) > 1 or "other" in formats:
        lose(3, "inconsistent_dates", "Dates use mixed formats.", "Use one format everywhere, e.g. “Jan 2023”.")
    else:
        structure += 3
    starts = [ym for ym in (_year_month(e.start) for e in resume.experience) if ym]
    if len(starts) >= 2 and starts != sorted(starts, reverse=True):
        lose(
            3,
            "not_reverse_chronological",
            "Experience isn't in reverse-chronological order.",
            "List the latest role first.",
        )
    else:
        structure += 3

    # Length (15)
    limit = region.max_pages(resume.level)
    if layout.pages <= limit:
        length = 15.0
    elif layout.pages == limit + 1:
        length = 15 - lose(
            8,
            "too_long",
            f"{layout.pages} pages; {limit} is the norm at this level.",
            "Cut older, less relevant detail.",
        )
    else:
        length = 15 - lose(
            15, "too_long", f"{layout.pages} pages; {limit} is the norm at this level.", "Cut to the norm."
        )
    if layout.word_count < 200:
        length = max(0.0, length - lose(5, "too_thin", "Under 200 words — too little for ATS to match.", "Add detail."))

    ex.sort(key=lambda e: e.impact)
    return SubScore(key="ats", score=round_half_up(parse + keywords + structure + length), explanations=ex)
