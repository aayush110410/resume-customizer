"""Career moves: the ones already made (context) and the target move this application represents (judged)."""

from app.knowledge.models import Knowledge
from app.profile.employers import jd_employer_kind
from app.profile.stage import FULL_TIME
from app.schemas import EmployerKind, JDAnalysis, Move, MoveKind, Stint

LABEL = {
    "startup": "startup",
    "product": "product company",
    "it_services": "IT services",
    "mnc": "MNC",
    "mega_mnc": "mega-MNC",
    "govt": "government",
    "unknown": "company",
}


def _kind_move(a: EmployerKind, b: EmployerKind, b_is_product: bool) -> MoveKind | None:
    if a == "it_services" and (b in ("startup", "product", "mega_mnc") or b_is_product):
        return "services_to_product"
    if a in ("startup", "product") and b in ("mnc", "mega_mnc"):
        return "startup_to_mnc"
    if a == "mnc" and b == "mega_mnc":
        return "mnc_to_mega"
    return None


def detect_moves(stints: list[Stint], jd: JDAnalysis, kb: Knowledge) -> list[Move]:
    work = [s for s in stints if s.kind in FULL_TIME and s.start]
    moves: list[Move] = []
    for a, b in zip(work, work[1:], strict=False):
        if kind := _kind_move(a.employer_kind, b.employer_kind, False):
            moves.append(Move(kind=kind, from_label=a.organization, to_label=b.organization))
        if a.field and b.field and a.field != b.field:
            moves.append(Move(kind="field_switch", from_label=a.title, to_label=b.title))
    if not work:
        return moves
    latest = max(work, key=lambda s: (s.end is None, s.end or "", s.start))
    target_kind = jd_employer_kind(jd, kb)
    to = jd.company or LABEL[target_kind]
    if kind := _kind_move(latest.employer_kind, target_kind, jd.employer_type in ("product_startup", "gcc")):
        moves.append(
            Move(
                kind=kind, from_label=f"{latest.organization} ({LABEL[latest.employer_kind]})", to_label=to, target=True
            )
        )
    if latest.field and jd.role_family not in ("general", latest.field) and jd.role_family in kb.role_families:
        moves.append(Move(kind="field_switch", from_label=latest.title, to_label=jd.title, target=True))
    return moves
