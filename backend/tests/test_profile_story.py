from datetime import date

import pytest

from app.knowledge.loader import load_knowledge
from app.profile import build_profile
from app.profile.story import (
    continuity_score,
    internship_score,
    score_story,
    stability_score,
    transition_score,
)
from app.resume_ops import assign_ids
from app.schemas import (
    Answer,
    CareerGap,
    Contact,
    Entry,
    Evidence,
    JDAnalysis,
    LayoutReport,
    Move,
    Profile,
    ProjectFacts,
    ProjectRead,
    RecruiterVerdict,
    Requirement,
    RequirementMatch,
    ResumeDoc,
    Stint,
)
from app.scoring import score_all
from app.scoring.insights import build_insights

TODAY = date(2026, 10, 14)


@pytest.fixture
def kb():
    return load_knowledge()


def jd(musts=0) -> JDAnalysis:
    reqs = [
        Requirement(id=f"r{i}", text=f"Skill {i}", type="hard_skill", importance="must", keywords=["python"])
        for i in range(musts)
    ]
    return JDAnalysis(
        is_job_description=True,
        title="Software Developer",
        role_family="software_engineering",
        employer_type="product_startup",
        seniority="junior",
        suggested_region="india",
        requirements=reqs,
        ats_keywords=["python"],
    )


def ev(statuses=()) -> Evidence:
    return Evidence(
        matches=[RequirementMatch(requirement_id=f"r{i}", status=s, rationale="") for i, s in enumerate(statuses)],
        gaps=[],
        recruiter=RecruiterVerdict(decision="maybe", first_impression="", reasons=[]),
    )


def stint(i, kind="job", months=24, short=False, start="2022-01", field="software_engineering") -> Stint:
    return Stint(
        entry_id=f"exp{i}",
        organization="Org",
        title="Engineer",
        start=start,
        end="2024-01",
        months=months,
        precise=True,
        kind=kind,
        field=field,
        short=short,
    )


def gap(months) -> CareerGap:
    return CareerGap(id="gap:2023-01", start="2023-01", end="2023-12", months=months)


def resume(**kw) -> ResumeDoc:
    return assign_ids(ResumeDoc(contact=Contact(name="T", links=kw.pop("links", [])), **kw))


def test_student_weights(kb):
    r = resume(education=[Entry(title="B.Tech (CGPA 8.6)", organization="VIT", end="May 2027")], links=["github.com/t"])
    read = ProjectRead(project_id="prj0", title="P", score=90, facts=ProjectFacts(project_id="prj0"))
    profile = Profile(
        stage="student", study_year=4, stints=[stint(0, kind="internship", months=3)], projects=[read], as_of="2026-10"
    )
    sub = score_story(profile, r, jd(), ev(), "india", kb)
    assert sub.key == "story" and sub.score == 89


def test_no_dates_fresher_renormalises(kb):
    r = resume(education=[Entry(title="B.Tech", organization="VIT")])
    profile = Profile(
        stage="fresh_grad", stints=[Stint(entry_id="exp0", organization="A", title="Engineer")], as_of="2026-10"
    )
    sub = score_story(profile, r, jd(), ev(), "india", kb)
    signals = {e.signal for e in sub.explanations}
    assert "gap" not in signals and "short_stints" not in signals
    # projects 0 (weight 40), internships 20 (25), presentation 0 (20) over 85
    assert sub.score == round((25 * 20) / 85)


def test_continuity_by_region(kb):
    r = resume()
    for months, india, intl in ((8, 70, 85), (14, 50, 75)):
        p = Profile(stage="early", gaps=[gap(months)], as_of="2026-10")
        assert continuity_score(p, r, kb.regions["india"].story)[0] == india
        assert continuity_score(p, r, kb.regions["international"].story)[0] == intl
    answered = Profile(
        stage="early", gaps=[gap(8)], answers={"gap:2023-01": Answer(value="exam_prep")}, as_of="2026-10"
    )
    assert continuity_score(answered, r, kb.regions["india"].story)[0] == 90
    stated = resume(experience=[Entry(title="Career break: exam preparation", organization="", start="Jan 2023")])
    assert continuity_score(answered, stated, kb.regions["india"].story)[0] == 100


def test_stability_steps(kb):
    for n, expected in ((0, 100), (1, 85), (2, 60), (3, 30)):
        p = Profile(
            stage="early", stints=[stint(i, months=4, short=True, start="2024-01") for i in range(n)], as_of="2026-10"
        )
        assert stability_score(p)[0] == expected
    contracts = Profile(
        stage="early",
        stints=[stint(i, months=4, short=True, start="2024-01") for i in range(2)],
        answers={"stint:exp0": Answer(value="contract"), "stint:exp1": Answer(value="contract")},
        as_of="2026-10",
    )
    assert stability_score(contracts)[0] == 100


def test_internships_relevance(kb):
    p = Profile(stage="student", stints=[stint(0, kind="internship", months=1)], as_of="2026-10")
    assert internship_score(p, jd())[0] == 20
    other = Profile(stage="student", stints=[stint(0, kind="internship", months=3, field="marketing")], as_of="2026-10")
    assert internship_score(other, jd())[0] == 20
    virtual = Profile(stage="student", stints=[stint(0, kind="virtual_program", months=3)], as_of="2026-10")
    assert internship_score(virtual, jd())[0] == 20


def test_transition_field_switch(kb):
    r = resume(
        summary="Sales executive moving into software development.",
        projects=[Entry(title="Inventory API in Python", organization="Personal")],
    )
    p = Profile(
        stage="early",
        moves=[Move(kind="field_switch", from_label="BDE", to_label="Developer", target=True)],
        as_of="2026-10",
    )
    score, notes = transition_score(p, r, jd(musts=4), ev(["strong", "partial", "missing", "missing"]), kb)
    assert score == 75


def test_losses_become_ranked_story_actions(kb):
    r = resume(experience=[Entry(title="Engineer", organization="A", start="Jan 2020", end="Present")])
    p = Profile(stage="mid", gaps=[gap(14)], stints=[stint(0)], as_of="2026-10")
    report = score_all(
        "text",
        LayoutReport(file_type="pdf", pages=1, char_count=4, word_count=1),
        r,
        jd(),
        ev(),
        "india",
        kb,
        profile=p,
    )
    assert set(report.subscores) == {"match", "ats", "quality", "region", "story"}
    assert abs(sum(report.weights.values()) - 1.0) < 1e-9
    story = report.subscores["story"]
    assert all(e.fix for e in story.explanations if e.impact < 0)
    insights = build_insights(report, jd(), ev(), kb.regions["india"], [], "mid")
    assert any(a.source == "story" for a in insights.actions)


def test_score_all_without_profile_renormalises(kb):
    r = resume()
    report = score_all(
        "text", LayoutReport(file_type="pdf", pages=1, char_count=4, word_count=1), r, jd(), ev(), "india", kb
    )
    assert set(report.subscores) == {"match", "ats", "quality", "region"}
    assert abs(sum(report.weights.values()) - 1.0) < 1e-9


def test_build_profile_end_to_end(kb):
    r = resume(
        experience=[Entry(title="Systems Engineer", organization="TCS", start="Jul 2024", end="Present")],
        education=[Entry(title="B.Tech", organization="VIT", end="May 2022")],
    )
    p = build_profile(r, jd(), ev(), [], "india", kb, TODAY)
    assert p.stage == "early" and p.as_of == "2026-10"
    assert [m.kind for m in p.moves if m.target] == ["services_to_product"]
