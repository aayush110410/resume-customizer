import pytest

from app.knowledge.loader import load_knowledge
from app.schemas import (
    Entry,
    Evidence,
    LayoutReport,
    RecruiterVerdict,
    Requirement,
    RequirementMatch,
    ResumeDoc,
    SubScore,
)
from app.scoring.aggregate import build_report
from app.scoring.ats import missing_keywords, score_ats
from app.scoring.match import score_match

INDIA_W = {"match": 0.40, "ats": 0.25, "quality": 0.20, "region": 0.15}
REQS = [
    Requirement(id="r1", text="Python", type="hard_skill", importance="must"),
    Requirement(id="r2", text="Kubernetes", type="tool", importance="should"),
    Requirement(id="r3", text="Kafka", type="tool", importance="nice"),
]


def ev(*statuses):
    return Evidence(
        matches=[RequirementMatch(requirement_id=f"r{i + 1}", status=s, rationale="") for i, s in enumerate(statuses)],
        gaps=[],
        recruiter=RecruiterVerdict(decision="maybe", first_impression="", reasons=[]),
    )


def test_match_formula(jd_factory):
    sub, ko = score_match(jd_factory(requirements=REQS), ev("strong", "partial", "missing"), years=6)
    assert sub.score == 70 and ko == []  # (3*1 + 2*0.6 + 0) / 6


def test_match_years_factor(jd_factory):
    sub, _ = score_match(jd_factory(requirements=REQS, min_years=5), ev("strong", "partial", "missing"), years=3)
    assert sub.score == 59  # 70 * 0.84 = 58.8
    assert any(e.signal == "years_gap" for e in sub.explanations)


def test_missing_must_is_knockout(jd_factory):
    assert score_match(jd_factory(requirements=REQS), ev("missing", "strong", "strong"), 6)[1] == ["Python"]


def test_unassessed_requirement_counts_as_missing(jd_factory):
    sub, ko = score_match(jd_factory(requirements=REQS), ev("strong"), 6)
    assert sub.score == 50 and ko == []


def test_match_no_requirements(jd_factory):
    sub, ko = score_match(jd_factory(requirements=[]), ev(), 2)
    assert sub.score == 0 and sub.explanations[0].signal == "no_requirements" and ko == []


TEXT = "Arjun Mehta arjun@example.com +91 98765 43210\nSKILLS\nPython, Kafka\nEXPERIENCE\nBuilt Python services on Kubernetes"
CLEAN = LayoutReport(file_type="pdf", pages=1, char_count=len(TEXT), word_count=400)


@pytest.fixture
def kb():
    return load_knowledge()


@pytest.fixture
def doc(sample_doc):
    return sample_doc.model_copy(
        update={
            "experience": [
                Entry(
                    title="SE",
                    organization="X",
                    start="Jan 2022",
                    end="Present",
                    bullets=[{"text": "Built Python services on Kubernetes"}],
                )
            ]
        }
    )


@pytest.fixture
def full_doc(doc):
    """The same resume with enough neutral content (coursework) to clear the 200-word ATS minimum."""
    filler = "Studied algorithms, operating systems and computer networks with distinction. " * 20
    edu = Entry(title="B.Tech, Computer Science", organization="NIT Trichy", end="2020", bullets=[{"text": filler}])
    return doc.model_copy(update={"education": [edu]})


def test_ats_clean_resume_full_marks(full_doc, jd_factory, kb):
    jd = jd_factory(ats_keywords=["Python", "Kubernetes"])
    assert score_ats(TEXT, CLEAN, full_doc, jd, kb.regions["india"], kb).score == 100


def test_ats_layout_penalties(full_doc, jd_factory, kb):
    jd = jd_factory(ats_keywords=["Python", "Kubernetes"])
    worse = CLEAN.model_copy(update={"multi_column": True, "hidden_chars": 40})
    assert score_ats(TEXT, worse, full_doc, jd, kb.regions["india"], kb).score == 80


def test_ats_keyword_weighting(full_doc, jd_factory, kb):
    jd = jd_factory(ats_keywords=["Python", "Kafka", "Terraform", "k8s"])  # bullet, skills-only, missing, synonym
    sub = score_ats(TEXT, CLEAN, full_doc, jd, kb.regions["india"], kb)
    assert sub.score == 89  # 30 + 35*(1+0.7+0+1)/4 + 20 + 15 = 88.625
    assert missing_keywords(TEXT, jd, kb) == ["Terraform"]


def test_ats_missing_contact_and_too_long(doc, jd_factory, kb):
    layout = CLEAN.model_copy(update={"pages": 3})
    sub = score_ats("no contact here " * 50, layout, doc, jd_factory(ats_keywords=[]), kb.regions["india"], kb)
    signals = {e.signal for e in sub.explanations}
    assert {"no_email", "no_phone", "too_long"} <= signals


def test_ats_fresher_projects_only(sample_doc, jd_factory, kb):
    fresher = ResumeDoc(contact=sample_doc.contact, projects=sample_doc.projects, education=sample_doc.education)
    sub = score_ats(TEXT, CLEAN, fresher, jd_factory(ats_keywords=["Python"]), kb.regions["india"], kb)
    assert 0 < sub.score < 100 and "no_skills" in {e.signal for e in sub.explanations}


def test_build_report_half_up():
    subs = [SubScore(key=k, score=s) for k, s in (("match", 70), ("ats", 80), ("quality", 60), ("region", 90))]
    assert build_report(subs, INDIA_W, []).overall == 74  # 73.5 → 74


def _signals(doc, layout, jd_factory, kb):
    jd = jd_factory(ats_keywords=["Python", "Kubernetes"])
    return {e.signal for e in score_ats(TEXT, layout, doc, jd, kb.regions["india"], kb).explanations}


def test_thinness_counts_content_not_filler(doc, jd_factory, kb):
    from app.schemas import Bullet, OtherSection

    padded = doc.model_copy(deep=True)
    padded.other_sections = [OtherSection(name="Declaration", bullets=[Bullet(text="I hereby declare " * 40)])]
    # the page has 400 words, but they are a declaration: still too thin for ATS matching
    assert "too_thin" in _signals(padded, CLEAN, jd_factory, kb)


def test_thinness_ignores_page_word_count_when_content_is_enough(doc, jd_factory, kb):
    from app.schemas import Bullet, Entry

    full = doc.model_copy(deep=True)
    full.projects.append(
        Entry(
            title="Ledger API",
            organization="Personal",
            bullets=[Bullet(text="Built a ledger reconciliation service in Python " * 6) for _ in range(5)],
        )
    )
    sparse_page = CLEAN.model_copy(update={"word_count": 120})  # a generated resume's own count can be low
    assert "too_thin" not in _signals(full, sparse_page, jd_factory, kb)
