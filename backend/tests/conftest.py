import pytest
from fastapi.testclient import TestClient

from app.schemas import Bullet, Contact, Entry, ResumeDoc, SkillGroup


@pytest.fixture
def sample_doc() -> ResumeDoc:
    return ResumeDoc(
        contact=Contact(name="Arjun Mehta", email="arjun@example.com", phone="+91 98765 43210", location="Bengaluru"),
        summary="Backend engineer with 4 years building payment APIs.",
        skills=[SkillGroup(name="Languages", items=["Python", "Go"])],
        experience=[
            Entry(
                title="Software Engineer",
                organization="Razorpay",
                start="Jan 2022",
                end="Present",
                bullets=[
                    Bullet(text="Reduced p99 latency by 30% for 2M daily payments"),
                    Bullet(text="Built REST APIs"),
                ],
            ),
            Entry(
                title="Associate Engineer",
                organization="Infosys",
                start="Jul 2020",
                end="Dec 2021",
                bullets=[Bullet(text="Maintained billing jobs"), Bullet(text="Wrote SQL reports")],
            ),
        ],
        projects=[Entry(title="Ledger CLI", organization="Personal", bullets=[Bullet(text="Open-source ledger tool")])],
        education=[Entry(title="B.Tech, Computer Science", organization="NIT Trichy", end="2020")],
        achievements=[Bullet(text="Winner, Smart India Hackathon 2019"), Bullet(text="AWS Certified Developer")],
    )


@pytest.fixture
def client() -> TestClient:
    from app.main import create_app

    return TestClient(create_app())
