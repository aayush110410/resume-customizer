"""Persona golden set: one resume per career situation, with the stage, flags, target move and Story band the
rubric should produce. Fix the profile code rather than loosening the expectations."""

from datetime import date
from pathlib import Path

import pytest
import yaml

from app.knowledge.loader import load_knowledge
from app.profile import build_profile
from app.profile.story import score_story
from app.resume_ops import assign_ids
from app.schemas import (
    Answer,
    Evidence,
    JDAnalysis,
    ProjectFacts,
    RecruiterVerdict,
    Requirement,
    RequirementMatch,
    ResumeDoc,
)

TODAY = date(2026, 10, 14)
KB = load_knowledge()
RAW = yaml.safe_load((Path(__file__).parent / "personas.yaml").read_text(encoding="utf-8"))
BY_ID = {p["id"]: p for p in RAW}
KEYWORDS = ["python", "sql", "javascript", "docker"]


def _persona(p: dict) -> dict:
    return {**BY_ID[p["same_as"]], **{k: v for k, v in p.items() if k != "same_as"}} if "same_as" in p else p


def _resume(raw: dict) -> ResumeDoc:
    raw = {**raw}
    for section in ("experience", "projects", "education"):
        raw[section] = [{**e, "bullets": [{"text": b} for b in e.get("bullets", [])]} for e in raw.get(section, [])]
    return assign_ids(ResumeDoc.model_validate(raw))


def _jd(overrides: dict) -> JDAnalysis:
    reqs = [
        Requirement(id=f"r{i}", text=k, type="hard_skill", importance="must", keywords=[k])
        for i, k in enumerate(KEYWORDS)
    ]
    base = dict(
        is_job_description=True,
        title="Software Engineer",
        role_family="software_engineering",
        employer_type="product_startup",
        seniority="junior",
        suggested_region="india",
        requirements=reqs,
        ats_keywords=KEYWORDS,
    )
    return JDAnalysis(**{**base, **overrides})


@pytest.mark.parametrize("raw", RAW, ids=[p["id"] for p in RAW])
def test_persona(raw):
    p = _persona(raw)
    resume, jd = _resume(p["resume"]), _jd(p.get("jd", {}))
    statuses = p.get("evidence", ["partial"] * 4)
    ev = Evidence(
        matches=[RequirementMatch(requirement_id=f"r{i}", status=s, rationale="") for i, s in enumerate(statuses)],
        gaps=[],
        recruiter=RecruiterVerdict(decision="maybe", first_impression="", reasons=[]),
    )
    facts = [ProjectFacts.model_validate(f) for f in p.get("facts", [])]
    answers = {k: Answer.model_validate(v) for k, v in p.get("answers", {}).items()}
    profile = build_profile(resume, jd, ev, facts, p.get("region", "india"), KB, TODAY, answers=answers)
    story = score_story(profile, resume, jd, ev, p.get("region", "india"), KB)
    e = p["expect"]
    got = {
        "stage": profile.stage,
        "study_year": profile.study_year,
        "gaps": len(profile.gaps),
        "short_stints": sum(s.short for s in profile.stints),
        "target_moves": [m.kind for m in profile.moves if m.target],
        "tutorial_projects": [r.title for r in profile.projects if r.facts.tutorial_pattern],
    }
    assert got == {k: e[k] for k in got}
    low, high = e["story"]
    assert story is not None and low <= story.score <= high, f"story {story.score if story else None}"
