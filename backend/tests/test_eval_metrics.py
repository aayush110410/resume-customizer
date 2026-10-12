import pytest

from app.schemas import Evidence, RecruiterVerdict, RequirementMatch
from evals.metrics import grounding_rate, ordering_ok, stability


def ev(*verified):
    ms = [
        RequirementMatch(requirement_id=f"r{i}", status="strong", quote="q", rationale="", verified=v)
        for i, v in enumerate(verified)
    ]
    return Evidence(matches=ms, gaps=[], recruiter=RecruiterVerdict(decision="maybe", first_impression="", reasons=[]))


def test_stability_is_population_stdev():
    assert stability([70, 72, 74]) == pytest.approx(1.633, abs=1e-3)
    assert stability([80]) == 0


def test_ordering():
    assert ordering_ok([(1, 80), (2, 60), (3, 30)])
    assert not ordering_ok([(1, 60), (2, 61)])


def test_grounding_rate():
    assert grounding_rate([ev(True, False), ev(True, False)]) == 0.5
    assert grounding_rate([]) == 1.0
