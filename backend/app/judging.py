"""Code-first judging. Everything a recruiter can decide from facts is decided here; the model only adds
semantic evidence that code cannot see, and only when it can cite a bullet whose quote verifies.

Floors and facts:
- years of experience: computed from the resume's own dates (internships excluded, overlaps merged)
- degree level: B.Tech/B.E./BSc/BCA… < M.Tech/MSc/MCA/MBA/PGDM… < PhD
- certifications: found in achievements, skills or summary
- skills and tools: where their keywords (and synonyms) appear — a demonstrated bullet, a weak bullet, or only a list
"""

import re
from datetime import date

from app.knowledge.models import Knowledge
from app.resume_ops import iter_bullets
from app.schemas import Level, MatchStatus, Requirement, RequirementMatch, ResumeDoc
from app.scoring.match import CREDIT
from app.text_utils import contains_term, normalize

_MONTHS = {
    m: i for i, m in enumerate(["jan", "feb", "mar", "apr", "may", "jun", "jul", "aug", "sep", "oct", "nov", "dec"], 1)
}
_ONGOING = re.compile(r"present|current|now|till date|to date|ongoing", re.I)
_INTERN = re.compile(r"\bintern(ship)?\b", re.I)
_YEARS = re.compile(r"(\d+(?:\.\d+)?)\s*\+?\s*(?:(?:-|–|to)\s*\d+(?:\.\d+)?\s*)?\+?\s*(?:years?|yrs?)\b", re.I)
_DEGREES = (
    (3, re.compile(r"\b(ph\.?\s?d|doctorate)\b", re.I)),
    (
        2,
        re.compile(
            r"\b(m\.?\s?tech|m\.?\s?e\b|m\.?\s?sc|mca|mba|pgdm|pgp|master'?s?|m\.?\s?com|m\.?\s?s\b|post[- ]?graduate)",
            re.I,
        ),
    ),
    (
        1,
        re.compile(
            r"\b(b\.?\s?tech|b\.?\s?e\b|b\.?\s?sc|bca|bba|b\.?\s?com|b\.?\s?a\b|bachelor'?s?|graduate|degree in|undergraduate)",
            re.I,
        ),
    ),
)
_METRIC = re.compile(r"\d|%|₹|\$")
_GENERIC = {
    "experience",
    "development",
    "skills",
    "skill",
    "knowledge",
    "strong",
    "good",
    "ability",
    "working",
    "hands-on",
}


def _parse_date(value: str | None, today: date) -> date | None:
    if not value:
        return None
    v = value.strip().lower()
    if _ONGOING.search(v):
        return today
    year = re.search(r"(19|20)\d{2}", v) or re.search(r"'(\d{2})\b", v)
    if not year:
        return None
    y = int(year.group(0)) if len(year.group(0)) == 4 else 2000 + int(year.group(1))
    numeric = re.match(r"(\d{1,2})[/-]", v)
    month = int(numeric.group(1)) if numeric and 1 <= int(numeric.group(1)) <= 12 else _MONTHS.get(v[:3], 0)
    return date(y, month or 1, 1)


def years_of_experience(resume: ResumeDoc, today: date) -> float | None:
    """Full-time professional years from entry dates: internships excluded, overlapping roles counted once."""
    spans = []
    for e in resume.experience:
        if _INTERN.search(e.title):
            continue
        start = _parse_date(e.start, today)
        end = _parse_date(e.end, today) if e.end else today
        if start and end and end >= start:
            spans.append((start, end))
    if not spans:
        return None
    # Month spans are inclusive (Feb–Jul = 6 months); back-to-back roles merge into one stretch.
    idx = sorted((st.year * 12 + st.month - 1, en.year * 12 + en.month) for st, en in spans)
    months, (cur_s, cur_e) = 0, idx[0]
    for s_, e_ in idx[1:]:
        if s_ <= cur_e:
            cur_e = max(cur_e, e_)
        else:
            months += cur_e - cur_s
            cur_s, cur_e = s_, e_
    months += cur_e - cur_s
    return round(months / 12, 1)


def level_for_years(years: float) -> Level:
    return (
        "fresher"
        if years < 1
        else "junior"
        if years < 3
        else "mid"
        if years < 7
        else "senior"
        if years < 12
        else "executive"
    )


def required_years(text: str) -> float | None:
    m = _YEARS.search(text)
    return float(m.group(1)) if m else None


def degree_level(text: str) -> int:
    return next((lvl for lvl, rx in _DEGREES if rx.search(text)), 0)


_CERT_WORD = re.compile(r"certif", re.I)
_OR = re.compile(r"\bor\b|/|\beither\b", re.I)
_TIER = {"strong": 3, "partial": 2}


def _forms(term: str, kb: Knowledge) -> set[str]:
    """Inflections a resume might use for an ordinary word (payment/payments, mentor/mentored/mentoring).
    Tool and technology names from the vocabulary are matched exactly."""
    forms = {term}
    if term in kb.synonyms.groups or " " in term or not term.isalpha() or len(term) < 4:
        return forms
    base = term[:-1] if term.endswith("s") else term
    forms |= {base, base + "s", base + "ed", base + "ing"}
    if base.endswith("e"):
        forms |= {base + "d", base[:-1] + "ing"}
    return forms


