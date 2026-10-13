"""Streams the writer's JSONL into typed items and assembles the tailored resume deterministically."""

import json
import re
from collections.abc import AsyncIterator
from typing import TYPE_CHECKING

from pydantic import TypeAdapter, ValidationError

from app.resume_ops import render_plain
from app.schemas import (
    Bullet,
    BulletItem,
    ChangeItem,
    Evidence,
    ResumeDoc,
    SectionKey,
    SkillGroup,
    SkillsItem,
    SummaryItem,
    TailorItem,
)
from app.scoring.match import CREDIT

if TYPE_CHECKING:
    from app.tailor_plan import TailorPlan
from app.text_utils import normalize

_ITEM = TypeAdapter(TailorItem)


class parse_jsonl_items:  # noqa: N801 — used like a function returning an async iterator
    """Async iterator of valid TailorItems from streamed text chunks; counts skipped lines in `.invalid`."""

    def __init__(self, chunks: AsyncIterator[str]):
        self._chunks = chunks
        self.invalid = 0

    def _parse(self, line: str) -> TailorItem | None:
        line = line.strip()
        if not line or line.startswith("```"):
            return None
        try:
            return _ITEM.validate_python(json.loads(line))
        except (ValueError, ValidationError):
            self.invalid += 1
            return None

    async def __aiter__(self) -> AsyncIterator[TailorItem]:
        buffer = ""
        async for chunk in self._chunks:
            buffer += chunk
            *lines, buffer = buffer.split("\n")
            for line in lines:
                if (item := self._parse(line)) is not None:
                    yield item
        if (item := self._parse(buffer)) is not None:
            yield item


_TAIL = re.compile(r"(?:,\s*|\s+and\s+)\w+ing\b")
_STOP = {"with", "from", "into", "that", "this", "their", "across", "while", "through", "over", "more", "less", "than"}


def _supported(clause: str, original: str) -> bool:
    """A trailing clause stays only if it restates the original: one of its numbers, or most of its words."""
    numbers = re.findall(r"\d[\d,.]*%?", clause)
    if numbers and any(n.rstrip(".,") in original for n in numbers):
        return True
    words = [w for w in re.findall(r"[a-z]+", clause.lower())[1:] if len(w) > 3 and w not in _STOP]
    if not words:
        return True
    stems = {w[:5] for w in re.findall(r"[a-z]+", original.lower())}
    return sum(w[:5] in stems for w in words) / len(words) >= 0.6


def strip_invented_outcomes(original: str, rewritten: str) -> str:
    """Removes trailing ", improving X" / "and ensuring Y" clauses the writer added without support in the original."""
    text = rewritten.strip()
    end = "." if text.endswith(".") else ""
    body, changed = text.rstrip("."), False
    while starts := [m.start() for m in _TAIL.finditer(body)]:
        tail = body[starts[-1] :]
        if _supported(tail, original):
            break
        body, changed = body[: starts[-1]].rstrip(" ,"), True
    # Then trailing words after the last word the original also contains ("…queries significantly").
    stems = {w[:5] for w in re.findall(r"[a-z]+", original.lower())}
    numbers = set(re.findall(r"\d[\d,.]*%?", original))
    tokens = list(re.finditer(r"[A-Za-z][\w+#./-]*|\d[\d,.]*%?", body))
    known = [t for t in tokens if t.group(0)[:5].lower() in stems or t.group(0) in numbers]
    if known and known[-1].end() < len(body):
        tail = body[known[-1].end() :]
        if re.search(r"[A-Za-z]{4,}", tail) and not any(n in tail for n in numbers):
            body, changed = body[: known[-1].end()].rstrip(" ,"), True
    return body + end if changed else text


def _reorder(bullets: list[Bullet], items: list[BulletItem]) -> list[Bullet]:
    by_id = {b.id: b for b in bullets}
    out, used = [], set()
    for it in items:
        if it.source_id in by_id and it.source_id not in used:
            src = by_id[it.source_id]
            out.append(
                src.model_copy(
                    update={"text": strip_invented_outcomes(src.text, it.text) if it.text.strip() else src.text}
                )
            )
            used.add(it.source_id)
    return out + [b for b in bullets if b.id not in used]


