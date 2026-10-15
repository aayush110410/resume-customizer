import json
from collections.abc import AsyncIterator
from datetime import date

from app.knowledge.loader import build_context_brief
from app.knowledge.models import Knowledge
from app.letter import assemble, clean_paragraph, letter_text
from app.llm.client import LLM
from app.llm.prompting import render, wrap
from app.resume_ops import render_contact, render_plain
from app.schemas import CoverLetterRequest, LetterBody
from app.services import ServerEvent, stage
from app.services.tailor import TONE_RULES
from app.tailoring import confirmed_facts

LETTER_TEMPERATURE = 0.5
WORD_BUDGET = {"india": "180–250", "international": "250–350"}


async def cover_letter_stream(req: CoverLetterRequest, llm: LLM, kb: Knowledge) -> AsyncIterator[ServerEvent]:
    a = req.analysis
    pack = kb.regions[a.region]
    reqs = {q.id: q for q in a.jd.requirements}
    proof = [
        {"requirement": reqs[m.requirement_id].text, "evidence": m.quote}
        for m in a.evidence.matches
        if m.status == "strong" and m.quote and m.requirement_id in reqs and reqs[m.requirement_id].importance == "must"
    ][:4]
    notice = (req.notice_period or "").strip()
    auth = (req.work_authorization or "").strip()
    user = render(
        "cover_letter",
        context_brief=build_context_brief(pack, a.jd, req.resume.level, kb),
        conventions="\n".join(f"- {c}" for c in pack.cover_letter),
        tone_rule=TONE_RULES[req.tone],
        word_budget=WORD_BUDGET[a.region],
        jd_title=a.jd.title,
        company=a.jd.company or "the company",
        notice_rule=f"Mention the notice period once: {notice}." if notice else "Do not mention notice period.",
        auth_rule=f"State work authorisation once: {auth}." if auth else "Do not mention work authorisation.",
        proof_json=json.dumps(proof, ensure_ascii=False),
        about_block=wrap("job_description", a.jd_text[:2500]) if a.jd_text else "",
        resume_block=wrap("resume", render_contact(req.resume.contact) + "\n\n" + render_plain(req.resume)),
    )
    yield stage("tailoring", "active")
    r = await llm.structured(
        "writer",
        render("system_core", region_label=pack.label),
        user,
        LetterBody,
        temperature=LETTER_TEMPERATURE,
        model=req.model,
    )
    body = r.value
    # Facts are checked against the original resume (and what the candidate confirmed), not the tailored
    # version, so wording a rewrite borrowed can't slip into the letter.
    resume_text = "\n".join([a.resume_text, render_plain(a.resume), confirmed_facts(a.profile)])
    years = {str(int(a.resume.total_years_experience))} if a.resume.total_years_experience else set()
    # (text, facts it may use, JD to check for borrowed wording). The company paragraph may quote the JD.
    parts = [
        (body.opening, resume_text, a.jd_text),
        *((p, resume_text, a.jd_text) for p in body.proof[:2]),
        (body.motivation, resume_text + "\n" + a.jd_text, None),
        (body.closing, f"{resume_text}\n{notice}\n{auth}", None),
    ]
    paragraphs, removed = [], []
    for text, source, jd_text in parts:
        kept, dropped = clean_paragraph(text, source, kb, years, jd_text)
        paragraphs.append(kept)
        removed += dropped
    letter = assemble(paragraphs, req.resume.contact, a.jd, a.region, date.today(), removed)
    text = letter_text(letter)
    yield stage("tailoring", "done")
    for block in text.split("\n\n"):
        yield ServerEvent("token", {"text": block + "\n\n"})
    yield ServerEvent("done", {"text": text, "letter": letter.model_dump(), "model": r.model})
