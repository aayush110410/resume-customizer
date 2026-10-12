import math

from app.schemas import ScoreReport, SubScore


def round_half_up(x: float) -> int:
    """Scores round 73.5 → 74 regardless of float noise (0.15 * 90 == 13.499999…)."""
    return max(0, min(100, math.floor(x + 0.5 + 1e-9)))


def build_report(subs: list[SubScore], weights: dict[str, float], knockouts: list[str]) -> ScoreReport:
    overall = round_half_up(sum(weights[s.key] * s.score for s in subs))
    return ScoreReport(overall=overall, weights=weights, subscores={s.key: s for s in subs}, knockouts=knockouts)
