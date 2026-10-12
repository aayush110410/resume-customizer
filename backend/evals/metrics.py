import statistics

from app.schemas import Evidence


def stability(scores: list[int]) -> float:
    return statistics.pstdev(scores) if len(scores) > 1 else 0.0


def ordering_ok(group: list[tuple[int, int]]) -> bool:
    """(expected_rank, score) pairs: rank 1 must score strictly highest, and so on."""
    scores = [s for _, s in sorted(group)]
    return all(a > b for a, b in zip(scores, scores[1:], strict=False))


def grounding_rate(evs: list[Evidence]) -> float:
    quoted = [m for e in evs for m in e.matches if m.quote]
    return sum(m.verified for m in quoted) / len(quoted) if quoted else 1.0
