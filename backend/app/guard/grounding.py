"""Grounding checks: quotes from the LLM must appear in the resume, and tailored text must not add facts."""

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


def _fact_terms(text: str, known_skills: dict | None = None) -> list[str]:
    """Tokens that assert a fact: tools/tech (digits, + # . /, internal capitals) and capitalised names mid-sentence."""
    terms = []
    for sentence in _SENTENCE.split(text):
        for i, tok in enumerate(_TOKEN.findall(sentence)):
            if _NUMERIC.fullmatch(tok) or tok.lower() in _STOP:
                continue  # numbers are checked separately
            techy = any(c.isdigit() for c in tok) or any(c in "+#./" for c in tok) or sum(c.isupper() for c in tok) >= 2
            known = known_skills is not None and normalize(tok) in known_skills
            if techy or known or (tok[0].isupper() and i > 0):
                terms.append(tok)
    return list(dict.fromkeys(terms))


def _present(term: str, haystack: str, kb: Knowledge) -> bool:
    forms = {term}
    if len(term) > 2 and term.endswith("s") and term[:-1].isupper():
        forms.add(term[:-1])  # APIs -> API
    if term.isupper():
        forms.add(term + "s")  # API when the original says APIs
    return any(contains_term(haystack, v) for f in forms for v in kb.synonyms.variants(f))


# Ordinary resume words: not a claim on their own, even when the JD uses them.
_GLUE = {
    "strong",
    "solid",
    "proven",
    "excellent",
    "good",
    "great",
    "deep",
    "extensive",
    "hands-on",
    "highly",
    "skills",
    "skill",
    "ability",
    "year",
    "years",
    "experience",
    "experienced",
    "using",
    "across",
    "within",
    "through",
    "multiple",
    "various",
    "including",
    "based",
    "related",
    "their",
    "these",
    "those",
    "which",
    "while",
    "where",
    "other",
    "about",
    "into",
    "over",
    "under",
    "team",
    "teams",
    "work",
    "worked",
    "working",
    "with",
    "from",
    "that",
    "this",
    "more",
    "than",
    "also",
    "each",
    "both",
    "such",
    "well",
    "new",
    "end",
}
_IRREGULAR_VERBS = {"build", "lead", "run", "drive", "write", "make", "grow", "own", "ship", "set", "take", "find"}
_SUFFIXES = ("ations", "ation", "ings", "ing", "ies", "ied", "ed", "es", "s")
_WORD = re.compile(r"[a-z][a-z-]{3,}")


def _stem(word: str) -> str:
    for suffix in _SUFFIXES:
        if word.endswith(suffix) and len(word) - len(suffix) >= 3:
            return word[: -len(suffix)]
    return word


def _stems(text: str) -> set[str]:
    return {_stem(w) for w in _WORD.findall(normalize(text))}


def _jd_wording(
    text: str, original_text: str, original_stems: set[str], jd_stems: set[str], kb: Knowledge
) -> list[str]:
    """Words a rewrite took from the job description that the original resume does not say. For example,
    "payments module" becoming "payment orchestration module" adds a claim. Action verbs, glue words and
    genuine synonyms are wording, not facts."""
    verbs = {_stem(v) for v in kb.lexicons.action_verbs} | _IRREGULAR_VERBS
    out = []
    for w in _WORD.findall(normalize(text)):
        st = _stem(w)
        new = st in jd_stems and st not in original_stems and st not in verbs and w not in _GLUE
        if new and not _present(w, original_text, kb):
            out.append(w)
    return list(dict.fromkeys(out))


def _merge(bad: list[str], jd_words: list[str]) -> list[str]:
    seen = {b.lower() for b in bad}
    return bad + [w for w in jd_words if w not in seen]


JD_REASON = "Uses job description wording your original doesn't state"


def unsupported(text: str, source_text: str, kb: Knowledge, allowed_numbers: set[str] | None = None) -> list[str]:
    """Numbers, tools and names in `text` that `source_text` doesn't contain."""
    numbers = _numbers(source_text) | {n.rstrip("+") for n in (allowed_numbers or set())}
    bad = [n for n in _numbers(text) if n.rstrip("+") not in numbers]
    bad += [t for t in _fact_terms(text, kb.synonyms.groups) if not _present(t, source_text, kb)]
    return list(dict.fromkeys(bad))


def find_fabrications(
    original: ResumeDoc,
    original_text: str,
    tailored: ResumeDoc,
    kb: Knowledge,
    allowed: set[str] | None = None,
    jd_text: str | None = None,
) -> list[FabricationFlag]:
    flags: list[FabricationFlag] = []
    all_numbers = _numbers(original_text) | {n.rstrip("+") for n in (allowed or set())}
    jd_stems = _stems(jd_text) if jd_text else set()
    original_stems = _stems(original_text)

    def jd_words(text: str) -> list[str]:
        return _jd_wording(text, original_text, original_stems, jd_stems, kb) if jd_stems else []

    if tailored.summary and tailored.summary != original.summary:
        bad = [n for n in _numbers(tailored.summary) if n.rstrip("+") not in all_numbers]
        bad += [t for t in _fact_terms(tailored.summary, kb.synonyms.groups) if not _present(t, original_text, kb)]
        from_jd = jd_words(tailored.summary)
        if bad or from_jd:
            reason = "Not found in your original resume" if bad else JD_REASON
            flags.append(FabricationFlag(target_id="summary", tokens=_merge(bad, from_jd), reason=reason))

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
        bad += [t for t in _fact_terms(bullet.text, kb.synonyms.groups) if not _present(t, original_text, kb)]
        from_jd = jd_words(bullet.text)
        if bad or from_jd:
            reason = "Not in the original bullet" if bad else JD_REASON
            flags.append(
                FabricationFlag(target_id=bullet.id, tokens=_merge(list(dict.fromkeys(bad)), from_jd), reason=reason)
            )
    return flags
