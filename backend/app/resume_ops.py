"""Deterministic operations over ResumeDoc: stable IDs, traversal and plain-text rendering."""

from collections.abc import Callable, Iterable, Iterator
from typing import Literal

from app.schemas import Bullet, Contact, Entry, ResumeDoc, SectionKey

_ENTRY_SECTIONS: tuple[tuple[SectionKey, str], ...] = (
    ("experience", "exp"),
    ("projects", "prj"),
    ("education", "edu"),
)


def assign_ids(doc: ResumeDoc) -> ResumeDoc:
    doc = doc.model_copy(deep=True)
    for section, prefix in _ENTRY_SECTIONS:
        for i, entry in enumerate(getattr(doc, section)):
            entry.id = f"{prefix}{i}"
            for j, bullet in enumerate(entry.bullets):
                bullet.id = f"{entry.id}.b{j}"
    for j, bullet in enumerate(doc.achievements):
        bullet.id = f"ach.b{j}"
    for i, other in enumerate(doc.other_sections):
        other.id = f"oth{i}"
        for j, bullet in enumerate(other.bullets):
            bullet.id = f"{other.id}.b{j}"
    return doc


def iter_bullets(
    doc: ResumeDoc, sections: Iterable[SectionKey] | None = None
) -> Iterator[tuple[SectionKey | Literal["other"], str, Bullet]]:
    wanted = set(sections) if sections is not None else None

    def want(key: str) -> bool:
        return wanted is None or key in wanted

    for section, _ in _ENTRY_SECTIONS:
        if want(section):
            for entry in getattr(doc, section):
                for bullet in entry.bullets:
                    yield section, entry.id, bullet
    if want("achievements"):
        for bullet in doc.achievements:
            yield "achievements", "ach", bullet
    if wanted is None:
        for other in doc.other_sections:
            for bullet in other.bullets:
                yield "other", other.id, bullet


def bullet_index(doc: ResumeDoc) -> dict[str, Bullet]:
    return {bullet.id: bullet for _, _, bullet in iter_bullets(doc)}


def _entry_line(entry: Entry) -> str:
    parts = [f"{entry.title}, {entry.organization}" if entry.organization else entry.title]
    if entry.location:
        parts.append(entry.location)
    dates = " – ".join(d for d in (entry.start, entry.end) if d)
    if dates:
        parts.append(dates)
    return " | ".join(parts)


def _render(doc: ResumeDoc, entry_line: Callable[[Entry], str], bullet_line: Callable[[Bullet], str]) -> str:
    lines: list[str] = []
    if doc.summary:
        lines += ["SUMMARY", doc.summary, ""]
    if doc.skills:
        lines += ["SKILLS", *(f"{g.name}: {', '.join(g.items)}" for g in doc.skills), ""]
    for section, _ in _ENTRY_SECTIONS:
        entries: list[Entry] = getattr(doc, section)
        if entries:
            lines.append(section.upper())
            for entry in entries:
                lines += [entry_line(entry), *(bullet_line(b) for b in entry.bullets)]
            lines.append("")
    if doc.achievements:
        lines += ["ACHIEVEMENTS", *(bullet_line(b) for b in doc.achievements), ""]
    for other in doc.other_sections:
        lines += [other.name.upper(), *(bullet_line(b) for b in other.bullets), ""]
    return "\n".join(lines).strip()


def render_for_matching(doc: ResumeDoc) -> str:
    """Resume as the evidence matcher sees it: every bullet tagged with its ID so quotes can be traced."""
    return _render(doc, lambda e: f"<{e.id}> {_entry_line(e)}", lambda b: f"[{b.id}] {b.text}")


def render_plain(doc: ResumeDoc) -> str:
    return _render(doc, _entry_line, lambda b: f"- {b.text}")


def render_contact(contact: Contact) -> str:
    details = [d for d in (contact.email, contact.phone, contact.location, *contact.links) if d]
    return contact.name + ("\n" + " | ".join(details) if details else "")