def _keep_all_skills(original: list[SkillGroup], rewritten: list[SkillGroup]) -> list[SkillGroup]:
    """The writer may reorder and regroup skills but never drop one: dropped skills return under their old group."""
    groups = [g.model_copy(deep=True) for g in rewritten]
    present = {normalize(i) for g in groups for i in g.items}
    for old in original:
        dropped = [i for i in old.items if normalize(i) not in present]
        if dropped:
            target = next((g for g in groups if normalize(g.name) == normalize(old.name)), None)
            if target is None:
                target = SkillGroup(name=old.name, items=[])
                groups.append(target)
            target.items.extend(dropped)
            present |= {normalize(i) for i in dropped}
    return groups


def keep_best_evidence(before: Evidence, after: Evidence) -> Evidence:
    """Tailoring keeps every original fact, so a requirement can't lose evidence; a weaker re-judgment is model noise."""
    prior = {m.requirement_id: m for m in before.matches}
    out = after.model_copy(deep=True)
    out.matches = [
        prior[m.requirement_id]
        if m.requirement_id in prior and CREDIT[prior[m.requirement_id].status] > CREDIT[m.status]
        else m
        for m in out.matches
    ]
    return out


def apply_tailoring(
    original: ResumeDoc,
    items: list[TailorItem],
    sections: set[SectionKey],
    drop: list[str],
    plan: "TailorPlan | None" = None,
) -> tuple[ResumeDoc, list[ChangeItem]]:
    doc = original.model_copy(deep=True)
    summaries = [i for i in items if isinstance(i, SummaryItem)]
    if "summary" in sections and summaries:
        # Each sentence is held to the whole original resume: unsupported trailing outcome clauses are cut.
        support = render_plain(original)
        sentences = re.split(r"(?<=[.!?])\s+", summaries[-1].text.strip())
        doc.summary = " ".join(strip_invented_outcomes(support, sent) for sent in sentences if sent.strip())
    skills = [i for i in items if isinstance(i, SkillsItem)]
    if "skills" in sections and plan is not None:
        doc.skills = plan.skills  # code-ranked: JD matches first, nothing dropped
    elif "skills" in sections and skills:
        doc.skills = _keep_all_skills(original.skills, skills[-1].groups)

    # The model's ids are cleaned and the entry is taken from the bullet's own id ("exp0.b2" → "exp0").
    bullet_items = [
        i.model_copy(
            update={"source_id": (sid := re.sub(r"[^\w.]", "", i.source_id)), "entry_id": sid.rsplit(".b", 1)[0]}
        )
        for i in items
        if isinstance(i, BulletItem)
    ]
    editable: set[str] = {k for k in ("summary", "skills") if k in sections}
    for section in ("experience", "projects", "education"):
        if section in sections:
            for entry in getattr(doc, section):
                entry.bullets = _reorder(entry.bullets, [b for b in bullet_items if b.entry_id == entry.id])
                if plan is not None and entry.id in plan.order:
                    rank = {bid: i for i, bid in enumerate(plan.order[entry.id])}
                    entry.bullets.sort(key=lambda b: rank.get(b.id, len(rank)))
                editable |= {b.id for b in entry.bullets}
    if "achievements" in sections:
        doc.achievements = _reorder(doc.achievements, [b for b in bullet_items if b.entry_id == "ach"])
        editable |= {b.id for b in doc.achievements}

    changes = [c for c in items if isinstance(c, ChangeItem) and c.target_id in editable]
    if (
        "skills" in sections
        and plan is not None
        and doc.skills != original.skills
        and not any(c.target_id == "skills" for c in changes)
    ):
        changes.append(
            ChangeItem(
                type="change",
                target_id="skills",
                what="Put the skills this job asks for first",
                why="Recruiters and ATS read the first items of each skills line",
            )
        )
    kept = []
    for other in doc.other_sections:
        if any(re.fullmatch(p, other.name.strip(), re.I) for p in drop):
            changes.append(
                ChangeItem(
                    type="change",
                    target_id=other.id,
                    what=f"Removed section '{other.name}'",
                    why="Not expected by recruiters for this region and employer type",
                )
            )
        else:
            kept.append(other)
    doc.other_sections = kept
    return doc, changes
