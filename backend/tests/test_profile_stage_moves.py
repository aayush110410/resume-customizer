from datetime import date

import pytest

from app.knowledge.loader import load_knowledge
from app.profile.employers import classify, employer_kind, field_of, jd_employer_kind
from app.profile.moves import detect_moves
from app.profile.stage import detect_stage
from app.profile.timeline import build_stints
from app.resume_ops import assign_ids
from app.schemas import Bullet, Contact, Entry, JDAnalysis, ResumeDoc

TODAY = date(2026, 10, 14)


@pytest.fixture
def kb():
    return load_knowledge()


def doc(experience=(), education=()) -> ResumeDoc:
    return assign_ids(
        ResumeDoc(
            contact=Contact(name="Test"),
            experience=[
                Entry(title=t, organization=o, start=s, end=e, bullets=[Bullet(text=b) for b in bl])
                for t, o, s, e, *rest in experience
                for bl in [rest[0] if rest else []]
            ],
            education=[Entry(title=t, organization="Uni", end=e) for t, e in education],
        )
    )


def jd(company=None, employer_type="product_startup", family="software_engineering") -> JDAnalysis:
    return JDAnalysis(
        is_job_description=True,
        title="Engineer",
        company=company,
        role_family=family,
        employer_type=employer_type,
        seniority="junior",
        suggested_region="india",
        requirements=[],
        ats_keywords=[],
    )


def stage_of(kb, resume):
    return detect_stage(resume, build_stints(resume, kb, kb.regions["india"].story, TODAY), TODAY)


@pytest.mark.parametrize(
    ("degree", "end", "expected"),
    [
        ("B.Tech, Computer Science", "May 2027", ("student", 4, 2027)),
        ("B.Tech, Computer Science", "May 2028", ("student", 3, 2028)),
        ("B.E. Mechanical", "May 2029", ("student", 2, 2029)),
        ("BCA", "May 2028", ("student", 2, 2028)),
        ("MBA", "2027", ("student", 2, 2027)),
    ],
)
def test_student_year(kb, degree, end, expected):
    assert stage_of(kb, doc(education=[(degree, end)])) == expected


def test_stage_by_full_time_years(kb):
    grad = [("B.Tech", "May 2026")]
    interns_only = doc([("SDE Intern", "A", "Jan 2026", "Jun 2026")], grad)
    assert stage_of(kb, interns_only)[0] == "fresh_grad"
    nats = doc([("Apprentice (NATS)", "BHEL", "Jul 2025", "Jun 2026")], [("B.Tech", "May 2025")])
    assert stage_of(kb, nats)[0] == "fresh_grad"
    assert stage_of(kb, doc([("Engineer", "A", "Oct 2024", "Present")], grad))[0] == "early"
    assert stage_of(kb, doc([("Engineer", "A", "Oct 2021", "Present")], grad))[0] == "mid"
    assert stage_of(kb, doc([("Engineer", "A", "Oct 2017", "Present")], grad))[0] == "senior"


def test_employer_kind(kb):
    assert employer_kind("Infosys Ltd", "", kb) == "it_services"
    assert employer_kind("L&T Infotech", "", kb) == "it_services"
    assert employer_kind("Acme Labs", "Joined as the 4th engineer at a seed-stage startup", kb) == "startup"
    assert employer_kind("Acme Labs", "", kb) == "unknown"
    assert field_of("Business Development Executive", kb) == "sales_bd"
    assert field_of("Data Engineer", kb) == "data_ml"
    assert jd_employer_kind(jd(company="Google"), kb) == "mega_mnc"
    assert jd_employer_kind(jd(employer_type="gcc"), kb) == "mnc"


def targets(kb, experience, the_jd):
    resume = doc(experience)
    stints = classify(build_stints(resume, kb, kb.regions["india"].story, TODAY), resume, kb)
    return [m.kind for m in detect_moves(stints, the_jd, kb) if m.target]


def test_target_moves(kb):
    tcs = [("Systems Engineer", "TCS", "Jul 2022", "Present")]
    assert targets(kb, tcs, jd()) == ["services_to_product"]
    ibm = [("Software Engineer", "IBM", "Jul 2022", "Present")]
    assert targets(kb, ibm, jd(company="Google", employer_type="product_startup")) == ["mnc_to_mega"]
    razorpay = [("Software Engineer", "Razorpay", "Jul 2022", "Present")]
    assert "mnc_to_mega" not in targets(kb, razorpay, jd(company="Google"))
    startup = [("Engineer", "Acme Labs", "Jul 2022", "Present", ["Founding engineer at a seed-stage startup"])]
    assert targets(kb, startup, jd(employer_type="gcc")) == ["startup_to_mnc"]
    sales = [("Business Development Executive", "Infosys", "Jul 2022", "Present")]
    assert "field_switch" in targets(kb, sales, jd(employer_type="it_services"))
    assert targets(kb, tcs, jd(employer_type="it_services")) == []


def test_past_moves_are_not_targets(kb):
    history = [("Engineer", "TCS", "Jul 2019", "Jun 2022"), ("Engineer", "Razorpay", "Jul 2022", "Present")]
    resume = doc(history)
    stints = classify(build_stints(resume, kb, kb.regions["india"].story, TODAY), resume, kb)
    moves = detect_moves(stints, jd(employer_type="product_startup"), kb)
    assert [(m.kind, m.target) for m in moves] == [("services_to_product", False)]


def test_student_freelancing_during_degree_stays_student(kb):
    resume = doc([("Freelance Developer", "Self", "2024", "Present")], [("B.Tech, Computer Science", "May 2027")])
    assert stage_of(kb, resume) == ("student", 4, 2027)


def test_year_only_start_counts_conservatively(kb):
    resume = doc([("Engineer", "Acme", "2023", "Present")], [("B.Tech", "2023")])
    assert stage_of(kb, resume)[0] == "early"  # Dec 2023 → Oct 2026 at least, not Jan 2023


def test_job_before_a_part_time_degree_is_not_a_student(kb):
    resume = doc([("Engineer", "Acme", "Jan 2018", "Present")], [("MBA (part-time)", "May 2027")])
    assert stage_of(kb, resume)[0] == "senior"
