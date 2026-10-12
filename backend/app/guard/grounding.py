"""Anti-hallucination checks: LLM quotes must exist in the resume; tailored text must not add facts."""

import re

from rapidfuzz import fuzz

from app.knowledge.models import Knowledge
from app.resume_ops import bullet_index, iter_bullets
from app.schemas import Evidence, FabricationFlag, MatchStatus, ResumeDoc
from app.text_utils import contains_term, normalize

QUOTE_THRESHOLD = 90
_DOWNGRADE: dict[MatchStatus, MatchStatus] = {"strong": "partial", "partial": "transferable", "transferable": "missing"}
_NUM = re.compile(r"\d[\d,]*(?:\.\d+)?\s?%?")
_TOKEN = re.compile(r"[A-Za-z0-9][A-Za-z0-9+#./\-]*[A-Za-z0-9+#]|[A-Za-z0-9]")
_SENTENCE = re.compile(r"(?<=[.!?;:])\s+|\n+")
_NUMERIC = re.compile(r"[\d.,%+]+")
_STOP = {
    "i",
    "a",
    "an",
    "the",
    "and",
    "or",
    "of",
    "in",
    "on",
    "at",
    "for",
    "with",
    "to",
    "by",
    "from",
    "as",
    "via",
    "jan",
    "feb",
    "mar",
    "apr",
    "may",
    "jun",
    "jul",
    "aug",
    "sep",
    "sept",
    "oct",
    "nov",
    "dec",
}


def verify_quote(quote: str, source: str, threshold: int = QUOTE_THRESHOLD) -> bool:
    q = normalize(quote or "")
    return bool(q) and fuzz.partial_ratio(q, normalize(source)) >= threshold


def verify_evidence(ev: Evidence, resume: ResumeDoc, resume_text: str) -> Evidence:
    """Drop unknown bullet ids; downgrade a claim one step when its quote isn't in the resume or it cites nothing."""
    known = bullet_index(resume)
    out = ev.model_copy(deep=True)
    for m in out.matches:
        m.bullet_ids = [b for b in dict.fromkeys(m.bullet_ids) if b in known]
        if m.status == "missing":
            continue
        quote_ok = verify_quote(m.quote, resume_text) if m.quote else False
        if (m.quote and not quote_ok) or (not m.quote and not m.bullet_ids):
            m.verified = False
            m.status = _DOWNGRADE[m.status]
    return out


def _numbers(text: str) -> set[str]:
    return {re.sub(r"[,\s]", "", n) for n in _NUM.findall(text)}


def _fact_terms(text: str) -> list[str]:
    """Tokens that assert a fact: tools/tech (digits, + # . /, internal capitals) and capitalised names mid-sentence."""
    terms = []
    for sentence in _SENTENCE.split(text):
        for i, tok in enumerate(_TOKEN.findall(sentence)):
            if _NUMERIC.fullmatch(tok) or tok.lower() in _STOP:
                continue  # numbers are checked separately
            techy = any(c.isdigit() for c in tok) or any(c in "+#./" for c in tok) or sum(c.isupper() for c in tok) >= 2
            if techy or (tok[0].isupper() and i > 0):
                terms.append(tok)
    return list(dict.fromkeys(terms))


def _present(term: str, haystack: str, kb: Knowledge) -> bool:
    forms = {term}
    if len(term) > 2 and term.endswith("s") and term[:-1].isupper():
        forms.add(term[:-1])  # APIs -> API
    return any(contains_term(haystack, v) for f in forms for v in kb.synonyms.variants(f))


def find_fabrications(
    original: ResumeDoc, original_text: str, tailored: ResumeDoc, kb: Knowledge
) -> list[FabricationFlag]:
    flags: list[FabricationFlag] = []
    all_numbers = _numbers(original_text)

    if tailored.summary and tailored.summary != original.summary:
        bad = [n for n in _numbers(tailored.summary) if n not in all_numbers]
        bad += [t for t in _fact_terms(tailored.summary) if not _present(t, original_text, kb)]
        if bad:
            flags.append(FabricationFlag(target_id="summary", tokens=bad, reason="Not found in your original resume"))

    original_skills = {normalize(i) for g in original.skills for i in g.items}
    new_skills = [
        item
        for g in tailored.skills
        for item in g.items
        if normalize(item) not in original_skills and not _present(item, original_text, kb)
    ]
    if new_skills:
        flags.append(
            FabricationFlag(target_id="skills", tokens=new_skills, reason="Skill not present in your original resume")
        )

    sources = bullet_index(original)
    for _, _, bullet in iter_bullets(tailored):
        source = sources.get(bullet.id)
        if source is None or source.text == bullet.text:
            continue
        source_numbers = _numbers(source.text)
        bad = [n for n in _numbers(bullet.text) if n not in source_numbers]
        bad += [t for t in _fact_terms(bullet.text) if not _present(t, original_text, kb)]
        if bad:
            flags.append(
                FabricationFlag(
                    target_id=bullet.id, tokens=list(dict.fromkeys(bad)), reason="Not in the original bullet"
                )
            )
    return flags
