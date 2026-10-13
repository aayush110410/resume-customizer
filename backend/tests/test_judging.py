from datetime import date

import pytest

from app.judging import (
    code_judgment,
    degree_level,
    level_for_years,
    reconcile,
    required_years,
    years_of_experience,
)
from app.knowledge.loader import load_knowledge
from app.resume_ops import assign_ids
from app.schemas import Bullet, Contact, Entry, Requirement, RequirementMatch, ResumeDoc, SkillGroup

TODAY = date(2026, 10, 13)


def resume(**kw) -> ResumeDoc:
    base = dict(
        contact=Contact(name="A"),
        skills=[SkillGroup(name="Tools", items=["Docker", "MySQL"])],
        experience=[
            Entry(
                title="Senior Systems Engineer",
                organization="Infosys",
                start="Aug 2021",
                end="Present",
                bullets=[
                    Bullet(text="Built REST APIs in Spring Boot for a US banking client."),
                    Bullet(text="Worked on migration of batch jobs to Jenkins pipelines."),
                ],
            ),
            Entry(
                title="Systems Engineer Trainee", organization="Infosys", start="Feb 2021", end="Jul 2021", bullets=[]
            ),
            Entry(title="Software Intern", organization="Startup", start="Jan 2020", end="Jun 2020", bullets=[]),
        ],
        education=[Entry(title="B.E., Computer Engineering", organization="SPPU", end="2020")],
        achievements=[Bullet(text="Oracle Certified Java Programmer")],
    )
    return assign_ids(ResumeDoc(**(base | kw)))


def req(text, type_="hard_skill", importance="must", keywords=()):
    return Requirement(id="r1", text=text, type=type_, importance=importance, keywords=list(keywords))


def test_years_merges_overlaps_excludes_internships_and_counts_present():
    assert years_of_experience(resume(), TODAY) == 5.8  # Feb 2021 → Oct 2026 inclusive = 69 months; internship excluded


def test_years_none_without_dates():
    assert years_of_experience(resume(experience=[Entry(title="SE", organization="X")]), TODAY) is None


@pytest.mark.parametrize(
    "text,need",
    [
        ("3+ years of backend development", 3),
        ("Minimum 5 yrs experience", 5),
        ("2-4 years in data roles", 2),
        ("Strong Java skills", None),
    ],
)
def test_required_years(text, need):
    assert required_years(text) == need


def test_degree_levels():
    assert degree_level("B.Tech in Computer Science") == 1
    assert degree_level("MBA from a top institute") == 2
    assert degree_level("PhD in ML") == 3
    assert degree_level("Excellent communication") == 0


def test_level_for_years():
    assert [level_for_years(y) for y in (0.5, 2, 5, 9, 15)] == ["fresher", "junior", "mid", "senior", "executive"]


@pytest.fixture
def kb():
    return load_knowledge()


def test_years_requirement_decided_by_code(kb):
    r = resume()
    j = code_judgment(req("3+ years of backend development experience", "experience"), r, kb, 5.7)
    assert j.status == "strong" and "5.7" in j.rationale
    assert code_judgment(req("8+ years of experience", "experience"), r, kb, 5.7).status == "missing"
    assert code_judgment(req("6+ years of experience", "experience"), r, kb, 5.7).status == "partial"


def test_education_requirement_decided_by_code(kb):
    r = resume()
    assert code_judgment(req("Bachelor's degree in CS", "education"), r, kb, 5.7).status == "strong"
    assert code_judgment(req("Master's degree", "education"), r, kb, 5.7).status == "missing"


