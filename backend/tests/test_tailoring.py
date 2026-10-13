import pytest

from app.resume_ops import assign_ids, bullet_index, render_contact
from app.schemas import Bullet, BulletItem, ChangeItem, Contact, OtherSection, SkillGroup, SkillsItem, SummaryItem
from app.tailoring import apply_tailoring, parse_jsonl_items


def bullet(entry, source, text):
    return BulletItem(type="bullet", entry_id=entry, source_id=source, text=text)


@pytest.fixture
def doc(sample_doc):
    d = sample_doc.model_copy(deep=True)
    d.experience[0].bullets.append(Bullet(text="Mentored four engineers"))
    d.other_sections = [OtherSection(name="Declaration", bullets=[Bullet(text="I hereby declare...")])]
    return assign_ids(d)


def test_reorder_and_rewrite(doc):
    out, _ = apply_tailoring(doc, [bullet("exp0", "exp0.b2", "X"), bullet("exp0", "exp0.b0", "Y")], {"experience"}, [])
    assert [b.id for b in out.experience[0].bullets] == ["exp0.b2", "exp0.b0", "exp0.b1"]
    assert [b.text for b in out.experience[0].bullets[:2]] == ["X", "Y"]


def test_every_original_bullet_exactly_once(doc):
    items = [
        bullet("exp0", "exp0.b0", "A"),
        bullet("exp0", "exp0.b0", "B"),
        bullet("exp0", "exp9.b1", "C"),
        bullet("zzz", "x", "D"),
        bullet("exp1", "exp0.b1", "wrong entry"),
    ]
    out, _ = apply_tailoring(doc, items, {"experience"}, [])
    assert sorted(bullet_index(out)) == sorted(bullet_index(doc))
    assert (
        out.experience[0].bullets[0].text == "A" and out.experience[0].bullets[1].text == "wrong entry"
    )  # id wins over entry label


def test_unselected_sections_untouched(doc):
    items = [
        SummaryItem(type="summary", text="New"),
        SkillsItem(type="skills", groups=[SkillGroup(name="X", items=["Python"])]),
        bullet("exp0", "exp0.b0", "changed"),
    ]
    out, changes = apply_tailoring(doc, items, {"projects"}, [])
    assert out.summary == doc.summary and out.skills == doc.skills and out.experience == doc.experience


def test_summary_and_skills_when_selected(doc):
    items = [
        SummaryItem(type="summary", text="Old"),
        SummaryItem(type="summary", text=" New "),
        SkillsItem(type="skills", groups=[SkillGroup(name="Core", items=["Go", "Python"])]),
    ]
    out, _ = apply_tailoring(doc, items, {"summary", "skills"}, [])
    assert out.summary == "New" and out.skills[0].items == ["Go", "Python"]


def test_drop_declaration_and_filter_changes(doc):
    items = [
        ChangeItem(type="change", target_id="exp0.b0", what="w", why="y"),
        ChangeItem(type="change", target_id="prj9.b9", what="w", why="y"),
        ChangeItem(type="change", target_id="summary", what="w", why="y"),
    ]
    out, changes = apply_tailoring(doc, items, {"experience"}, ["^declaration$"])
    assert out.other_sections == []
    assert [c.target_id for c in changes] == ["exp0.b0", "oth0"] and changes[-1].what.startswith("Removed section")


def test_render_contact():
    assert (
        render_contact(Contact(name="A B", email="a@b.co", phone="+91 1", links=["x.com/a"]))
        == "A B\na@b.co | +91 1 | x.com/a"
    )


async def chunks(parts):
    for p in parts:
        yield p


async def test_jsonl_parser_skips_bad_lines():
    stream = chunks(
        [
            '{"type":"summary","te',
            'xt":"S"}\nnot json\n```\n',
            '{"type":"change","target_id":"summary","what":"w","why":"y"}',
        ]
    )
    parsed = parse_jsonl_items(stream)
    items = [i async for i in parsed]
    assert [i.type for i in items] == ["summary", "change"] and parsed.invalid == 1


def _ev(*pairs):
    from app.schemas import Evidence, RecruiterVerdict, RequirementMatch

    return Evidence(
        matches=[RequirementMatch(requirement_id=r, status=s, quote=f"{r}-{s}", rationale=s) for r, s in pairs],
        gaps=[],
        recruiter=RecruiterVerdict(decision="maybe", first_impression="", reasons=[]),
    )


