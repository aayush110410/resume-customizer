"""Streams the writer's JSONL into typed items and assembles the tailored resume deterministically."""

import json
import re
from collections.abc import AsyncIterator

from pydantic import TypeAdapter, ValidationError

from app.schemas import Bullet, BulletItem, ChangeItem, ResumeDoc, SectionKey, SkillsItem, SummaryItem, TailorItem

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


def _reorder(bullets: list[Bullet], items: list[BulletItem]) -> list[Bullet]:
    by_id = {b.id: b for b in bullets}
    out, used = [], set()
    for it in items:
        if it.source_id in by_id and it.source_id not in used:
            out.append(by_id[it.source_id].model_copy(update={"text": it.text.strip()}))
            used.add(it.source_id)
    return out + [b for b in bullets if b.id not in used]


def apply_tailoring(
    original: ResumeDoc, items: list[TailorItem], sections: set[SectionKey], drop: list[str]
) -> tuple[ResumeDoc, list[ChangeItem]]:
    doc = original.model_copy(deep=True)
    summaries = [i for i in items if isinstance(i, SummaryItem)]
    if "summary" in sections and summaries:
        doc.summary = summaries[-1].text.strip()
    skills = [i for i in items if isinstance(i, SkillsItem)]
    if "skills" in sections and skills:
        doc.skills = skills[-1].groups

    bullet_items = [i for i in items if isinstance(i, BulletItem)]
    editable: set[str] = {k for k in ("summary", "skills") if k in sections}
    for section in ("experience", "projects", "education"):
        if section in sections:
            for entry in getattr(doc, section):
                entry.bullets = _reorder(entry.bullets, [b for b in bullet_items if b.entry_id == entry.id])
                editable |= {b.id for b in entry.bullets}
    if "achievements" in sections:
        doc.achievements = _reorder(doc.achievements, [b for b in bullet_items if b.entry_id == "ach"])
        editable |= {b.id for b in doc.achievements}

    changes = [c for c in items if isinstance(c, ChangeItem) and c.target_id in editable]
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
