import json
from collections.abc import AsyncIterator

from app.knowledge.loader import build_context_brief
from app.knowledge.models import Knowledge
from app.llm.client import LLM
from app.llm.prompting import render, wrap
from app.resume_ops import render_contact, render_plain
from app.schemas import CoverLetterRequest
from app.services import ServerEvent, stage
from app.services.tailor import TONE_RULES

LETTER_TEMPERATURE = 0.6


async def cover_letter_stream(req: CoverLetterRequest, llm: LLM, kb: Knowledge) -> AsyncIterator[ServerEvent]:
    a = req.analysis
    pack = kb.regions[a.region]
    texts = {q.id: q for q in a.jd.requirements}
    proof = [
        {
            "requirement": texts[m.requirement_id].text,
            "importance": texts[m.requirement_id].importance,
            "evidence": m.quote,
        }
        for m in a.evidence.matches
        if m.status == "strong" and m.quote and m.requirement_id in texts
    ][:4]
    user = render(
        "cover_letter",
        context_brief=build_context_brief(pack, a.jd, req.resume.level, kb),
        conventions="\n".join(f"- {c}" for c in pack.cover_letter),
        tone_rule=TONE_RULES[req.tone],
        jd_title=a.jd.title,
        company=a.jd.company or "the company",
        notice_rule=f"Notice period / availability: {req.notice_period}. Mention it once, briefly, in the close."
        if req.notice_period
        else "Do not mention notice period or availability.",
        auth_rule=f"{req.work_authorization}. State it once, plainly."
        if req.work_authorization
        else "Do not mention it.",
        proof_json=json.dumps(proof, ensure_ascii=False),
        resume_block=wrap("resume", render_contact(req.resume.contact) + "\n\n" + render_plain(req.resume)),
    )
    yield stage("tailoring", "active")
    stream = await llm.open_stream(
        "writer", render("system_core", region_label=pack.label), user, temperature=LETTER_TEMPERATURE, model=req.model
    )
    text = ""
    async for chunk in stream:
        text += chunk
        yield ServerEvent("token", {"text": chunk})
    yield stage("tailoring", "done")
    yield ServerEvent("done", {"text": text, "model": stream.model})
