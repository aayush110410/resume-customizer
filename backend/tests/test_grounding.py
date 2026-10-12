import pytest

from app.guard.grounding import find_fabrications, verify_evidence, verify_quote
from app.knowledge.models import Knowledge, Lexicons, SynonymIndex
from app.resume_ops import assign_ids, render_plain
from app.schemas import Bullet, Evidence, RecruiterVerdict, RequirementMatch, SkillGroup


@pytest.fixture
def kb() -> Knowledge:
    return Knowledge(
        regions={},
        role_families={},
        lexicons=Lexicons(frozenset(), [], [], []),
        synonyms=SynonymIndex.from_mapping({"kubernetes": ["k8s"], "amazon web services": ["aws"]}),
    )


@pytest.fixture
def doc(sample_doc):
    return assign_ids(sample_doc)


def ev(*matches):
    return Evidence(
        matches=[
            RequirementMatch(requirement_id=r, status=s, bullet_ids=ids, quote=q, rationale="x")
            for r, s, ids, q in matches
        ],
        gaps=[],
        recruiter=RecruiterVerdict(decision="maybe", first_impression="", reasons=[]),
    )


def tailored_with(doc, **bullet_texts):
    out = doc.model_copy(deep=True)
    for _, _, b in [(None, None, b) for e in out.experience for b in e.bullets]:
        if b.id.replace(".", "_") in bullet_texts:
            b.text = bullet_texts[b.id.replace(".", "_")]
    return out


def test_ligature_quote_verifies():
    assert verify_quote("efficient API design", "Eﬃcient API design for payments")


def test_paraphrase_quote_fails():
    assert not verify_quote("led a team of 12 engineers", "Worked with engineers on payments")


def test_unverified_strong_downgrades_to_partial(doc):
    out = verify_evidence(ev(("r1", "strong", ["exp0.b0"], "invented a quantum compiler")), doc, render_plain(doc))
    assert out.matches[0].status == "partial" and out.matches[0].verified is False


def test_verified_quote_keeps_status(doc):
    out = verify_evidence(ev(("r1", "strong", ["exp0.b0"], "Reduced p99 latency by 30%")), doc, render_plain(doc))
    assert out.matches[0].status == "strong" and out.matches[0].verified


def test_unknown_bullet_ids_dropped(doc):
    out = verify_evidence(ev(("r1", "strong", ["exp9.b9", "exp0.b0"], "Built REST APIs")), doc, render_plain(doc))
    assert out.matches[0].bullet_ids == ["exp0.b0"]


def test_claim_without_any_evidence_downgrades(doc):
    out = verify_evidence(ev(("r1", "partial", ["nope"], None)), doc, render_plain(doc))
    assert out.matches[0].status == "transferable"


def test_missing_stays_missing(doc):
    assert verify_evidence(ev(("r1", "missing", [], None)), doc, render_plain(doc)).matches[0].status == "missing"


def test_changed_metric_flagged(doc, kb):
    t = tailored_with(doc, exp0_b0="Cut p99 latency by 45% for 2M daily payments")
    flags = find_fabrications(doc, render_plain(doc), t, kb)
    assert [(f.target_id, f.tokens) for f in flags] == [("exp0.b0", ["45%"])]


def test_new_tool_flagged(doc, kb):
    t = tailored_with(doc, exp1_b1="Wrote SQL reports in Snowflake")
    flags = find_fabrications(doc, render_plain(doc), t, kb)
    assert flags[0].target_id == "exp1.b1" and "Snowflake" in flags[0].tokens


def test_synonym_and_rephrase_not_flagged(doc, kb):
    d = doc.model_copy(deep=True)
    d.experience[0].bullets[1] = Bullet(id="exp0.b1", text="Built REST APIs on k8s")
    t = tailored_with(
        d, exp0_b1="Shipped REST APIs running on Kubernetes", exp0_b0="Cut p99 latency 30% across 2M daily payments"
    )
    assert find_fabrications(d, render_plain(d), t, kb) == []


def test_invented_skill_and_summary_number_flagged(doc, kb):
    t = doc.model_copy(deep=True)
    t.skills = [SkillGroup(name="Languages", items=["Python", "Go", "Rust"])]
    t.summary = "Backend engineer with 7 years building payment APIs."
    flags = {f.target_id: f.tokens for f in find_fabrications(doc, render_plain(doc), t, kb)}
    assert flags == {"skills": ["Rust"], "summary": ["7"]}
