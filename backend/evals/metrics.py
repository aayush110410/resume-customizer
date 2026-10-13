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


def _earliest(text: str, concepts: list[dict]) -> dict | None:
    """The concept the requirement names first (ties: the longer alias, then label order)."""
    import re

    from app.text_utils import contains_term, normalize

    best, key = None, None
    norm = normalize(text)
    for order, c in enumerate(concepts):
        for a in c["aliases"]:
            if contains_term(text, a):
                m = re.search(re.escape(normalize(a)), norm)
                k = (m.start() if m else 0, -len(a), order)
                if key is None or k < key:
                    best, key = c, k
    return best


def label_accuracy(requirements, ev: Evidence, concepts: list[dict]) -> dict:
    """Each extracted requirement is judged against the first hand-labelled concept it names."""

    status = {m.requirement_id: m.status for m in ev.matches}
    correct, judged, wrong, seen = 0, 0, [], set()
    for req in requirements:
        text = " ".join([req.text, *req.keywords])
        concept = _earliest(text, concepts)
        if concept is None:
            continue
        seen.add(concept["id"])
        judged += 1
        got = status.get(req.id, "missing")
        if got in concept["ok"]:
            correct += 1
        else:
            wrong.append(f"{concept['id']}: {got}")
    return {"correct": correct, "judged": judged, "wrong": wrong, "uncovered": []}
