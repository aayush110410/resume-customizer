import json
import uuid
from collections.abc import AsyncIterator
from datetime import UTC, datetime

from app.guard.grounding import find_fabrications
from app.knowledge.loader import build_context_brief, drop_patterns
from app.knowledge.models import Knowledge
from app.llm.client import LLM
from app.llm.prompting import render, wrap
from app.llm.tasks import match_evidence
from app.resume_ops import render_contact, render_for_matching, render_plain
from app.schemas import LayoutReport, ResumeDoc, TailorBatch, TailoredVersion, TailorRequest
from app.scoring import score_all
from app.services import ServerEvent, stage
from app.tailoring import apply_tailoring, keep_best_evidence, parse_jsonl_items
from app.text_utils import estimate_pages

TONE_RULES = {
    "conservative": "Minimal edits: keep the candidate's own wording; fix weak openers, mirror evidenced JD terms, reorder.",
    "balanced": "Rephrase for impact and relevance; tighten wording; mirror evidenced JD terms.",
    "bold": "Assertive rewrite: strongest accurate verbs, outcomes first, restructure bullets — still strictly truthful.",
}
WRITER_TEMPERATURE = 0.4


def resume_text_for_scoring(doc: ResumeDoc) -> tuple[str, LayoutReport]:
    """Text and layout of the tailored resume as exported by our single-column, ATS-safe template."""
    text = render_contact(doc.contact) + "\n\n" + render_plain(doc)
    words = len(text.split())
    return text, LayoutReport(
        file_type="generated", pages=estimate_pages(words), char_count=len(text), word_count=words
    )


async def tailor_stream(req: TailorRequest, llm: LLM, kb: Knowledge) -> AsyncIterator[ServerEvent]:
    a, s = req.analysis, req.settings
    pack = kb.regions[a.region]
    system = render("system_core", region_label=pack.label)
    user = render(
        "tailor",
        sections=", ".join(s.sections),
        context_brief=build_context_brief(pack, a.jd, a.resume.level, kb),
        tone_rule=TONE_RULES[s.tone],
        spelling={"us": "US English", "uk": "British English"}.get(a.jd.spelling, "match the JD"),
        requirements_json=json.dumps([q.model_dump(include={"id", "text", "importance"}) for q in a.jd.requirements]),
        evidence_json=json.dumps(
            [m.model_dump(include={"requirement_id", "status", "bullet_ids"}) for m in a.evidence.matches]
        ),
        resume_block=wrap("resume", render_for_matching(a.resume)),
    )

    yield stage("tailoring", "active")
    stream = await llm.open_stream("writer", system, user, temperature=WRITER_TEMPERATURE, model=s.model)
    model, items = stream.model, []
    async for item in parse_jsonl_items(stream):
        items.append(item)
        yield ServerEvent("item", item.model_dump())
    if not items:
        note = '\n\nReturn a single JSON object {"items": [...]} containing the same objects instead of JSON Lines.'
        batch = await llm.structured(
            "writer", system, user + note, TailorBatch, temperature=WRITER_TEMPERATURE, model=s.model
        )
        model, items = batch.model, list(batch.value.items)
        for item in items:
            yield ServerEvent("item", item.model_dump())
    yield stage("tailoring", "done")

    yield stage("verifying", "active")
    tailored, changes = apply_tailoring(a.resume, items, set(s.sections), drop_patterns(pack, a.jd.employer_type))
    flags = find_fabrications(a.resume, a.resume_text, tailored, kb)
    yield stage("verifying", "done")

    yield stage("rescoring", "active")
    text, layout = resume_text_for_scoring(tailored)
    ev = await match_evidence(llm, tailored, text, a.jd, pack, kb)
    evidence = keep_best_evidence(a.evidence, ev.value)
    scores = score_all(text, layout, tailored, a.jd, evidence, a.region, kb)
    yield stage("rescoring", "done")

    version = TailoredVersion(
        id=uuid.uuid4().hex[:8],
        created_at=datetime.now(UTC).isoformat(timespec="seconds"),
        settings=s,
        resume=tailored,
        changes=changes,
        flags=flags,
        scores=scores,
        model=model,
    )
    yield ServerEvent("done", {"version": version.model_dump()})
