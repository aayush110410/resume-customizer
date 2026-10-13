"""The three extraction/judgment LLM steps, each followed by deterministic clean-up and verification."""

import json
from datetime import date

from app.guard.grounding import verify_evidence, verify_quote
from app.judging import code_judgment, is_factual, level_for_years, reconcile, years_of_experience
from app.knowledge.loader import build_context_brief, select_tips
from app.knowledge.models import Knowledge, RegionPack
from app.llm.client import LLM, Structured
from app.llm.prompting import render, wrap
from app.resume_ops import assign_ids, render_for_matching, render_plain
from app.schemas import Evidence, JDAnalysis, RequirementMatch, ResumeDoc

STRUCTURE_THRESHOLD = 80
MAX_REQUIREMENTS = 25
MAX_ATS_KEYWORDS = 30
_IMPORTANCE_ORDER = {"must": 0, "should": 1, "nice": 2}


def _system(region_label: str) -> str:
    return render("system_core", region_label=region_label)


async def structure_resume(llm: LLM, text: str) -> Structured[ResumeDoc]:
    user = render("structure_resume", resume_block=wrap("resume", text))
    r = await llm.structured(
        "analysis", _system("India and international markets"), user, ResumeDoc, reasoning_effort="low"
    )
    doc = r.value.model_copy(deep=True)

    def grounded(bullets):
        return [b for b in bullets if verify_quote(b.text, text, STRUCTURE_THRESHOLD)]

    for entry in doc.experience + doc.projects + doc.education:
        entry.bullets = grounded(entry.bullets)
    doc.achievements = grounded(doc.achievements)
    for other in doc.other_sections:
        other.bullets = grounded(other.bullets)
    doc = assign_ids(doc)
    years = years_of_experience(doc, date.today())
    if years is not None:  # dates on the page beat the model's arithmetic
        doc.total_years_experience = years
        doc.level = level_for_years(years)
    return Structured(doc, r.model)


async def analyze_jd(llm: LLM, jd_text: str, kb: Knowledge) -> Structured[JDAnalysis]:
    user = render("analyze_jd", jd_block=wrap("jd", jd_text), role_family_keys=", ".join(kb.role_families))
    r = await llm.structured(
        "analysis", _system("India and international markets"), user, JDAnalysis, reasoning_effort="medium"
    )
    jd = r.value.model_copy(deep=True)
    reqs = sorted(jd.requirements, key=lambda q: _IMPORTANCE_ORDER[q.importance])[:MAX_REQUIREMENTS]
    for i, req in enumerate(reqs, 1):
        req.id = f"r{i}"
    jd.requirements = reqs
    seen: dict[str, str] = {}
    for kw in jd.ats_keywords:
        seen.setdefault(kw.strip().lower(), kw.strip())
    jd.ats_keywords = [k for k in seen.values() if k][:MAX_ATS_KEYWORDS]
    if jd.role_family not in kb.role_families:
        jd.role_family = "general"
    return Structured(jd, r.model)


def _finding(req, code) -> str:
    if code is None:
        return f"{req.id}: no keyword hit in the resume. Look for the same skill in different words (step 2) or a bridge (step 4)."
    if is_factual(req):
        return f"{req.id}: DECIDED {code.status}. {code.rationale}"
    where = f"bullets {', '.join(code.bullet_ids)}" if code.bullet_ids else f'listed ("{code.quote}")'
    return f"{req.id}: {where} → at least {code.status}. Raise it only if a bullet clearly shows the work."


async def match_evidence(
    llm: LLM, resume: ResumeDoc, resume_text: str, jd: JDAnalysis, region: RegionPack, kb: Knowledge
) -> Structured[Evidence]:
    tips = select_tips(region, jd, resume.level)
    years = years_of_experience(resume, date.today())
    if years is None:
        years = resume.total_years_experience or None
    code = {q.id: code_judgment(q, resume, kb, years) for q in jd.requirements}
    user = render(
        "match_evidence",
        context_brief=build_context_brief(region, jd, resume.level, kb),
        code_findings="\n".join(_finding(q, code[q.id]) for q in jd.requirements),
        recruiter_persona=region.recruiter_persona,
        tips_json=json.dumps([{"tip_id": t.id, "tip": t.text} for t in tips], ensure_ascii=False),
        requirements_json=json.dumps(
            [{"id": q.id, "text": q.text, "type": q.type, "importance": q.importance} for q in jd.requirements],
            ensure_ascii=False,
        ),
        resume_block=wrap("resume", render_for_matching(resume)),
    )
    r = await llm.structured("analysis", _system(region.label), user, Evidence, reasoning_effort="medium")
    ev = r.value.model_copy(deep=True)

    by_id: dict[str, RequirementMatch] = {}
    for m in ev.matches:
        by_id.setdefault(m.requirement_id, m)
    ev.matches = [
        by_id.get(q.id) or RequirementMatch(requirement_id=q.id, status="missing", rationale="Not assessed by model")
        for q in jd.requirements
    ]
    source = resume_text + "\n" + render_plain(resume)
    ev = verify_evidence(ev, resume, source)
    ev.matches = [reconcile(q, code[q.id], m) for q, m in zip(jd.requirements, ev.matches, strict=True)]
    final = {m.requirement_id: m.status for m in ev.matches}
    known = {q.id for q in jd.requirements}
    ev.gaps = [
        g
        for g in ev.gaps
        if g.requirement_id is None or (g.requirement_id in known and final[g.requirement_id] != "strong")
    ]
    allowed = {t.id for t in tips}
    ev.tips = [t for t in ev.tips if t.tip_id in allowed][:5]
    return Structured(ev, r.model)
