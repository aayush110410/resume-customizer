from pydantic import TypeAdapter

from app.resume_ops import assign_ids, bullet_index, iter_bullets, render_for_matching, render_plain
from app.schemas import BulletItem, ChangeItem, TailorItem


def test_tailor_item_discriminator():
    item = TypeAdapter(TailorItem).validate_python(
        {"type": "bullet", "entry_id": "exp0", "source_id": "exp0.b1", "text": "x"}
    )
    assert isinstance(item, BulletItem)
    change = TypeAdapter(TailorItem).validate_python(
        {"type": "change", "target_id": "summary", "what": "w", "why": "y"}
    )
    assert isinstance(change, ChangeItem)


def test_assign_ids_is_deterministic(sample_doc):
    doc = assign_ids(sample_doc)
    assert [e.id for e in doc.experience] == ["exp0", "exp1"]
    assert doc.experience[1].bullets[1].id == "exp1.b1"
    assert doc.projects[0].id == "prj0" and doc.projects[0].bullets[0].id == "prj0.b0"
    assert doc.education[0].id == "edu0"
    assert [b.id for b in doc.achievements] == ["ach.b0", "ach.b1"]
    assert assign_ids(doc) == doc


def test_bullet_index_and_iter(sample_doc):
    doc = assign_ids(sample_doc)
    idx = bullet_index(doc)
    assert sorted(idx) == ["ach.b0", "ach.b1", "exp0.b0", "exp0.b1", "exp1.b0", "exp1.b1", "prj0.b0"]
    exp_only = [(s, e, b.id) for s, e, b in iter_bullets(doc, ["experience"])]
    assert exp_only[0] == ("experience", "exp0", "exp0.b0") and len(exp_only) == 4


def test_render_for_matching_tags_bullets(sample_doc):
    text = render_for_matching(assign_ids(sample_doc))
    assert "[exp0.b0] Reduced p99 latency by 30% for 2M daily payments" in text
    assert "[ach.b1] AWS Certified Developer" in text


def test_render_plain_orders_sections(sample_doc):
    doc = assign_ids(sample_doc)
    plain = render_plain(doc)
    assert plain.index("SUMMARY") < plain.index("SKILLS") < plain.index("EXPERIENCE") < plain.index("PROJECTS")
    assert plain.index("PROJECTS") < plain.index("EDUCATION") < plain.index("ACHIEVEMENTS")
    assert "- Reduced p99 latency by 30% for 2M daily payments" in plain
    assert "Software Engineer — Razorpay | Jan 2022 – Present" in plain
    assert "Languages: Python, Go" in plain
