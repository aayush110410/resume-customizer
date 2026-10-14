from datetime import date

import pytest

from app.knowledge.loader import load_knowledge
from app.profile import build_profile
from app.profile.clarify import rescore
from app.resume_ops import assign_ids, render_plain
from app.schemas import (
    Analysis,
    Answer,
    Contact,
    Entry,
    Evidence,
    Insights,
    JDAnalysis,
    LayoutReport,
    RecruiterVerdict,
    ResumeDoc,
)
from app.scoring import score_all

TODAY = date(2026, 10, 14)
VERDICT = RecruiterVerdict(decision="maybe", first_impression="", reasons=[])


@pytest.fixture
def kb():
    return load_knowledge()


def _resume() -> ResumeDoc:
    return assign_ids(
        ResumeDoc(
            contact=Contact(name="T"),
            experience=[
                Entry(title="Software Engineer", organization="Acme Labs", start="Jan 2025", end="Present"),
                Entry(title="Software Engineer", organization="Foo Systems", start="Jan 2024", end="Apr 2024"),
                Entry(title="Software Engineer", organization="Bar Tech", start="May 2023", end="Aug 2023"),
                Entry(title="SDE Intern", organization="Baz", start="Jan 2021", end="Mar 2021"),
            ],
            education=[Entry(title="B.Tech", organization="VIT", start="Jul 2017", end="May 2021")],
        )
    )


def _jd() -> JDAnalysis:
    return JDAnalysis(
        is_job_description=True,
        title="Backend Engineer",
        role_family="software_engineering",
        employer_type="product_startup",
        seniority="junior",
        suggested_region="india",
        requirements=[],
        ats_keywords=[],
    )


def _ev() -> Evidence:
    return Evidence(matches=[], gaps=[], recruiter=VERDICT)


def _analysis(kb) -> Analysis:
    resume, jd, ev = _resume(), _jd(), _ev()
    profile = build_profile(resume, jd, ev, [], "india", kb, TODAY)
    text = render_plain(resume)
    layout = LayoutReport(file_type="pdf", pages=1, char_count=len(text), word_count=len(text.split()))
    scores = score_all(text, layout, resume, jd, ev, "india", kb, profile)
    return Analysis(
        region="india",
        resume=resume,
        resume_text=text,
        layout=layout,
        jd=jd,
        evidence=ev,
        scores=scores,
        insights=Insights(actions=[], tips=[], recruiter=VERDICT, missing_keywords=[]),
        prompt_version="t",
        models={},
        profile=profile,
    )


def test_questions_ordered_and_capped(kb):
    qs = build_profile(_resume(), _jd(), _ev(), [], "india", kb, TODAY).questions
    assert qs[0].id == "stage" and len(qs) <= 6
    impacts = [q.impact for q in qs[1:]]
    assert impacts == sorted(impacts, reverse=True)
    ids = {q.id for q in qs}
    assert {"gap:2021-06", "stint:exp1", "stint:exp2", "employer:exp0"} <= ids


def test_gap_options(kb):
    q = next(q for q in build_profile(_resume(), _jd(), _ev(), [], "india", kb, TODAY).questions if q.kind == "gap")
    assert [o.value for o in q.options] == [
        "higher_studies",
        "exam_prep",
        "health",
        "family",
        "layoff",
        "startup",
        "relocation",
        "other",
    ]
    assert q.options[1].label == "Exam prep (UPSC/GATE/CAT/other)" and q.allow_text
    assert q.prompt == "What were you doing from Jun 2021 to Apr 2023 (23 months)?"


def test_answers_reclassify_and_retarget(kb):
    base = build_profile(_resume(), _jd(), _ev(), [], "india", kb, TODAY)
    assert not any(m.target for m in base.moves)
    p = build_profile(
        _resume(),
        _jd(),
        _ev(),
        [],
        "india",
        kb,
        TODAY,
        answers={"intern:exp3": Answer(value="virtual"), "employer:exp0": Answer(value="it_services")},
    )
    assert next(s for s in p.stints if s.entry_id == "exp3").kind == "virtual_program"
    assert [m.kind for m in p.moves if m.target] == ["services_to_product"]


