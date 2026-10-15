import math

from app.schemas import ScoreReport, SubScore


def round_half_up(x: float) -> int:
    """Rounds half up (73.5 gives 74) even when float noise makes 0.15 * 90 come out as 13.499999."""
    return max(0, min(100, math.floor(x + 0.5 + 1e-9)))


def build_report(subs: list[SubScore], weights: dict[str, float], knockouts: list[str]) -> ScoreReport:
    """Weights renormalise over the sub-scores present (Story sits out when there is nothing to judge)."""
    total = sum(weights[s.key] for s in subs)
    weights = {s.key: weights[s.key] / total for s in subs}
    overall = round_half_up(sum(weights[s.key] * s.score for s in subs))
    return ScoreReport(overall=overall, weights=weights, subscores={s.key: s for s in subs}, knockouts=knockouts)