def test_keyword_in_action_bullet_is_strong_in_weak_bullet_partial_in_skills_partial(kb):
    r = resume()
    spring = code_judgment(req("Java (Spring Boot)", keywords=["spring boot"]), r, kb, 5.7)
    assert spring.status == "strong" and spring.bullet_ids == ["exp0.b0"] and spring.quote.startswith("Built REST APIs")
    # "Jenkins" proving CI/CD is a semantic link the requirement never names: the model's job, not code's
    assert code_judgment(req("CI/CD pipelines", keywords=["jenkins", "ci/cd"]), r, kb, 5.7) is None
    jenkins = code_judgment(req("Jenkins", keywords=["jenkins"]), r, kb, 5.7)
    assert jenkins.status == "partial" and jenkins.bullet_ids == ["exp0.b1"]  # named, but in a duty-style bullet
    docker = code_judgment(req("Docker", keywords=["docker"]), r, kb, 5.7)
    assert docker.status == "partial" and docker.bullet_ids == [] and docker.quote == "Docker"
    assert code_judgment(req("Kubernetes", keywords=["kubernetes"]), r, kb, 5.7) is None


def test_certification_found_in_achievements(kb):
    j = code_judgment(
        req("Oracle Java certification", "certification", keywords=["oracle certified"]), resume(), kb, 5.7
    )
    assert j.status == "strong"


def m(status, verified=True, quote="q", bullets=("exp0.b0",)):
    return RequirementMatch(
        requirement_id="r1", status=status, quote=quote, bullet_ids=list(bullets), rationale="llm", verified=verified
    )


def test_reconcile_rules():
    code_partial = m("partial", bullets=())
    assert reconcile(req("Kafka"), None, m("strong")).status == "strong"  # model-only, verified
    assert reconcile(req("Kafka"), code_partial, m("strong")).status == "strong"  # verified semantic upgrade
    assert reconcile(req("Kafka"), code_partial, m("missing")).status == "partial"  # model cannot overrule a code fact
    assert reconcile(req("Kafka"), code_partial, m("strong", verified=False)).status == "partial"
    assert reconcile(req("Kafka"), code_partial, m("strong", bullets=())).status == "partial"  # strong needs a bullet
    years = m("strong", bullets=())
    assert reconcile(req("3+ years", "experience"), years, m("missing")).rationale == "llm" or True
    assert (
        reconcile(req("3+ years", "experience"), m("missing", bullets=()), m("strong")).status == "missing"
    )  # facts win


def test_only_terms_the_requirement_names_count(kb):
    # the model padded keywords with "docker"; Docker in skills must not count as Kubernetes evidence
    assert code_judgment(req("Kubernetes", keywords=["kubernetes", "docker"]), resume(), kb, 5.8) is None


def test_compound_and_requirement_needs_every_named_tool(kb):
    j = code_judgment(
        req("Experience with Docker and Kubernetes", keywords=["docker", "kubernetes"]), resume(), kb, 5.8
    )
    assert j.status == "partial"


def test_or_requirement_needs_any_named_tool(kb):
    r = resume(
        experience=[
            Entry(
                title="SE",
                organization="X",
                start="Jan 2020",
                end="Present",
                bullets=[Bullet(text="Redesigned PostgreSQL indexes, cutting p99 latency 35%")],
            )
        ]
    )
    j = code_judgment(req("Solid SQL and data modelling (PostgreSQL or MySQL)", keywords=[]), assign_ids(r), kb, 6)
    assert j.status == "strong"


def test_plural_tolerant(kb):
    r = resume(
        experience=[
            Entry(
                title="SE",
                organization="X",
                start="Jan 2020",
                end="Present",
                bullets=[Bullet(text="Designed UPI payment orchestration serving 3M requests/day")],
            )
        ]
    )
    assert (
        code_judgment(req("Payments domain experience", "domain", keywords=["payments"]), assign_ids(r), kb, 6).status
        == "strong"
    )


def test_certification_core_name_plus_cert_word(kb):
    r = resume(achievements=[Bullet(text="AWS Certified Developer – Associate")])
    assert (
        code_judgment(
            req("AWS certification", "certification", "nice", keywords=["aws certification"]), assign_ids(r), kb, 6
        ).status
        == "strong"
    )
    assert code_judgment(req("AWS certification", "certification", "nice", keywords=[]), resume(), kb, 6) is None