def _named_groups(req: Requirement, kb: Knowledge) -> list[tuple[set[str], bool]]:
    """The distinct skills/tools the requirement itself names, as (matchable forms, named inside parentheses).
    Keywords the model added but the requirement never mentions are ignored."""
    text = re.sub(_CERT_WORD.pattern + r"\w*", " ", req.text, flags=re.I) if req.type == "certification" else req.text
    outside = re.sub(r"\([^)]*\)", " ", text)
    candidates = [normalize(k) for k in req.keywords]
    candidates += [v for v in kb.synonyms.groups if len(v) >= 2 and contains_term(text, v)]
    groups: list[tuple[set[str], bool]] = []

    def add(c: str) -> None:
        c = _CERT_WORD.sub("", c).strip() if req.type == "certification" else c
        if len(c) < 2 or c in _GENERIC:
            return
        variants = kb.synonyms.variants(c)
        forms = {f for v in variants for f in _forms(v, kb) if len(f) >= 2}
        if not any(contains_term(text, f) for f in forms) or any(forms & g or forms <= g for g, _ in groups):
            return
        groups.append((forms, not any(contains_term(outside, f) for f in forms)))

    for c in candidates:
        add(c)
    if not groups and len(text.split()) <= 3:
        add(normalize(text))
    return groups


def _best(forms: set[str], resume: ResumeDoc, kb: Knowledge, cert: bool) -> tuple[str, str | None, list[str]]:
    """Strongest evidence for one named skill: ('strong'|'partial'|'none', quote, bullet ids)."""
    if cert:
        for item in [b.text for b in resume.achievements] + [i for g in resume.skills for i in g.items]:
            if _CERT_WORD.search(item) and any(contains_term(item, f) for f in forms):
                return "strong", item, []
        return "none", None, []
    strong, weak = [], []
    for _, _, b in iter_bullets(resume, ["experience", "projects"]):
        if any(contains_term(b.text, f) for f in forms):
            first = re.findall(r"[a-z]+", normalize(b.text))[:1]
            demonstrated = bool(first and first[0] in kb.lexicons.action_verbs) or bool(_METRIC.search(b.text))
            (strong if demonstrated else weak).append(b)
    if strong:
        return "strong", strong[0].text, [b.id for b in strong]
    if weak:
        return "partial", weak[0].text, [b.id for b in weak]
    for item in (
        [i for g in resume.skills for i in g.items] + [b.text for b in resume.achievements] + [resume.summary or ""]
    ):
        if item and any(contains_term(item, f) for f in forms):
            return "partial", item, []
    return "none", None, []


def _match(
    req: Requirement, status: MatchStatus, rationale: str, quote: str | None = None, bullets: list[str] | None = None
) -> RequirementMatch:
    return RequirementMatch(
        requirement_id=req.id, status=status, quote=quote, bullet_ids=bullets or [], rationale=rationale
    )


def is_factual(req: Requirement) -> bool:
    """Requirements code decides outright (the model is not consulted)."""
    return (req.type == "experience" and required_years(req.text) is not None) or (
        req.type == "education" and degree_level(req.text) > 0
    )


def code_judgment(req: Requirement, resume: ResumeDoc, kb: Knowledge, years: float | None) -> RequirementMatch | None:
    need = required_years(req.text)
    if req.type == "experience" and need is not None and years is not None:
        status: MatchStatus = "strong" if years >= need else "partial" if years >= 0.75 * need else "missing"
        return _match(
            req, status, f"Resume dates show about {years:g} years of full-time experience; the JD asks for {need:g}+."
        )
    if req.type == "education" and (need_lvl := degree_level(req.text)):
        have = max((degree_level(f"{e.title} {e.organization}") for e in resume.education), default=0)
        if have >= need_lvl:
            return _match(req, "strong", "Degree level on the resume meets the requirement.", resume.education[0].title)
        return _match(req, "missing", "No degree at the required level on the resume.")

    groups = _named_groups(req, kb)
    if not groups:
        return None
    cert = req.type == "certification"
    examples = set().union(*[g for g, inside in groups if inside]) if any(inside for _, inside in groups) else set()
    main = [g for g, inside in groups if not inside] or [g for g, _ in groups]
    # A parenthetical names examples of the term it qualifies: "Java (Spring Boot)" is proven by Spring Boot work.
    found = [_best(g | examples, resume, kb, cert) for g in main]
    if len(found) == 1 or _OR.search(req.text):
        tier, quote, ids = max(found, key=lambda f: _TIER.get(f[0], 0))
    else:
        present = [f for f in found if f[0] != "none"]
        if not present:
            return None
        weakest = min(present, key=lambda f: _TIER[f[0]])
        tier = weakest[0] if len(present) == len(found) else "partial"
        quote, ids = present[0][1], [i for f in present for i in f[2]]
    if tier == "none":
        return None
    if cert:
        return _match(req, "strong", "The certification is listed on the resume.", quote)
    reason = {
        "strong": "Named in an experience or project bullet that shows the work.",
        "partial": "Named only in a list, in a duty-style bullet, or only part of a compound requirement is shown.",
    }[tier]
    return _match(req, tier, reason, quote, list(dict.fromkeys(ids)))


def reconcile(req: Requirement, code: RequirementMatch | None, model: RequirementMatch) -> RequirementMatch:
    """Facts win; otherwise the model may only raise a status, and only with a verified quote (and a bullet for strong)."""
    if code is not None and is_factual(req):
        return code
    floor = code or _match(req, "missing", model.rationale)
    trusted = model.verified and bool(model.quote) and (model.status != "strong" or bool(model.bullet_ids))
    if trusted and CREDIT[model.status] > CREDIT[floor.status]:
        return model
    if code is None:
        return model if trusted else _match(req, "missing", model.rationale)
    return code
