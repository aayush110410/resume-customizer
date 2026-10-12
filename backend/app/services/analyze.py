import asyncio
from collections.abc import AsyncIterator

from app.cache import AsyncLRU, cache_key
from app.knowledge.models import Knowledge
from app.llm.client import LLM
from app.llm.prompting import PROMPT_VERSION
from app.llm.tasks import analyze_jd, match_evidence, structure_resume
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
    ev_r = await match_evidence(llm, resume, parsed.text, jd, pack, kb)
    yield ServerEvent("evidence", ev_r.value.model_dump())
    yield stage("matching", "done")

    yield stage("scoring", "active")
    report = score_all(parsed.text, parsed.layout, resume, jd, ev_r.value, region, kb)
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
        models={"resume": resume_r.model, "jd": jd_r.model, "match": ev_r.model},
    )
    yield ServerEvent("done", {"analysis": analysis.model_dump()})
