import pytest

from app.knowledge.loader import load_knowledge
from app.resume_ops import assign_ids
from app.schemas import Bullet, Evidence, RecruiterVerdict, Requirement, RequirementMatch, SkillGroup
from app.tailor_plan import build_plan


@pytest.fixture
def doc(sample_doc):
    d = sample_doc.model_copy(deep=True)
    d.experience[0].bullets = [
        Bullet(text="Responsible for nightly billing jobs"),
        Bullet(text="Deployed 12 services on k8s with Helm"),
        Bullet(text="Built REST APIs in Python for payments"),
    ]
    d.skills = [
        SkillGroup(name="Languages", items=["Java", "Python", "Go"]),
        SkillGroup(name="Infra", items=["Docker", "Kubernetes"]),
    ]
    return assign_ids(d)


@pytest.fixture
def jd(jd_factory):
    return jd_factory(
        requirements=[
            Requirement(id="r1", text="Python", type="hard_skill", importance="must", keywords=["python"]),
            Requirement(id="r2", text="Kubernetes", type="tool", importance="should", keywords=["kubernetes"]),
        ],
        ats_keywords=["Python", "Kubernetes", "REST APIs"],
    )


def ev():
    return Evidence(
        matches=[
            RequirementMatch(requirement_id="r1", status="strong", bullet_ids=["exp0.b2"], quote="q", rationale=""),
            RequirementMatch(requirement_id="r2", status="strong", bullet_ids=["exp0.b1"], quote="q", rationale=""),
        ],
        gaps=[],
        recruiter=RecruiterVerdict(decision="maybe", first_impression="", reasons=[]),
    )


def test_bullets_ordered_by_requirement_weight(doc, jd):
    plan = build_plan(doc, jd, ev(), load_knowledge())
    assert plan.order["exp0"] == ["exp0.b2", "exp0.b1", "exp0.b0"]  # must-have proof, then should-have, then neither
    assert plan.order["exp1"] == ["exp1.b0", "exp1.b1"]  # nothing relevant: original order kept


def test_bullet_instructions(doc, jd):
    by_id = {b.id: b for b in build_plan(doc, jd, ev(), load_knowledge()).bullets}
    assert by_id["exp0.b1"].mirror == [("k8s", "Kubernetes")]
    assert by_id["exp0.b1"].requirement_ids == ["r2"] and by_id["exp0.b1"].numbers == ["12"]
    assert by_id["exp0.b0"].weak_opener == "responsible for"
    assert by_id["exp0.b2"].mirror == []  # already uses the JD's word


def test_skills_reordered_by_jd_match_without_losing_any(doc, jd):
    skills = build_plan(doc, jd, ev(), load_knowledge()).skills
    assert [g.name for g in skills] == ["Languages", "Infra"]
    assert skills[0].items == ["Python", "Java", "Go"] and skills[1].items == ["Kubernetes", "Docker"]


def test_summary_facts_are_strong_must_have_quotes(doc, jd):
    plan = build_plan(doc, jd, ev(), load_knowledge())
    assert plan.summary_facts == ["Built REST APIs in Python for payments"]
