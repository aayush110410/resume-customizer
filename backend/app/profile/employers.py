"""What kind of company each employer is (from the curated India-first list) and which field each role is in."""

import re

from app.knowledge.models import Knowledge
from app.schemas import EmployerKind, JDAnalysis, ResumeDoc, Stint
from app.text_utils import contains_term, normalize

_STARTUP = re.compile(
    r"\bstart-?up\b|\bseed\b|pre-seed|series [a-d]\b|early[- ]stage|founding (engineer|member|team)", re.I
)
_JD_KINDS: dict[str, EmployerKind] = {
    "product_startup": "startup",
    "it_services": "it_services",
    "gcc": "mnc",
    "bfsi": "mnc",
    "consulting_mba": "mnc",
    "psu_govt": "govt",
    "other": "unknown",
}


def employer_kind(organization: str, bullets_text: str, kb: Knowledge) -> EmployerKind:
    org = normalize(organization or "")
    for name in sorted(kb.employers, key=len, reverse=True):
        if contains_term(org, name):
            return kb.employers[name]
    if _STARTUP.search(f"{organization} {bullets_text}"):
        return "startup"
    return "unknown"


def field_of(title: str, kb: Knowledge) -> str | None:
    """The role family whose longest title keyword appears in the title ("Data Engineer" gives data_ml)."""
    best: tuple[int, str] | None = None
    for family in kb.role_families.values():
        for t in family.titles:
            if contains_term(title, t) and (best is None or len(t) > best[0]):
                best = (len(t), family.key)
    return best[1] if best else None


def jd_employer_kind(jd: JDAnalysis, kb: Knowledge) -> EmployerKind:
    if jd.company and (kind := employer_kind(jd.company, "", kb)) != "unknown":
        return kind
    return _JD_KINDS.get(jd.employer_type, "unknown")


def classify(stints: list[Stint], resume: ResumeDoc, kb: Knowledge) -> list[Stint]:
    """Fill employer kind and field on each stint (answers can override them later)."""
    text = {e.id: " ".join(b.text for b in e.bullets) for e in resume.experience}
    return [
        st.model_copy(
            update={
                "employer_kind": employer_kind(st.organization, text.get(st.entry_id, ""), kb),
                "field": field_of(st.title, kb),
            }
        )
        for st in stints
    ]
