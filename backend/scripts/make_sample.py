"""Writes frontend/public/samples/sample-resume.pdf: a fictional resume with deliberate, common flaws
(generic objective, Declaration + DOB, few metrics, weak openers) so the demo shows real findings.

Usage: .venv/bin/python -m scripts.make_sample
"""

from pathlib import Path

from app.export.pdf import render_resume_pdf
from app.knowledge.loader import load_knowledge
from app.schemas import Bullet, Contact, Entry, OtherSection, ResumeDoc, SkillGroup

OUT = Path(__file__).resolve().parents[2] / "frontend" / "public" / "samples" / "sample-resume.pdf"

SAMPLE = ResumeDoc(
    contact=Contact(
        name="Arjun Mehta",
        email="arjun.mehta@example.com",
        phone="+91 98765 43210",
        location="Pune, India",
        links=["linkedin.com/in/arjun-mehta-demo", "github.com/arjun-demo"],
    ),
    summary="Seeking a challenging position in a reputed organisation where I can utilise my skills and grow along with "
    "the organisation. Hardworking and result-oriented team player.",
    skills=[
        SkillGroup(name="Languages", items=["Java", "Python", "SQL", "JavaScript"]),
        SkillGroup(name="Frameworks & Tools", items=["Spring Boot", "Django", "Docker", "Git", "Jenkins", "MySQL"]),
    ],
    experience=[
        Entry(
            title="Senior Systems Engineer",
            organization="Infosys",
            location="Pune",
            start="Aug 2021",
            end="Present",
            bullets=[
                Bullet(text="Responsible for developing REST APIs in Spring Boot for a US banking client."),
                Bullet(text="Worked on migration of batch jobs from cron scripts to Jenkins pipelines."),
                Bullet(text="Reduced report generation time by 40% by rewriting slow SQL queries."),
                Bullet(text="Handled production support and bug fixes for the payments module."),
            ],
        ),
        Entry(
            title="Systems Engineer Trainee",
            organization="Infosys",
            location="Mysuru",
            start="Feb 2021",
            end="Jul 2021",
            bullets=[Bullet(text="Completed training in Java, SQL and agile methodology.")],
        ),
    ],
    projects=[
        Entry(
            title="Expense Tracker",
            organization="Personal project",
            start="2020",
            end="2020",
            bullets=[Bullet(text="Built a Django web app to track monthly expenses with charts.")],
        ),
    ],
    education=[
        Entry(
            title="B.E., Computer Engineering",
            organization="Savitribai Phule Pune University",
            end="2020",
            bullets=[Bullet(text="CGPA: 8.1/10")],
        ),
    ],
    achievements=[
        Bullet(text="Infosys Insta Award for production support, 2022"),
        Bullet(text="Oracle Certified Java Programmer"),
    ],
    other_sections=[
        OtherSection(
            name="Personal Details",
            bullets=[
                Bullet(text="Date of Birth: 14 March 1998"),
                Bullet(text="Marital Status: Single"),
                Bullet(text="Languages Known: English, Hindi, Marathi"),
            ],
        ),
        OtherSection(
            name="Declaration",
            bullets=[Bullet(text="I hereby declare that the above information is true to the best of my knowledge.")],
        ),
    ],
)

if __name__ == "__main__":
    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_bytes(render_resume_pdf(SAMPLE, load_knowledge().regions["india"]))
    print(f"wrote {OUT} ({OUT.stat().st_size} bytes)")
