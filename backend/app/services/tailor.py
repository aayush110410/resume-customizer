import re
import uuid
from collections.abc import AsyncIterator
from datetime import UTC, datetime

from app.guard.grounding import find_fabrications
from app.knowledge.loader import build_context_brief, drop_patterns
from app.knowledge.models import Knowledge
from app.llm.client import LLM, LLMUnavailable
from app.llm.prompting import render
from app.llm.tasks import match_evidence
from app.resume_ops import render_contact, render_plain
from app.schemas import BulletItem, LayoutReport, ResumeDoc, TailorBatch, TailoredVersion, TailorRequest
from app.scoring import score_all
from app.services import ServerEvent, stage
from app.tailor_plan import build_plan
from app.tailoring import apply_tailoring, keep_best_evidence, parse_jsonl_items
from app.text_utils import estimate_pages, normalize

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


def _selected(plan, sections: set[str]):
    return [b for b in plan.bullets if ("experience" if b.entry_id.startswith("exp") else "projects") in sections]


def _lines(plan, resume, sections: set[str], label: dict[str, str], only: set[str] | None = None) -> str:
    out = []
    for b in _selected(plan, sections):
        if only is not None and b.id not in only:
            continue
        proves = ", ".join(label[r] for r in b.requirement_ids if r in label) or "none (keep it tight)"
        use = "; ".join(f'"{a}" → "{t}"' for a, t in b.mirror) or "—"
        out.append(
            f"[{b.id}]{' MUST REWRITE' if b.must_rewrite else ''} · proves: {proves} · use: {use}"
            f" · keep: {', '.join(b.numbers) or '—'} · weak opener: {b.weak_opener or '—'}\n    original: {b.text}"
        )
    if "achievements" in sections and only is None:
        for a in resume.achievements:
            out.append(f"[{a.id}] entry ach · proves: — · use: — · keep: — · weak opener: —\n    original: {a.text}")
    return "\n".join(out) or "(no lines selected)"


async def tailor_stream(req: TailorRequest, llm: LLM, kb: Knowledge) -> AsyncIterator[ServerEvent]:
    a, s = req.analysis, req.settings
    pack = kb.regions[a.region]
    plan = build_plan(a.resume, a.jd, a.evidence, kb)
    label = {q.id: f"{q.id} {q.text} ({q.importance})" for q in a.jd.requirements}
    sections = set(s.sections)
    summary_block, summary_format = "", ""
    years = int(a.resume.total_years_experience)
    if "summary" in sections:
        current = a.resume.experience[0].title if a.resume.experience else None
        facts = "\n".join(f"   - {f}" for f in plan.summary_facts) or "   - (use the strongest lines above)"
        summary_block = (
            "\nSUMMARY: also write a 2–3 sentence summary, 40–70 words, from ONLY these facts.\n"
            + (f'   - experience: {years}+ years (write it exactly as "{years}+ years")\n' if years else "")
            + f"   - current title: {current or 'not stated'}\n{facts}\n"
            "   Sentence 1: who they are (title, years, domain). Sentence 2–3: their strongest proof for this kind of role.\n"
            "   Never mention the job being applied for, never say seeking/looking for/aspiring, no first person, no clichés.\n"
        )
        summary_format = '{"type":"summary","text":"<summary>"}\n'
    system = render("system_core", region_label=pack.label)
    render_args = dict(
        context_brief=build_context_brief(pack, a.jd, a.resume.level, kb),
        tone_rule=TONE_RULES[s.tone],
        spelling={"us": "US English", "uk": "British English"}.get(a.jd.spelling, "match the JD"),
    )
    user = render(
        "tailor",
        **render_args,
        summary_block=summary_block,
        summary_format=summary_format,
        lines=_lines(plan, a.resume, sections, label),
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
    # Verify, then repair: lines that had to change but came back unchanged get one targeted retry.
    returned = {re.sub(r"[^\w.]", "", i.source_id): i.text for i in items if isinstance(i, BulletItem)}
    todo = {
        b.id
        for b in _selected(plan, sections)
        if b.must_rewrite and normalize(returned.get(b.id, b.text)) == normalize(b.text)
    }
    if todo:
        repair_user = render(
            "tailor",
            **render_args,
            summary_block="",
            summary_format="",
            lines=_lines(plan, a.resume, sections, label, todo),
        )
        repair_user += "\n\nThese lines came back unchanged. Each is marked MUST REWRITE: rewrite every one now."
        try:
            fixed = await llm.structured(
                "writer", system, repair_user, TailorBatch, temperature=WRITER_TEMPERATURE, model=s.model
            )
            repaired = [
                i for i in fixed.value.items if isinstance(i, BulletItem) and re.sub(r"[^\w.]", "", i.source_id) in todo
            ]
            done_ids = {re.sub(r"[^\w.]", "", i.source_id) for i in repaired}
            # the repaired line replaces the unchanged one (assembly keeps the first line per bullet)
            items = [
                i for i in items if not (isinstance(i, BulletItem) and re.sub(r"[^\w.]", "", i.source_id) in done_ids)
            ] + repaired
            for item in repaired:
                yield ServerEvent("item", item.model_dump())
        except LLMUnavailable:
            pass  # the originals stand; nothing is lost
    yield stage("tailoring", "done")

    yield stage("verifying", "active")
    tailored, changes = apply_tailoring(a.resume, items, sections, drop_patterns(pack, a.jd.employer_type), plan)
    flags = find_fabrications(a.resume, a.resume_text, tailored, kb, allowed={str(years)} if years else None)
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
