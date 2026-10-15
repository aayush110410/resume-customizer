from datetime import date

from app.knowledge.loader import load_knowledge
from app.letter import assemble, clean_paragraph, letter_date, letter_text
from app.schemas import Contact, JDAnalysis

KB = load_knowledge()
TODAY = date(2026, 10, 15)
SOURCE = "Reduced report generation time by 40% by rewriting slow SQL queries. Built REST APIs in Spring Boot."


def jd(company="Acme Payments", location="Bengaluru, India") -> JDAnalysis:
    return JDAnalysis(
        is_job_description=True,
        title="Backend Engineer (SDE-2)",
        company=company,
        location=location,
        role_family="software_engineering",
        employer_type="product_startup",
        seniority="mid",
        suggested_region="india",
        requirements=[],
        ats_keywords=[],
    )


def test_date_follows_the_region():
    assert letter_date(TODAY, "india") == "15 October 2026"
    assert letter_date(TODAY, "international") == "October 15, 2026"


def test_india_letter_has_subject_and_regards():
    letter = assemble(["Opening.", "Proof."], Contact(name="Arjun Mehta"), jd(), "india", TODAY)
    assert letter.recipient == ["Hiring Team", "Acme Payments", "Bengaluru, India"]
    assert letter.subject == "Subject: Application for Backend Engineer (SDE-2)"
    assert letter.salutation == "Dear Acme Payments Hiring Team,"
    assert (letter.sign_off, letter.name) == ("Regards,", "Arjun Mehta")


def test_international_letter_without_company():
    letter = assemble(
        ["Opening."], Contact(name="Arjun Mehta"), jd(company=None, location=None), "international", TODAY
    )
    assert letter.recipient == ["Hiring Team"] and letter.subject is None
    assert (letter.salutation, letter.sign_off) == ("Dear Hiring Manager,", "Sincerely,")


def test_clean_paragraph_drops_cliches_and_invented_claims():
    text = (
        "I am writing to apply for this role. I cut report generation time by 40% by rewriting SQL queries. "
        "I also scaled Kafka pipelines to 10 million events a day."
    )
    kept, removed = clean_paragraph(text, SOURCE, KB)
    assert kept == "I cut report generation time by 40% by rewriting SQL queries."
    assert len(removed) == 2


def test_letter_text_layout():
    letter = assemble(["First paragraph.", "Second paragraph."], Contact(name="Arjun Mehta"), jd(), "india", TODAY)
    blocks = letter_text(letter).split("\n\n")
    assert blocks[0] == "15 October 2026"
    assert blocks[1] == "Hiring Team\nAcme Payments\nBengaluru, India"
    assert blocks[2].startswith("Subject:") and blocks[3] == "Dear Acme Payments Hiring Team,"
    assert blocks[-1] == "Regards,\nArjun Mehta"
