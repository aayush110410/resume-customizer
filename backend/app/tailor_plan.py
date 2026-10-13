"""The tailoring plan, decided in code. The writer model only rewrites each bullet to its instruction.

- Order: within each entry, bullets that prove heavier requirements come first (must 3 · should 2 · nice 1,
  scaled by how well they prove it), with original order as the tie-break.
- Skills: JD-matched items move to the front of their group and groups with more matches move up. Nothing is dropped.
- Mirroring: a JD term may replace the resume's wording only when the bullet already says the same thing in other
  words (a synonym from the knowledge base), so mirroring never adds a skill.
- Summary: built from the verbatim evidence of strong must-have matches, plus years and current title.
"""

import re
from dataclasses import dataclass, field

from app.knowledge.models import Knowledge
from app.schemas import Evidence, JDAnalysis, ResumeDoc, SkillGroup
from app.scoring.match import CREDIT, WEIGHT
from app.text_utils import contains_term, normalize

_NUM = re.compile(r"(?<![A-Za-z])\d[\d,]*(?:\.\d+)?\s?%?(?![A-Za-z])")


@dataclass
class BulletPlan:
    id: str
    entry_id: str
    text: str
    requirement_ids: list[str] = field(default_factory=list)
    relevance: float = 0.0
    mirror: list[tuple[str, str]] = field(default_factory=list)  # (resume wording, JD wording)
    weak_opener: str | None = None
    numbers: list[str] = field(default_factory=list)
    must_rewrite: bool = False  # weak opener or no action verb: the writer may not return it unchanged


@dataclass
class TailorPlan:
    bullets: list[BulletPlan]
    order: dict[str, list[str]]  # entry id → bullet ids in the planned order
    skills: list[SkillGroup]
    summary_facts: list[str]


def _jd_terms(jd: JDAnalysis) -> list[str]:
    seen: dict[str, str] = {}
    for t in list(jd.ats_keywords) + [k for q in jd.requirements for k in q.keywords]:
        if t.strip():
            seen.setdefault(normalize(t), t.strip())  # first spelling wins (the JD's own casing)
    return list(seen.values())


def _matches_jd(item: str, jd_terms: list[str], kb: Knowledge) -> int | None:
    """Index of the first JD term this skill item satisfies (directly or via a synonym), else None."""
    for i, term in enumerate(jd_terms):
        if any(contains_term(item, v) for v in kb.synonyms.variants(term)) or contains_term(term, item):
            return i
    return None


def build_plan(resume: ResumeDoc, jd: JDAnalysis, ev: Evidence, kb: Knowledge) -> TailorPlan:
    importance = {q.id: q.importance for q in jd.requirements}
    proves: dict[str, list[tuple[str, float]]] = {}
    for m in ev.matches:
        if m.requirement_id in importance:
            for bid in m.bullet_ids:
                proves.setdefault(bid, []).append(
                    (m.requirement_id, WEIGHT[importance[m.requirement_id]] * CREDIT[m.status])
                )

    terms = _jd_terms(jd)
    bullets: list[BulletPlan] = []
    order: dict[str, list[str]] = {}
    for section in ("experience", "projects"):
        for entry in getattr(resume, section):
            plans = []
            for b in entry.bullets:
                reqs = proves.get(b.id, [])
                plan = BulletPlan(
                    id=b.id,
                    entry_id=entry.id,
                    text=b.text,
                    requirement_ids=[r for r, _ in reqs],
                    relevance=sum(w for _, w in reqs) + 0.25 * sum(contains_term(b.text, t) for t in jd.ats_keywords),
                    numbers=[re.sub(r"[,\s]", "", n) for n in _NUM.findall(b.text)],
                    weak_opener=next((w for w in kb.lexicons.weak_openers if normalize(b.text).startswith(w)), None),
                )
                first = re.findall(r"[a-z]+", normalize(b.text))[:1]
                plan.must_rewrite = bool(plan.weak_opener) or not (first and first[0] in kb.lexicons.action_verbs)
                for term in terms:
                    if contains_term(b.text, term):
                        continue
                    alias = next(
                        (v for v in kb.synonyms.variants(term) if v != normalize(term) and contains_term(b.text, v)),
                        None,
                    )
                    if alias and (alias, term) not in plan.mirror:
                        plan.mirror.append((alias, term))
                plans.append(plan)
            bullets += plans
            ranked = sorted(enumerate(plans), key=lambda ip: (-ip[1].relevance, ip[0]))
            order[entry.id] = [p.id for _, p in ranked]

    def rank_items(group: SkillGroup) -> SkillGroup:
        keyed = [(_matches_jd(item, terms, kb), i, item) for i, item in enumerate(group.items)]
        ranked = sorted(keyed, key=lambda k: (k[0] is None, k[0] if k[0] is not None else 0, k[1]))
        return SkillGroup(name=group.name, items=[item for _, _, item in ranked])

    groups = [rank_items(g) for g in resume.skills]
    hits = [sum(_matches_jd(i, terms, kb) is not None for i in g.items) for g in groups]
    skills = [g for _, _, g in sorted(zip([-h for h in hits], range(len(groups)), groups, strict=True))]

    by_bullet = {b.id: b.text for b in bullets}
    facts = []
    for q in jd.requirements:
        if q.importance != "must":
            continue
        m = next((x for x in ev.matches if x.requirement_id == q.id and x.status == "strong" and x.bullet_ids), None)
        if m and (text := by_bullet.get(m.bullet_ids[0])) and text not in facts:
            facts.append(text)
    return TailorPlan(bullets=bullets, order=order, skills=skills, summary_facts=facts[:3])
