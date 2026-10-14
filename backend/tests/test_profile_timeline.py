from datetime import date

import pytest

from app.knowledge.loader import load_knowledge
from app.profile.timeline import build_stints, find_gaps, parse_date
from app.resume_ops import assign_ids
from app.schemas import Contact, Entry, ResumeDoc

TODAY = date(2026, 10, 14)


@pytest.fixture
def kb():
    return load_knowledge()


def doc(experience=(), education=()) -> ResumeDoc:
    return assign_ids(
        ResumeDoc(
            contact=Contact(name="Test"),
            experience=[Entry(title=t, organization=o, start=s, end=e) for t, o, s, e in experience],
            education=[Entry(title=t, organization=o, start=s, end=e) for t, o, s, e in education],
        )
    )


def test_parse_date_precision():
    assert parse_date("May 2021", TODAY) == (date(2021, 5, 1), True)
    assert parse_date("2021-05", TODAY) == (date(2021, 5, 1), True)
    assert parse_date("05/2021", TODAY) == (date(2021, 5, 1), True)
    assert parse_date("2021", TODAY) == (date(2021, 1, 1), False)
    assert parse_date("Present", TODAY) == (date(2026, 10, 1), True)
    assert parse_date("", TODAY) is None


def test_kinds(kb):
    rows = [
        ("SDE Intern", "Acme"),
        ("Apprentice (NATS)", "BHEL"),
        ("Graduate Engineer Trainee", "L&T"),
        ("Freelance Developer", "Self"),
        ("Software Engineering Virtual Experience", "Forage"),
        ("Engineer", "Acme"),
    ]
    resume = doc([(t, o, "Jan 2024", "Jun 2024") for t, o in rows])
    kinds = [s.kind for s in build_stints(resume, kb, kb.regions["india"].story, TODAY)]
    assert kinds == ["internship", "apprenticeship", "trainee", "freelance", "virtual_program", "job"]


def test_short_stint(kb):
    rules = kb.regions["india"].story
    stints = build_stints(doc([("Engineer", "A", "Jan 2023", "Apr 2023")]), kb, rules, TODAY)
    assert stints[0].months == 4 and stints[0].short is True and stints[0].precise is True
    current = build_stints(doc([("Engineer", "B", "Jul 2026", "Present")]), kb, rules, TODAY)
    assert current[0].short is False


def test_year_only_not_short(kb):
    rules = kb.regions["india"].story
    resume = doc([("Engineer", "A", "2022", "2022"), ("Engineer", "B", "Jan 2023", "Present")])
    stints = build_stints(resume, kb, rules, TODAY)
    assert stints[0].precise is False and stints[0].short is False and stints[0].months is None
    assert find_gaps(resume, stints, rules, TODAY) == []


def test_gap_after_education(kb):
    rules = kb.regions["india"].story
    resume = doc([("Engineer", "A", "Aug 2022", "Present")], [("B.Tech", "NIT", "Jul 2017", "May 2021")])
    gaps = find_gaps(resume, build_stints(resume, kb, rules, TODAY), rules, TODAY)
    assert [(g.id, g.start, g.end, g.months, g.after_entry_id) for g in gaps] == [
        ("gap:2021-06", "2021-06", "2022-07", 14, "edu0")
    ]
    short = doc([("Engineer", "A", "Nov 2021", "Present")], [("B.Tech", "NIT", "Jul 2017", "May 2021")])
    assert find_gaps(short, build_stints(short, kb, rules, TODAY), rules, TODAY) == []


def test_overlaps_not_gaps(kb):
    rules = kb.regions["india"].story
    resume = doc(
        [
            ("Engineer", "A", "Jan 2020", "Dec 2022"),
            ("Freelance Developer", "Self", "Jun 2021", "Mar 2022"),
            ("Engineer", "B", "Jan 2023", "Present"),
        ]
    )
    stints = build_stints(resume, kb, rules, TODAY)
    assert find_gaps(resume, stints, rules, TODAY) == []
    assert not any(s.short for s in stints)


