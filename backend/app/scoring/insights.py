"""Ranks what to fix by estimated overall-score gain, and attaches region tips and the recruiter verdict."""

from app.knowledge.loader import select_tips
from app.knowledge.models import RegionPack
from app.schemas import Action, Evidence, Insights, JDAnalysis, Level, ScoreReport
from app.scoring.match import CREDIT, WEIGHT

MAX_ACTIONS = 8


def build_insights(
    report: ScoreReport, jd: JDAnalysis, ev: Evidence, region: RegionPack, missing: list[str], level: Level
) -> Insights:
    weights = report.weights
    status = {m.requirement_id: m.status for m in ev.matches}
    gaps = {g.requirement_id: g for g in ev.gaps if g.requirement_id}
    total = sum(WEIGHT[r.importance] for r in jd.requirements) or 1
    actions: list[Action] = []
    for r in jd.requirements:
        s = status.get(r.id, "missing")
        if s == "strong":
            continue
        gap = gaps.get(r.id)
        actions.append(
            Action(
                title=gap.title if gap else f"Strengthen evidence for “{r.text}”",
                detail=gap.action if gap else f"Currently {s}. Show it in a bullet with scope and result.",
                est_gain=100 * weights["match"] * WEIGHT[r.importance] * (1 - CREDIT[s]) / total,
                source="match",
                suggested_bullet=gap.suggested_bullet if gap else None,
            )
        )
    for key in ("ats", "quality", "region"):
        sub = report.subscores.get(key)
        for e in sub.explanations if sub else []:
            if e.impact < 0 and e.fix:
                actions.append(Action(title=e.detail, detail=e.fix, est_gain=weights[key] * -e.impact, source=key))
    actions.sort(key=lambda a: a.est_gain, reverse=True)
    actions = [a.model_copy(update={"est_gain": round(a.est_gain, 1)}) for a in actions[:MAX_ACTIONS]]

    allowed = {t.id for t in select_tips(region, jd, level)}
    return Insights(
        actions=actions,
        tips=[t for t in ev.tips if t.tip_id in allowed],
        recruiter=ev.recruiter,
        missing_keywords=missing,
    )
