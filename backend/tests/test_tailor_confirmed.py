from datetime import date

from app.guard.grounding import find_fabrications
from app.knowledge.loader import load_knowledge
from app.profile import build_profile
from app.profile.story import score_story
from app.profile.timeline import build_stints
from app.resume_ops import assign_ids, render_plain
from app.schemas import (
    Answer,
    Bullet,
    Contact,
    CustomName,
    Entry,
    Evidence,
    JDAnalysis,
    ProjectFacts,
    RecruiterVerdict,
    ResumeDoc,
)
from app.tailoring import apply_confirmed, confirmed_facts

TODAY = date(2026, 10, 14)
KB = load_knowledge()
JD = JDAnalysis(
    is_job_description=True,
    title="Backend Engineer",
    role_family="software_engineering",
    employer_type="product_startup",
    seniority="junior",
    suggested_region="india",
    requirements=[],
    ats_keywords=[],
)
EV = Evidence(matches=[], gaps=[], recruiter=RecruiterVerdict(decision="maybe", first_impression="", reasons=[]))


def _resume() -> ResumeDoc:
    return assign_ids(
        ResumeDoc(
            contact=Contact(name="T"),
            experience=[
                Entry(title="Software Engineer", organization="Razorpay", start="Jan 2024", end="Present"),
                Entry(title="Software Engineer", organization="Foo Systems", start="Mar 2022", end="Jul 2022"),
            ],
            projects=[Entry(title="Zephyr", organization="Personal", bullets=[Bullet(text="Built Zephyr for orders")])],
            education=[Entry(title="B.Tech", organization="VIT", start="Jul 2018", end="Feb 2022")],
        )
    )


FACTS = [ProjectFacts(project_id="prj0", purpose="Built Zephyr for orders", custom_names=[CustomName(name="Zephyr")])]
ANSWERS = {
    "stint:exp1": Answer(value="contract"),
    "gap:2022-08": Answer(value="exam_prep", state_on_resume=True),
    "name:zephyr": Answer(value="own", text="event store on Kafka"),
}


def _profile(resume=None):
    # a tailored resume relabels the contract stint, so its question is gone: answers apply non-strictly
    return build_profile(resume or _resume(), JD, EV, FACTS, "india", KB, TODAY, answers=ANSWERS, strict=resume is None)


def test_contract_label_and_career_break_in_code():
    doc = apply_confirmed(apply_confirmed(_resume(), _profile()), _profile())
    titles = [e.title for e in doc.experience]
    assert titles == ["Software Engineer", "Career break: exam preparation", "Software Engineer (Contract)"]
    brk = doc.experience[1]
    assert (brk.start, brk.end) == ("Aug 2022", "Dec 2023")


def test_career_break_entries_are_not_stints():
    doc = apply_confirmed(_resume(), _profile())
    stints = build_stints(doc, KB, KB.regions["india"].story, TODAY)
    assert all(not s.title.startswith("Career break") for s in stints)


def test_confirmed_block_and_guard_allowance():
    block, _ = confirmed_facts(_profile())
    assert "Zephyr: my own event store on Kafka" in block
    original = _resume()
    tailored = original.model_copy(deep=True)
    tailored.projects[0].bullets[0].text = "Built Zephyr, my own event store on Kafka"
    text = render_plain(original)
    assert find_fabrications(original, text, tailored, KB)  # Kafka is not in the resume
    assert not find_fabrications(original, text + "\n" + block, tailored, KB)


def test_tailored_story_recovers_points():
    before = score_story(_profile(), _resume(), JD, EV, "india", KB).score
    tailored = apply_confirmed(_resume(), _profile())
    after = score_story(_profile(tailored), tailored, JD, EV, "india", KB).score
    assert after > before


def test_no_answers_means_none_block():
    p = build_profile(_resume(), JD, EV, FACTS, "india", KB, TODAY)
    assert confirmed_facts(p) == ("(none)", set())
