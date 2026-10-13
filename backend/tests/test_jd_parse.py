from pathlib import Path

from app.jd_parse import ats_keywords_from, parse_requirements
from app.knowledge.loader import load_knowledge

JD = (Path(__file__).parent.parent / "evals/golden/jd_sde2_bengaluru.txt").read_text()


def test_bullets_become_requirements_with_importance_from_their_heading():
    reqs = parse_requirements(JD, load_knowledge())
    by_imp = {imp: [t for t, i, _ in reqs if i == imp] for imp in ("must", "should", "nice")}
    assert by_imp["must"][0] == "3+ years of backend development experience."
    assert "Strong in Java (Spring Boot) or Python (Django/FastAPI)." in by_imp["must"]
    assert "Experience with Docker" in by_imp["must"] and "Experience with Kubernetes" in by_imp["must"]  # split
    assert len(by_imp["should"]) == 6 and by_imp["should"][0].startswith(
        "Design, build and own"
    )  # ";" splits one duty in two
    assert by_imp["nice"] == [
        "Payments or banking domain experience.",
        "AWS certification.",
        "Experience with Redis",
        "Experience with observability tools (Prometheus, Grafana)",
    ]
    assert not any("fintech product company" in t for t, _, _ in reqs)  # "About us" is not a requirement


def test_types_are_decided_in_code():
    types = {t: ty for t, _, ty in parse_requirements(JD, load_knowledge())}
    assert types["3+ years of backend development experience."] == "experience"
    assert types["AWS certification."] == "certification"
    assert types["Mentor junior engineers and review code."] == "soft_skill"


def test_unstructured_jd_falls_back_to_the_model():
    prose = "We are hiring a backend engineer. " * 20
    assert parse_requirements(prose, load_knowledge()) is None


def test_parsing_is_deterministic_and_ats_keywords_follow_the_jd():
    kb = load_knowledge()
    assert parse_requirements(JD, kb) == parse_requirements(JD, kb)
    kws = ats_keywords_from(JD, kb)
    assert kws[:3] == ["Python", "Java", "microservices"] and "Kafka" in kws and "Grafana" in kws
