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


def test_clean_paragraph_trims_outcomes_and_borrowed_jd_wording():
    resume = "Handled production support and bug fixes for the payments module. Built REST APIs in Spring Boot."
    jd_text = "Design Python and Java microservices for payment orchestration and reconciliation."
    text = (
        "I built REST APIs in Spring Boot, ensuring high availability. "
        "I handled production support and bug fixes for the payment orchestration module."
    )
    kept, removed = clean_paragraph(text, resume, KB, jd_text=jd_text)
    assert kept == "I built REST APIs in Spring Boot."
    assert any("orchestration" in r for r in removed)


def test_contact_details_are_not_repeated_in_the_body():
    source = SOURCE + " arjun@example.com +91 98765 43210"
    kept, removed = clean_paragraph(
        "I would welcome a conversation. You can reach me at +91 98765 43210 or arjun@example.com.", source, KB
    )
    assert kept == "I would welcome a conversation." and len(removed) == 1


def test_free_sentences_are_not_truncated():
    sentence = "I built REST APIs in Spring Boot and would welcome a call to discuss the role."
    kept, removed = clean_paragraph(sentence, SOURCE, KB)
    assert kept == sentence and removed == []


def test_enthusiasm_filler_is_rewritten_not_dropped():
    kept, removed = clean_paragraph("I am excited to contribute to your team. I cut report time by 40%.", SOURCE, KB)
    assert kept == "I would like to contribute to your team. I cut report time by 40%." and removed == []


def test_everyday_words_are_not_borrowed_jd_wording():
    source = "Responsible for developing REST APIs in Spring Boot for a US banking client."
    jd_text = "You will have to build and own REST APIs. Join a team that has shipped payments at scale."
    sentence = "I have developed REST APIs using Spring Boot for a US banking client."
    assert clean_paragraph(sentence, source, KB, jd_text=jd_text) == (sentence, [])


def test_leveraging_becomes_using():
    kept, _ = clean_paragraph("I built REST APIs in Spring Boot, leveraging SQL.", SOURCE, KB)
    assert kept == "I built REST APIs in Spring Boot, using SQL."


def test_bullet_style_sentences_become_first_person():
    kept, _ = clean_paragraph("Reduced report generation time by 40% by rewriting slow SQL queries.", SOURCE, KB)
    assert kept == "I reduced report generation time by 40% by rewriting slow SQL queries."


def test_recipient_drops_work_mode_notes():
    letter = assemble(["Opening."], Contact(name="A"), jd(location="Bengaluru, India (hybrid)"), "india", TODAY)
    assert letter.recipient[-1] == "Bengaluru, India"
