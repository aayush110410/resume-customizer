"""Cover letter layout and checks. The model writes the paragraphs; this module builds the letter around them
and drops any sentence that is a cliché or claims something the resume doesn't say."""

import re
from datetime import date

from app.guard.grounding import borrowed_jd_words, unsupported
from app.knowledge.models import Knowledge
from app.schemas import Contact, CoverLetter, JDAnalysis, Region
from app.tailoring import strip_invented_outcomes

_SENTENCE = re.compile(r"(?<=[.!?])\s+")
_CONTACT = re.compile(r"\S+@\S+\.\w+|\+?\d[\d\s-]{8,}\d")  # already in the letterhead
_CLICHES = re.compile(
    r"\b(i am writing to|writing to (apply|express)|express(ing)? my interest|i am confident|i believe i would|"
    r"team player|hard-?working|result-?oriented|results-?driven|passionate|dynamic|synergy|seamless(ly)?|"
    r"go-getter|kindly|do the needful|thanking you in anticipation|respected sir|to whom it may concern|"
    r"perfect fit|dream (job|role)|excited to apply|humbly|add value|(i am|i'm) (excited|thrilled|eager|delighted) to)\b",
    re.I,
)


def letter_date(today: date, region: Region) -> str:
    if region == "india":
        return f"{today.day} {today:%B %Y}"
    return f"{today:%B} {today.day}, {today.year}"


def clean_paragraph(
    text: str,
    source_text: str,
    kb: Knowledge,
    allowed_numbers: set[str] | None = None,
    jd_text: str | None = None,
) -> tuple[str, list[str]]:
    """Keep the sentences that are free of clichés and only state facts found in the source. Trailing outcome
    clauses the source doesn't support are trimmed; with `jd_text`, a sentence that borrows JD wording the
    source never uses is dropped."""
    kept, removed = [], []
    for sentence in _SENTENCE.split(" ".join(text.split())):
        if not sentence:
            continue
        sentence = strip_invented_outcomes(source_text, sentence, trim_words=False)
        borrowed = bool(jd_text) and borrowed_jd_words(sentence, source_text, jd_text or "", kb)
        if (
            _CLICHES.search(sentence)
            or _CONTACT.search(sentence)
            or unsupported(sentence, source_text, kb, allowed_numbers)
            or borrowed
        ):
            removed.append(sentence)
        else:
            kept.append(sentence)
    return " ".join(kept), removed


def assemble(
    paragraphs: list[str], contact: Contact, jd: JDAnalysis, region: Region, today: date, removed=()
) -> CoverLetter:
    company = jd.company
    return CoverLetter(
        date=letter_date(today, region),
        recipient=[line for line in ("Hiring Team", company, jd.location) if line],
        subject=f"Subject: Application for {jd.title}" if region == "india" else None,
        salutation=f"Dear {company} Hiring Team," if company else "Dear Hiring Manager,",
        paragraphs=[p for p in paragraphs if p],
        sign_off="Regards," if region == "india" else "Sincerely,",
        name=contact.name,
        removed=list(removed),
    )


def letter_text(letter: CoverLetter) -> str:
    """The letter as plain text, blocks separated by blank lines (the letterhead is added on export)."""
    blocks = [letter.date, "\n".join(letter.recipient)]
    if letter.subject:
        blocks.append(letter.subject)
    blocks += [letter.salutation, *letter.paragraphs, f"{letter.sign_off}\n{letter.name}"]
    return "\n\n".join(blocks)
