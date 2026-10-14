"""The three extraction/judgment LLM steps, each followed by deterministic clean-up and verification."""

import asyncio
import json
from datetime import date

from app.guard.grounding import verify_evidence, verify_quote
from app.jd_parse import ats_keywords_from, named_skills, parse_requirements
from app.judging import (
    code_judgment,
    is_factual,
    level_for_years,
    merge_passes,
    reconcile,
    required_years,
    years_of_experience,
)
from app.knowledge.loader import build_context_brief, select_tips
from app.knowledge.models import Knowledge, RegionPack
from app.llm.client import LLM, LLMUnavailable, Structured
from app.llm.prompting import render, wrap
from app.profile.projects import rule_facts
from app.resume_ops import assign_ids, render_for_matching, render_plain
from app.schemas import (
    CustomName,
    Evidence,
    JDAnalysis,
    ProjectFacts,
    ProjectFactsBatch,
    Requirement,
    RequirementMatch,
    ResumeDoc,
)
from app.text_utils import contains_term, normalize

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
    parsed = parse_requirements(jd_text, kb)
    if parsed:
        # The JD's own bullets, in order, with importance from their heading: same JD → same requirements.
        order = {"must": 0, "should": 1, "nice": 2}
        ranked = sorted(parsed, key=lambda p: order[p[1]])[:MAX_REQUIREMENTS]
        jd.requirements = [
            Requirement(id=f"r{i}", text=t, type=ty, importance=imp, keywords=named_skills(t, kb))
            for i, (t, imp, ty) in enumerate(ranked, 1)
        ]
        jd.min_years = next((required_years(q.text) for q in jd.requirements if q.type == "experience"), jd.min_years)
        code_keywords = ats_keywords_from(jd_text, kb)
        if len(code_keywords) >= 3:
            jd.ats_keywords = code_keywords[:MAX_ATS_KEYWORDS]
    else:
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
    llm: LLM, resume: ResumeDoc, resume_text: str, jd: JDAnalysis, region: RegionPack, kb: Knowledge, passes: int = 2
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
    source = resume_text + "\n" + render_plain(resume)

    async def one_pass(temperature: float) -> Structured[Evidence]:
        r = await llm.structured(
            "analysis", _system(region.label), user, Evidence, temperature=temperature, reasoning_effort="medium"
        )
        ev = r.value.model_copy(deep=True)
        by_id: dict[str, RequirementMatch] = {}
        for m in ev.matches:
            by_id.setdefault(m.requirement_id, m)
        ev.matches = [
            by_id.get(q.id)
            or RequirementMatch(requirement_id=q.id, status="missing", rationale="Not assessed by model")
            for q in jd.requirements
        ]
        return Structured(verify_evidence(ev, resume, source), r.model)

    # Independent passes run in parallel (no added wait); verified evidence found by either one counts.
    results = await asyncio.gather(*(one_pass(0.0 if i == 0 else 0.3) for i in range(passes)), return_exceptions=True)
    done = [x for x in results if isinstance(x, Structured)]
    if not done:
        failure = results[0]
        raise failure if isinstance(failure, Exception) else LLMUnavailable([])
    r = done[0]
    ev = r.value
    for extra in done[1:]:
        ev = merge_passes(ev, extra.value)
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


async def read_projects(llm: LLM, resume: ResumeDoc, resume_text: str, kb: Knowledge) -> Structured[list[ProjectFacts]]:
    """Quoted facts per project; anything whose quote does not verify is dropped, missing projects use rules."""
    if not resume.projects:
        return Structured([], "none")
    user = render(
        "read_projects",
        tutorial_list=", ".join(kb.tutorial_projects),
        resume_block=wrap("resume", render_for_matching(resume)),
    )
    r = await llm.structured(
        "analysis", _system("India and international markets"), user, ProjectFactsBatch, reasoning_effort="low"
    )
    source = resume_text + "\n" + render_plain(resume)
    norm = normalize(source)

    def quoted(value: str | None) -> str | None:
        return value if value and verify_quote(value, source) else None

    got = {f.project_id: f for f in r.value.projects}
    out = []
    for entry in resume.projects:
        f = got.get(entry.id)
        if f is None:
            out.append(rule_facts(entry, kb))
            continue
        names = []
        for c in f.custom_names:
            if not contains_term(source, c.name) or kb.synonyms.groups.get(normalize(c.name)):
                continue
            ok = quoted(c.quote)
            names.append(CustomName(name=c.name, what=c.what if ok else None, quote=ok))
        out.append(
            ProjectFacts(
                project_id=entry.id,
                purpose=quoted(f.purpose),
                users=quoted(f.users),
                scale=quoted(f.scale),
                links=[link for link in f.links if normalize(link) in norm],
                tutorial_pattern=f.tutorial_pattern if f.tutorial_pattern in kb.tutorial_projects else None,
                extension=quoted(f.extension),
                custom_names=names,
            )
        )
    return Structured(out, r.model)