def test_no_education_date(kb):
    rules = kb.regions["india"].story
    resume = doc(
        [("Engineer", "A", "Jan 2018", "Dec 2019"), ("Engineer", "B", "Jan 2021", "Present")],
        [("B.Tech", "NIT", None, None)],
    )
    gaps = find_gaps(resume, build_stints(resume, kb, rules, TODAY), rules, TODAY)
    assert [(g.start, g.end, g.months, g.after_entry_id) for g in gaps] == [("2020-01", "2020-12", 12, "exp0")]


def test_current_break_counts(kb):
    rules = kb.regions["india"].story
    resume = doc([("Engineer", "A", "Jan 2020", "Dec 2025")])
    gaps = find_gaps(resume, build_stints(resume, kb, rules, TODAY), rules, TODAY)
    assert [(g.start, g.end, g.months) for g in gaps] == [("2026-01", "2026-10", 10)]


def test_student_holes_are_not_gaps(kb):
    rules = kb.regions["india"].story
    resume = doc(
        [("SDE Intern", "A", "May 2025", "Jul 2025"), ("Intern", "B", "Jan 2024", "Feb 2024")],
        [("B.Tech, CSE", "VIT", None, "May 2028"), ("Class XII", "DPS", None, "2023")],
    )
    assert find_gaps(resume, build_stints(resume, kb, rules, TODAY), rules, TODAY) == []


def test_two_digit_years_after_month():
    assert parse_date("Jun 21", TODAY) == (date(2021, 6, 1), True)
    assert parse_date("Jun-21", TODAY) == (date(2021, 6, 1), True)
    assert parse_date("06/21", TODAY) == (date(2021, 6, 1), True)


def test_undated_role_suppresses_gaps(kb):
    rules = kb.regions["india"].story
    resume = doc([("Software Engineer", "Acme", None, None)], [("B.Tech", "NIT", "Jul 2017", "May 2021")])
    assert find_gaps(resume, build_stints(resume, kb, rules, TODAY), rules, TODAY) == []


def test_stated_career_break_covers_gap(kb):
    rules = kb.regions["india"].story
    resume = doc(
        [
            ("Software Engineer", "Acme", "Aug 2023", "Present"),
            ("Career break: UPSC preparation", "", "Jun 2021", "Jul 2023"),
        ],
        [("B.Tech", "NIT", "Jul 2017", "May 2021")],
    )
    assert find_gaps(resume, build_stints(resume, kb, rules, TODAY), rules, TODAY) == []


def test_promotion_at_same_employer_is_not_a_short_stint(kb):
    rules = kb.regions["india"].story
    resume = doc(
        [
            ("Senior Systems Engineer", "Infosys", "Aug 2021", "Present"),
            ("Systems Engineer Trainee", "Infosys Ltd", "Feb 2021", "Jul 2021"),
        ]
    )
    assert not any(s.short for s in build_stints(resume, kb, rules, TODAY))
    boomerang = doc([("Engineer", "Acme", "Jan 2022", "Apr 2022"), ("Engineer", "Acme", "Jun 2023", "Sep 2023")])
    assert sum(s.short for s in build_stints(boomerang, kb, rules, TODAY)) == 2  # 8 months in total: still short


def test_gap_precision(kb):
    rules = kb.regions["india"].story
    rough = doc([("Engineer", "A", "2022", "Present")], [("B.Tech", "NIT", None, "2019")])
    (g,) = find_gaps(rough, build_stints(rough, kb, rules, TODAY), rules, TODAY)
    assert (g.start, g.end, g.precise) == ("2020-01", "2021-12", False)
    exact = doc([("Engineer", "A", "Aug 2022", "Present")], [("B.Tech", "NIT", "Jul 2017", "May 2021")])
    assert find_gaps(exact, build_stints(exact, kb, rules, TODAY), rules, TODAY)[0].precise is True
