import pytest

from app.knowledge.loader import load_knowledge
from app.schemas import (
    Bullet,
    Entry,
    Evidence,
    Gap,
    LayoutReport,
    PersonalizedTip,
    RecruiterVerdict,
    Requirement,
    RequirementMatch,
    ResumeDoc,
)
from app.scoring import score_all
from app.scoring.insights import build_insights
from app.scoring.quality import score_quality
from app.scoring.region import score_region

GOOD_SUMMARY = (
    "Backend engineer with four years of experience building high-volume payment APIs in Python and Go, "
    "focused on reliability, latency and developer tooling for fintech teams in Bengaluru."
)
LAYOUT = LayoutReport(file_type="pdf", pages=1, char_count=900, word_count=400)


@pytest.fixture
def kb():
    return load_knowledge()


def doc_with(bullets, summary=GOOD_SUMMARY, contact=None, level="mid"):
    from app.schemas import Contact

    return ResumeDoc(
        contact=contact or Contact(name="A"),
        summary=summary,
        experience=[Entry(id="exp0", title="SE", organization="X", bullets=bullets)],
        level=level,
    )


FOUR = [
    Bullet(id="exp0.b0", text="Reduced checkout latency by 30% for two million daily payment requests", kind="impact"),
    Bullet(
        id="exp0.b1",
        text="Built a reconciliation service that cut manual finance work by 12 hours weekly",
        kind="impact",
    ),
    Bullet(
        id="exp0.b2",
        text="Led the migration of billing jobs from cron scripts to a managed workflow engine",
        kind="duty",
    ),
    Bullet(
        id="exp0.b3", text="Responsible for maintaining internal admin dashboards used by the support team", kind="duty"
    ),
]


def test_quality_components(kb):
    # quantified 2/4 → 30; action 3/4 → 15; length 4/4 → 15; impact 2/4 → 12.5; hygiene 10; summary 10 = 92.5
    assert score_quality(doc_with(FOUR), kb).score == 93


def test_quality_flags_weak_opener_buzzword_pronoun(kb):
    bullets = [*FOUR[:3], Bullet(id="exp0.b3", text="Responsible for my team's hardworking culture and dashboards")]
    signals = {e.signal for e in score_quality(doc_with(bullets), kb).explanations}
    assert {"weak_opener", "buzzwords", "first_person"} <= signals


def test_quality_generic_objective_summary(kb):
    sub = score_quality(
        doc_with(FOUR, summary="Seeking a challenging role to work in a challenging environment and grow."), kb
    )
    assert sub.score == 87 and "summary_generic" in {e.signal for e in sub.explanations}  # 92.5 - 10 + 4 = 86.5


def test_quality_fresher_no_summary_no_experience(sample_doc, kb):
    fresher = ResumeDoc(contact=sample_doc.contact, projects=sample_doc.projects)
    assert 0 < score_quality(fresher, kb).score < 100


def test_quality_no_bullets_is_zero(kb):
    assert score_quality(ResumeDoc(contact={"name": "A"}), kb).score == 0


DECL = "Date of Birth: 01/01/1998\nDECLARATION\nI hereby declare that the above information is true."


def test_region_india_declaration_product_vs_psu(jd_factory, kb):
    india, doc = kb.regions["india"], doc_with(FOUR)
    assert score_region(DECL, LAYOUT, doc, jd_factory(employer_type="product_startup"), india).score == 90
    assert score_region(DECL, LAYOUT, doc, jd_factory(employer_type="psu_govt"), india).score == 100


def test_region_international_photo_and_ctc(jd_factory, kb):
    layout = LAYOUT.model_copy(update={"image_count": 1})
    sub = score_region("Current CTC: 12 LPA", layout, doc_with(FOUR), jd_factory(), kb.regions["international"])
    assert sub.score == 100 - 12 - 5


def test_region_missing_cgpa_for_fresher_services(jd_factory, kb):
    sub = score_region(
        "B.Tech Computer Science, 2024",
        LAYOUT,
        doc_with(FOUR, level="fresher"),
        jd_factory(employer_type="it_services"),
        kb.regions["india"],
    )
    assert "academic_score" in {e.signal for e in sub.explanations}
    with_cgpa = score_region(
        "B.Tech Computer Science, CGPA 8.4/10, 2024",
        LAYOUT,
        doc_with(FOUR, level="fresher"),
        jd_factory(employer_type="it_services"),
        kb.regions["india"],
    )
    assert "academic_score" not in {e.signal for e in with_cgpa.explanations}


def test_region_overlength(jd_factory, kb):
    sub = score_region(
        "", LAYOUT.model_copy(update={"pages": 3}), doc_with(FOUR, level="fresher"), jd_factory(), kb.regions["india"]
    )
    assert "too_long" in {e.signal for e in sub.explanations}


REQS = [
    Requirement(id="r1", text="Python", type="hard_skill", importance="must"),
    Requirement(id="r2", text="Kafka", type="tool", importance="nice"),
]
EV = Evidence(
    matches=[
        RequirementMatch(requirement_id="r1", status="missing", rationale=""),
        RequirementMatch(requirement_id="r2", status="partial", rationale=""),
    ],
    gaps=[
        Gap(
            requirement_id="r1",
            title="No Python evidence",
            action="Add a Python bullet",
            suggested_bullet="Built [X] in Python",
        )
    ],
    recruiter=RecruiterVerdict(decision="maybe", first_impression="ok", reasons=[]),
    tips=[PersonalizedTip(tip_id="definitely-not-a-tip", advice="x")],
)


def test_insights_sorted_with_bullet_and_unknown_tips_dropped(jd_factory, kb):
    jd = jd_factory(requirements=REQS, ats_keywords=["Python"])
    report = score_all(DECL, LAYOUT, doc_with(FOUR), jd, EV, "india", kb)
    ins = build_insights(report, jd, EV, kb.regions["india"], ["Python"], "mid")
    gains = [a.est_gain for a in ins.actions]
    assert gains == sorted(gains, reverse=True) and len(ins.actions) <= 8
    top = ins.actions[0]
    assert top.title == "No Python evidence" and top.suggested_bullet == "Built [X] in Python"
    assert top.est_gain == 30.0  # 100 * 0.40 * 3 * 1 / 4
    assert ins.tips == [] and ins.missing_keywords == ["Python"]


def test_score_all_regions_differ(jd_factory, kb):
    jd = jd_factory(requirements=REQS, ats_keywords=["Python"])
    india = score_all(DECL, LAYOUT, doc_with(FOUR), jd, EV, "india", kb)
    intl = score_all(DECL, LAYOUT, doc_with(FOUR), jd, EV, "international", kb)
    assert india.weights != intl.weights and india.subscores["region"].score != intl.subscores["region"].score
