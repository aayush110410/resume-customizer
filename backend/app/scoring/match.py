"""JD match = weighted requirement coverage from LLM-extracted, grounding-verified evidence."""

from app.schemas import Evidence, Explanation, JDAnalysis, MatchStatus, SubScore
from app.scoring.aggregate import round_half_up

WEIGHT = {"must": 3, "should": 2, "nice": 1}
CREDIT: dict[MatchStatus, float] = {"strong": 1.0, "partial": 0.6, "transferable": 0.4, "missing": 0.0}


def years_factor(min_years: float | None, years: float) -> float:
    if not min_years or years >= min_years:
        return 1.0
    return max(0.75, 1 - 0.08 * (min_years - years))


def score_match(jd: JDAnalysis, ev: Evidence, years: float) -> tuple[SubScore, list[str]]:
    if not jd.requirements:
        note = Explanation(signal="no_requirements", impact=0, detail="No requirements could be extracted from the JD.")
        return SubScore(key="match", score=0, explanations=[note]), []

    status = {m.requirement_id: m.status for m in ev.matches}
    fixes = {g.requirement_id: g.action for g in ev.gaps if g.requirement_id}
    total = sum(WEIGHT[r.importance] for r in jd.requirements)
    got, explanations, knockouts = 0.0, [], []
    for r in jd.requirements:
        s = status.get(r.id, "missing")
        w, c = WEIGHT[r.importance], CREDIT[s]
        got += w * c
        if s != "strong":
            explanations.append(
                Explanation(
                    signal=f"requirement_{s}",
                    impact=-100 * w * (1 - c) / total,
                    detail=f"{r.text} ({r.importance}-have): {s}",
                    fix=fixes.get(r.id) or f"Show concrete evidence of “{r.text}” in an experience or project bullet.",
                )
            )
        if s == "missing" and r.importance == "must":
            knockouts.append(r.text)

    raw = 100 * got / total
    factor = years_factor(jd.min_years, years)
    if factor < 1:
        explanations.append(
            Explanation(
                signal="years_gap",
                impact=-(raw - raw * factor),
                detail=f"The JD asks for {jd.min_years:g}+ years; the resume shows about {years:g}.",
                fix="Make the scope and seniority of your work explicit (team size, ownership, scale).",
            )
        )
    explanations.sort(key=lambda e: e.impact)
    return SubScore(key="match", score=round_half_up(raw * factor), explanations=explanations), knockouts