def test_keep_best_evidence_never_downgrades():
    from app.tailoring import keep_best_evidence

    merged = keep_best_evidence(
        _ev(("r1", "strong"), ("r2", "partial"), ("r3", "missing")),
        _ev(("r1", "missing"), ("r2", "strong"), ("r3", "missing")),
    )
    assert [(m.requirement_id, m.status, m.quote) for m in merged.matches] == [
        ("r1", "strong", "r1-strong"),
        ("r2", "strong", "r2-strong"),
        ("r3", "missing", "r3-missing"),
    ]


def test_rewritten_skills_cannot_drop_original_skills(doc):
    items = [SkillsItem(type="skills", groups=[SkillGroup(name="Core", items=["Python"])])]
    out, _ = apply_tailoring(doc, items, {"skills"}, [])
    assert out.skills[0].items == ["Python"]
    assert [i for g in out.skills for i in g.items] == ["Python", "Go"]


def test_plan_decides_order_and_skills(doc):
    from app.tailor_plan import TailorPlan

    plan = TailorPlan(
        bullets=[],
        order={"exp0": ["exp0.b1", "exp0.b2", "exp0.b0"]},
        skills=[SkillGroup(name="Languages", items=["Go", "Python"])],
        summary_facts=[],
    )
    items = [
        bullet("exp0", "exp0.b0", "A"),
        bullet("exp0", "exp0.b2", "C"),
        SkillsItem(type="skills", groups=[SkillGroup(name="Mine", items=["Python"])]),
    ]
    out, changes = apply_tailoring(doc, items, {"experience", "skills"}, [], plan)
    assert [b.id for b in out.experience[0].bullets] == ["exp0.b1", "exp0.b2", "exp0.b0"]
    assert [b.text for b in out.experience[0].bullets][1:] == ["C", "A"]
    assert out.skills == plan.skills and any(c.target_id == "skills" for c in changes)


def test_bullets_matched_by_their_own_id_even_if_model_mangles_entry_id(doc):
    items = [BulletItem(type="bullet", entry_id="entry exp0", source_id="[exp0.b1]", text="Rewritten")]
    out, _ = apply_tailoring(doc, items, {"experience"}, [])
    assert next(b for b in out.experience[0].bullets if b.id == "exp0.b1").text == "Rewritten"


@pytest.mark.parametrize(
    "original,rewritten,expected",
    [
        (
            "Handled production support and bug fixes for the payments module.",
            "Managed production support and bug fixes for the payments module, ensuring uninterrupted transaction processing.",
            "Managed production support and bug fixes for the payments module.",
        ),
        (
            "Reduced report generation time by 40% by rewriting slow SQL queries.",
            "Optimised SQL queries, cutting report generation time by 40% and improving data processing efficiency.",
            "Optimised SQL queries, cutting report generation time by 40%.",
        ),
        (
            "Built REST APIs in Spring Boot used by 3 internal teams.",
            "Built REST APIs in Spring Boot, serving 3 internal teams.",
            "Built REST APIs in Spring Boot, serving 3 internal teams.",
        ),
    ],
)
def test_invented_outcome_clauses_are_removed(original, rewritten, expected):
    from app.tailoring import strip_invented_outcomes

    assert strip_invented_outcomes(original, rewritten) == expected


@pytest.mark.parametrize("original,rewritten,expected", [
    ("Reduced report generation time by 40% by rewriting slow SQL queries.",
     "Reduced report generation time by 40% by rewriting slow SQL queries significantly.",
     "Reduced report generation time by 40% by rewriting slow SQL queries."),
    ("Handled production support and bug fixes for the payments module.",
     "Managed production support and bug fixes for the payments module in a banking application.",
     "Managed production support and bug fixes for the payments module."),
    ("Completed training in Java, SQL and agile methodology.",
     "Completed training in Java, SQL and agile methodology to enhance development capabilities.",
     "Completed training in Java, SQL and agile methodology."),
    ("Built REST APIs in Spring Boot used by 3 internal teams.",
     "Built REST APIs in Spring Boot for 3 internal teams.",
     "Built REST APIs in Spring Boot for 3 internal teams."),
])
def test_unsupported_trailing_words_are_removed(original, rewritten, expected):
    from app.tailoring import strip_invented_outcomes

    assert strip_invented_outcomes(original, rewritten) == expected
