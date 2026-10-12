from app.resume_ops import render_contact, render_plain
from app.schemas import ResumeDoc


def render_txt(doc: ResumeDoc) -> str:
    return render_contact(doc.contact) + "\n\n" + render_plain(doc) + "\n"