def test_stage_answer_sets_student_and_fresher_level(kb):
    a = _analysis(kb)
    r = rescore(a, {"stage": Answer(value="student:3")}, kb)
    assert (r.profile.stage, r.profile.study_year) == ("student", 3)
    assert r.insights is not None


def test_rescore_idempotent_and_ids_stable(kb):
    a = _analysis(kb)
    answers = {"gap:2021-06": Answer(value="exam_prep"), "stint:exp1": Answer(value="contract")}
    one, two = rescore(a, answers, kb), rescore(a, answers, kb)
    assert one.scores == two.scores
    assert one.scores.subscores["story"].score > a.scores.subscores["story"].score
    staged = rescore(a, {**answers, "stage": Answer(value="mid")}, kb)
    assert "gap:2021-06" in staged.profile.answers
    assert {"gap:2021-06", "stint:exp1"} <= {q.id for q in staged.profile.questions}  # answered stay visible
    assert len(staged.profile.questions) <= 6
    assert one.scores.subscores["match"] == a.scores.subscores["match"]


def test_unknown_question_or_option_rejected(kb):
    a = _analysis(kb)
    with pytest.raises(ValueError, match="unknown question"):
        rescore(a, {"gap:1999-01": Answer(value="health")}, kb)
    with pytest.raises(ValueError, match="invalid answer"):
        rescore(a, {"stint:exp1": Answer(value="astronaut")}, kb)


def test_rescore_returns_level(kb):
    a = _analysis(kb)
    assert rescore(a, {"stage": Answer(value="mid")}, kb).level == "mid"
    assert rescore(a, {}, kb).level == a.resume.level


def test_rescore_is_fast_and_reverifies_names(kb):
    import time

    from app.schemas import Bullet, CustomName, ProjectFacts

    resume = _resume().model_copy(deep=True)
    names = ["Zephyr", "Nimbus", "Kestrel", "Orion", "Vega", "Atlas"]
    resume.projects = [
        Entry(
            id=f"prj{i}",
            title=n,
            organization="Personal",
            bullets=[Bullet(id=f"prj{i}.b0", text=f"Built {n} for 2,000 users in Go and Redis")],
        )
        for i, n in enumerate(names)
    ]
    facts = [
        ProjectFacts(project_id=f"prj{i}", purpose="for 2,000 users", custom_names=[CustomName(name=n)])
        for i, n in enumerate(names)
    ]
    facts[0].custom_names += [CustomName(name=f"Fake{i}") for i in range(90)]  # tampered: not in the resume
    a = _analysis(kb)
    text = render_plain(resume)
    profile = build_profile(resume, a.jd, a.evidence, facts, "india", kb, TODAY)
    a = a.model_copy(update={"resume": resume, "resume_text": text, "profile": profile})
    start = time.perf_counter()
    r = rescore(a, {"name:zephyr": Answer(value="own", text="event store")}, kb)
    assert time.perf_counter() - start < 0.5
    kept = {c.name for p in r.profile.projects for c in p.facts.custom_names}
    assert kept == set(names)


def test_stage_options_cover_first_and_fifth_year(kb):
    q = build_profile(_resume(), _jd(), _ev(), [], "india", kb, TODAY).questions[0]
    assert {"student:1", "student:5"} <= {o.value for o in q.options}


def test_every_short_stint_answer_moves_the_score(kb):
    from app.profile.story import score_story

    resume = assign_ids(
        ResumeDoc(
            contact=Contact(name="T"),
            experience=[
                Entry(title="Software Engineer", organization=f"Org{i}", start=f"{m1} 2024", end=f"{m2} 2024")
                for i, (m1, m2) in enumerate([("Jan", "Mar"), ("Apr", "Jun"), ("Jul", "Sep"), ("Oct", "Dec")])
            ]
            + [Entry(title="Software Engineer", organization="Stay", start="Jan 2025", end="Present")],
        )
    )

    def story(answers):
        p = build_profile(resume, _jd(), _ev(), [], "india", kb, TODAY, answers=answers)
        return score_story(p, resume, _jd(), _ev(), "india", kb).score

    one_contract = story({"stint:exp0": Answer(value="contract")})
    assert (
        story({})
        < one_contract
        < story({"stint:exp0": Answer(value="contract"), "stint:exp1": Answer(value="contract")})
    )
