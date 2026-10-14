import pytest

from app.knowledge.loader import load_knowledge
from app.llm.tasks import read_projects
from app.profile.projects import rule_facts, score_project
from app.resume_ops import assign_ids, render_plain
from app.schemas import Bullet, Contact, CustomName, Entry, ProjectFacts, ResumeDoc
from tests.fakes import FakeLLM


@pytest.fixture
def kb():
    return load_knowledge()


def project(title, *bullets) -> Entry:
    return Entry(title=title, organization="Personal", bullets=[Bullet(text=b) for b in bullets])


def test_full_marks(kb):
    entry = project(
        "PayLite",
        "Built a UPI split-bill app for hostel students using React, Node.js and PostgreSQL",
        "Used by 10k users; live at paylite.app",
    )
    facts = ProjectFacts(
        project_id="prj0",
        purpose="a UPI split-bill app for hostel students",
        users="Used by 10k users",
        scale="10k users",
        links=["paylite.app"],
    )
    read = score_project(entry, facts, kb, set())
    assert read.score == 100 and read.notes == []


def test_tutorial_without_and_with_extension(kb):
    entry = project("Expense Tracker", "Developed a Django web app to track monthly expenses")
    plain = ProjectFacts(project_id="prj0", purpose="track monthly expenses", tutorial_pattern="expense tracker")
    extended = plain.model_copy(update={"extension": "parses UPI SMS alerts into expenses"})
    a, b = score_project(entry, plain, kb, set()), score_project(entry, extended, kb, set())
    assert b.score - a.score == 10
    assert any("tutorial" in n for n in a.notes)


def test_custom_names_penalty_and_answer(kb):
    entry = project("Zephyr", "Built Zephyr and Nimbus on top of Kite for order processing")
    names = [CustomName(name=n) for n in ("Zephyr", "Nimbus", "Kite")]
    two = ProjectFacts(project_id="prj0", purpose="order processing", custom_names=names[:2])
    three = two.model_copy(update={"custom_names": names})
    base = score_project(entry, two.model_copy(update={"custom_names": []}), kb, set()).score
    assert base - score_project(entry, two, kb, set()).score == 10
    assert base - score_project(entry, three, kb, set()).score == 15
    answered = score_project(entry, two, kb, {"zephyr"})
    assert base - answered.score == 5
    assert not any("Zephyr" in n for n in answered.notes)


def test_rule_facts_fallback(kb):
    entry = project("Todo App", "Made a todo list with React", "Code: github.com/me/todo")
    facts = rule_facts(entry, kb)
    assert facts.tutorial_pattern == "todo" and facts.links == ["github.com/me/todo"]
    assert facts.purpose == "Made a todo list with React"


def _resume() -> ResumeDoc:
    return assign_ids(
        ResumeDoc(
            contact=Contact(name="T"),
            projects=[project("Zephyr", "Built Zephyr, an event-sourcing library used by 3 teams")],
        )
    )


async def test_read_projects_drops_unverified(kb):
    resume = _resume()
    text = render_plain(resume)
    fake = FakeLLM(
        {
            "ProjectFactsBatch": [
                {
                    "projects": [
                        {
                            "project_id": "prj0",
                            "purpose": "a distributed database used by Fortune 500 banks",
                            "users": "used by 3 teams",
                            "custom_names": [
                                {
                                    "name": "Zephyr",
                                    "what": "event-sourcing library",
                                    "quote": "an event-sourcing library",
                                },
                                {"name": "Hydra", "what": "a queue", "quote": "Hydra queue"},
                            ],
                        }
                    ]
                }
            ]
        }
    )
    r = await read_projects(fake, resume, text, kb)
    (facts,) = r.value
    assert facts.purpose is None and facts.users == "used by 3 teams"
    assert [c.name for c in facts.custom_names] == ["Zephyr"]


async def test_read_projects_without_projects_makes_no_call(kb):
    fake = FakeLLM()
    r = await read_projects(fake, ResumeDoc(contact=Contact(name="T")), "", kb)
    assert r.value == [] and fake.calls == {}
