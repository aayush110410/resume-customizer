"""Rule-based JD reading: requirements come from the JD's own bullets, importance from the heading above them.
The same JD always gives the same requirements. Prose-only JDs return None and fall back to the model."""

import re

from app.judging import degree_level, required_years
from app.knowledge.models import Knowledge
from app.schemas import Importance, ReqType
from app.text_utils import contains_term, normalize

_SKIP = re.compile(
    r"^(about|benefits|perks|why (join|us)|what we offer|location|compensation|salary|equal opportunity|how to apply|our (culture|company|team)|company)",
    re.I,
)
_NICE = re.compile(r"good to have|nice to have|preferred|bonus|plus|desirable|added advantage|brownie", re.I)
_MUST = re.compile(
    r"requirement|qualification|must[- ]?have|looking for|who you are|you (have|bring)|skills|eligibility|criteria|essential",
    re.I,
)
_SHOULD = re.compile(
    r"what you('ll| will) do|responsibilit|the role|your role|duties|day[- ]to[- ]day|your impact|key result|you will",
    re.I,
)
_BULLET = re.compile(r"^\s*(?:[-*•·▪–◦]|\d+[.)])\s+")
_LEAD = re.compile(
    r"^(experience (?:with|in)|knowledge of|familiarity with|hands-on (?:experience )?with|exposure to|proficiency in|expertise in|understanding of|working knowledge of)\s+(.*)$",
    re.I,
)
_SOFT = re.compile(
    r"mentor|communicat|leadership|stakeholder|teamwork|team player|ownership|collaborat|problem[- ]solving|presentation",
    re.I,
)

MIN_ITEMS = 3


def _heading(line: str) -> Importance | str | None:
    """Section a heading line opens: 'skip', an importance, or None if the line is not a heading."""
    text = line.strip().rstrip(":").strip()
    if not text or _BULLET.match(line) or len(text.split()) > 6 or text.endswith("."):
        return None
    for rx, kind in ((_SKIP, "skip"), (_NICE, "nice"), (_MUST, "must"), (_SHOULD, "should")):
        if rx.search(text):
            return kind
    return None


def _split(item: str) -> list[str]:
    """Splits a bullet into items: "Run X; own Y" gives two, "Experience with Docker and Kubernetes" gives one per
    thing (outside parentheses)."""
    parts = [p.strip() for p in item.split(";") if p.strip()]
    out = []
    for part in parts:
        lead = _LEAD.match(part)
        outside = re.sub(r"\([^)]*\)", lambda m: "\x00" * len(m.group(0)), part)
        if lead and " and " in outside[lead.start(2) :]:
            body = part[lead.start(2) :]
            masked = outside[lead.start(2) :]
            cut = [m.start() for m in re.finditer(r" and ", masked)]
            pieces, last = [], 0
            for c in cut:
                pieces.append(body[last:c])
                last = c + len(" and ")
            pieces.append(body[last:])
            out += [f"{lead.group(1)} {p.strip().rstrip('.')}" for p in pieces if p.strip()]
        else:
            out.append(part)
    return out


def _type(text: str) -> ReqType:
    if required_years(text) is not None:
        return "experience"
    if degree_level(text):
        return "education"
    if re.search(r"certif", text, re.I):
        return "certification"
    if _SOFT.search(text):
        return "soft_skill"
    if re.search(r"\b(domain|industry)\b", text, re.I):
        return "domain"
    return "hard_skill"


def _items(jd_text: str) -> list[tuple[str, Importance]] | None:
    section: str | None = None
    items: list[tuple[str, Importance]] = []
    for line in jd_text.splitlines():
        if not line.strip():
            continue
        kind = _heading(line)
        if kind is not None:
            section = kind
            continue
        if section in ("must", "should", "nice"):
            text = _BULLET.sub("", line).strip()
            if len(text.split()) >= 2:
                items += [(t, section) for t in _split(text)]
    return items if len(items) >= MIN_ITEMS else None


def named_skills(text: str, kb: Knowledge) -> list[str]:
    """Known skills the text names, as written in the text, in order of appearance (one per synonym group)."""
    found: dict[frozenset, tuple[int, str]] = {}
    norm = normalize(text)
    for variant, group in kb.synonyms.groups.items():
        if len(variant) < 2 or not contains_term(text, variant):
            continue
        m = re.search(re.escape(variant), norm)
        pos = m.start() if m else 0
        if group not in found or pos < found[group][0]:
            raw = re.search(re.escape(variant), text, re.I)
            found[group] = (pos, raw.group(0) if raw else variant)
    return [word for _, word in sorted(found.values())]


def parse_requirements(jd_text: str, kb: Knowledge) -> list[tuple[str, Importance, ReqType]] | None:
    items = _items(jd_text)
    if items is None:
        return None
    return [(text, imp, _type(text)) for text, imp in items]


def ats_keywords_from(jd_text: str, kb: Knowledge, limit: int = 30) -> list[str]:
    items = _items(jd_text)
    scope = "\n".join(t for t, _ in items) if items else jd_text
    seen: dict[str, str] = {}
    for word in named_skills(scope, kb):
        seen.setdefault(normalize(word), word)
    return list(seen.values())[:limit]
