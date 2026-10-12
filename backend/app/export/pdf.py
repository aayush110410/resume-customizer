"""PDF rendering with Typst (embedded Libertinus font; no system fonts or binaries needed)."""

import json
from pathlib import Path

import typst

from app.knowledge.models import RegionPack
from app.schemas import Contact, ResumeDoc

TEMPLATES = Path(__file__).parent / "templates"


def _compile(template: str, data: dict, paper: str) -> bytes:
    return typst.compile(str(TEMPLATES / template), sys_inputs={"data": json.dumps(data), "paper": paper})


def render_resume_pdf(doc: ResumeDoc, region: RegionPack) -> bytes:
    return _compile("resume.typ", doc.model_dump(), region.page_size)


def paragraphs(text: str) -> list[str]:
    return [
        " ".join(p.split()) if "\n" not in p.strip() else p.strip() for p in text.strip().split("\n\n") if p.strip()
    ]


def render_letter_pdf(text: str, contact: Contact, region: RegionPack) -> bytes:
    return _compile("letter.typ", {"contact": contact.model_dump(), "paragraphs": paragraphs(text)}, region.page_size)
