"""Region fit: personal-detail and terminology conventions, page norms and expected signals from the YAML pack."""

import re

from app.knowledge.models import SEVERITY_PENALTY, RegionPack
from app.schemas import Explanation, JDAnalysis, LayoutReport, ResumeDoc, SubScore
from app.scoring.aggregate import round_half_up

TERM_CAP = 20
FLAGS = re.IGNORECASE | re.MULTILINE


def _found(patterns: list[str], text: str) -> bool:
    return any(re.search(p, text, FLAGS) for p in patterns)


def score_region(text: str, layout: LayoutReport, resume: ResumeDoc, jd: JDAnalysis, region: RegionPack) -> SubScore:
    ex: list[Explanation] = []
    score = 100.0

    for rule in region.personal_rules:
        hit = _found(rule.patterns, text) or (rule.id == "photo" and layout.image_count > 0)
        penalty = SEVERITY_PENALTY[rule.severity_for(jd.employer_type)] if hit else 0
        if penalty:
            score -= penalty
            ex.append(Explanation(signal=rule.id, impact=-penalty, detail=rule.message, fix=rule.fix))

    term_loss = 0
    for rule in region.term_rules:
        penalty = SEVERITY_PENALTY[rule.severity_for(jd.employer_type)] if _found(rule.patterns, text) else 0
        penalty = min(penalty, TERM_CAP - term_loss)
        if penalty > 0:
            term_loss += penalty
            ex.append(Explanation(signal=rule.id, impact=-penalty, detail=rule.message, fix=rule.fix))
    score -= term_loss

    limit = region.max_pages(resume.level)
    if layout.pages > limit:
        score -= 15
        ex.append(
            Explanation(
                signal="too_long",
                impact=-15,
                detail=f"{layout.pages} pages; {region.label} recruiters expect {limit} at your level.",
                fix="Trim older and less relevant detail.",
            )
        )

    for exp in region.expectations:
        applies = resume.level in exp.levels and jd.employer_type in exp.employer_types
        if applies and not _found(exp.patterns, text):
            score -= exp.penalty
            ex.append(
                Explanation(signal=exp.id, impact=-exp.penalty, detail=f"Expected here: {exp.label}.", fix=exp.fix)
            )

    ex.sort(key=lambda e: e.impact)
    return SubScore(key="region", score=round_half_up(max(0.0, score)), explanations=ex)
