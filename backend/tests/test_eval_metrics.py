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


def test_label_accuracy_maps_requirements_to_first_matching_concept():
    from app.schemas import Requirement
    from evals.metrics import label_accuracy

    concepts = [
        {"id": "aws_cert", "aliases": ["aws certification"], "ok": ["missing"]},
        {"id": "aws", "aliases": ["aws"], "ok": ["missing"]},
        {"id": "java", "aliases": ["java"], "ok": ["strong"]},
    ]
    reqs = [
        Requirement(id="r1", text="AWS certification", type="certification", importance="nice"),
        Requirement(id="r2", text="Hands-on AWS", type="tool", importance="must"),
        Requirement(id="r3", text="Java or Python", type="hard_skill", importance="must"),
        Requirement(id="r4", text="Team player", type="soft_skill", importance="nice"),
    ]
    ev = ev_with({"r1": "missing", "r2": "partial", "r3": "strong", "r4": "strong"})
    result = label_accuracy(reqs, ev, concepts)
    assert result == {"correct": 2, "judged": 3, "wrong": ["aws: partial"], "uncovered": []}


def ev_with(statuses):
    return Evidence(
        matches=[RequirementMatch(requirement_id=k, status=v, rationale="") for k, v in statuses.items()],
        gaps=[],
        recruiter=RecruiterVerdict(decision="maybe", first_impression="", reasons=[]),
    )


def test_label_maps_to_the_concept_named_earliest_in_the_requirement():
    from app.schemas import Requirement
    from evals.metrics import label_accuracy

    concepts = [
        {"id": "payments", "aliases": ["payment"], "ok": ["missing"]},
        {"id": "python", "aliases": ["python"], "ok": ["strong"]},
    ]
    reqs = [
        Requirement(
            id="r1", text="Build Python microservices for payment orchestration", type="hard_skill", importance="should"
        )
    ]
    assert label_accuracy(reqs, ev_with({"r1": "strong"}), concepts)["correct"] == 1
