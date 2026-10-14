import asyncio
from collections.abc import AsyncIterator
from datetime import date

from app.cache import AsyncLRU, cache_key
from app.knowledge.models import Knowledge
from app.llm.client import LLM, Structured
from app.llm.prompting import PROMPT_VERSION
from app.llm.tasks import analyze_jd, match_evidence, read_projects, structure_resume
from app.profile import build_profile
from app.schemas import Analysis, ParsedResume, Region
from app.scoring import score_all
from app.scoring.ats import missing_keywords
from app.scoring.insights import build_insights
from app.services import ServerEvent, stage


async def analyze_stream(
    parsed: ParsedResume, jd_text: str, region: Region, llm: LLM, kb: Knowledge, cache: AsyncLRU
) -> AsyncIterator[ServerEvent]:
    pack = kb.regions[region]
    yield stage("parsing", "done")
    yield stage("understanding", "active")
    resume_r, jd_r = await asyncio.gather(
        cache.get_or_compute(
            cache_key(PROMPT_VERSION, "resume", parsed.text), lambda: structure_resume(llm, parsed.text)
        ),
        cache.get_or_compute(cache_key(PROMPT_VERSION, "jd", jd_text), lambda: analyze_jd(llm, jd_text, kb)),
    )
    resume, jd = resume_r.value, jd_r.value
    yield ServerEvent("resume", resume.model_dump())
    yield ServerEvent("jd", jd.model_dump())
    if not jd.is_job_description:
        yield ServerEvent("warning", {"code": "NOT_A_JD", "message": "This doesn't look like a job description."})
    yield stage("understanding", "done")

    yield stage("matching", "active")
    # Project reading runs alongside matching; if it fails, projects are judged by rules alone.
    ev_r, proj_r = await asyncio.gather(
        match_evidence(llm, resume, parsed.text, jd, pack, kb),
        cache.get_or_compute(
            cache_key(PROMPT_VERSION, "projects", parsed.text), lambda: read_projects(llm, resume, parsed.text, kb)
        ),
        return_exceptions=True,
    )
    if isinstance(ev_r, BaseException):
        raise ev_r
    facts, rules_only = (proj_r.value, False) if isinstance(proj_r, Structured) else ([], True)
    yield ServerEvent("evidence", ev_r.value.model_dump())
    yield stage("matching", "done")

    yield stage("scoring", "active")
    profile = build_profile(resume, jd, ev_r.value, facts, region, kb, date.today(), rules_only=rules_only)
    yield ServerEvent("profile", profile.model_dump())
    report = score_all(parsed.text, parsed.layout, resume, jd, ev_r.value, region, kb, profile)
    insights = build_insights(report, jd, ev_r.value, pack, missing_keywords(parsed.text, jd, kb), resume.level)
    yield ServerEvent("scores", report.model_dump())
    yield ServerEvent("insights", insights.model_dump())
    yield stage("scoring", "done")

    analysis = Analysis(
        region=region,
        resume=resume,
        resume_text=parsed.text,
        layout=parsed.layout,
        jd=jd,
        evidence=ev_r.value,
        scores=report,
        insights=insights,
        prompt_version=PROMPT_VERSION,
        models={
            "resume": resume_r.model,
            "jd": jd_r.model,
            "match": ev_r.model,
            "projects": proj_r.model if isinstance(proj_r, Structured) else "rules",
        },
        profile=profile,
        jd_text=jd_text,
    )
    yield ServerEvent("done", {"analysis": analysis.model_dump()})
