"""Career profile: who the candidate is (stage), what their history looks like (stints, gaps, moves) and how
real their projects are. Built in code from the structured resume, the JD, evidence and quoted project facts."""

from datetime import date

from app.knowledge.models import Knowledge
from app.profile.clarify import apply_answers, make_questions
from app.profile.employers import classify
from app.profile.moves import detect_moves
from app.profile.projects import rule_facts, score_project
from app.profile.stage import detect_stage
from app.profile.timeline import build_stints, find_gaps, month_key
from app.schemas import Answer, Evidence, JDAnalysis, Profile, ProjectFacts, Region, ResumeDoc


def build_profile(
    resume: ResumeDoc,
    jd: JDAnalysis,
    ev: Evidence,
    facts: list[ProjectFacts],
    region_key: Region,
    kb: Knowledge,
    today: date,
    answers: dict[str, Answer] | None = None,
    rules_only: bool = False,
) -> Profile:
    answers = answers or {}
    rules = kb.regions[region_key].story
    stints = classify(build_stints(resume, kb, rules, today), resume, kb)
    stage, study_year, grad_year = detect_stage(resume, stints, today)
    by_id = {f.project_id: f for f in facts}
    projects = [score_project(e, by_id.get(e.id) or rule_facts(e, kb), kb, set()) for e in resume.projects]
    base = Profile(
        stage=stage,
        study_year=study_year,
        grad_year=grad_year,
        stints=stints,
        gaps=find_gaps(resume, stints, rules, today),
        moves=detect_moves(stints, jd, kb),
        projects=projects,
        rules_only=rules_only,
        as_of=month_key(today),
    )
    profile = apply_answers(base, answers, resume, jd, kb)
    profile.questions = make_questions(base, answers, resume, jd, ev, region_key, kb)
    return profile
