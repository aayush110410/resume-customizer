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


def test_sentence_start_capitals_are_not_facts(doc, kb):
    t = doc.model_copy(deep=True)
    t.summary = "Backend engineer building payment APIs. Proven record shipping REST APIs."
    assert find_fabrications(doc, render_plain(doc), t, kb) == []


def test_slash_terms_kept_whole_and_decimals_reported_once(doc, kb):
    t = tailored_with(doc, exp1_b0="Maintained billing jobs on CI/CD with 99.9% uptime")
    assert find_fabrications(doc, render_plain(doc), t, kb)[0].tokens == ["99.9%", "CI/CD"]


def test_lowercase_known_skill_flagged(doc, kb):
    t = tailored_with(doc, exp1_b1="Wrote SQL reports streamed through kubernetes")
    assert find_fabrications(doc, render_plain(doc), t, kb)[0].tokens == ["kubernetes"]


def test_lowercase_ordinary_words_not_flagged(doc, kb):
    t = tailored_with(doc, exp1_b1="Wrote clear SQL reports for finance stakeholders")
    assert find_fabrications(doc, render_plain(doc), t, kb) == []


def test_code_supplied_numbers_are_allowed(doc, kb):
    t = doc.model_copy(deep=True)
    t.summary = "Backend engineer with 5+ years building payment APIs."
    assert find_fabrications(doc, render_plain(doc), t, kb) != []
    assert find_fabrications(doc, render_plain(doc), t, kb, allowed={"5"}) == []


def test_singular_acronym_of_plural_original_not_flagged(doc, kb):
    t = tailored_with(doc, exp0_b1="Built a REST API")
    assert find_fabrications(doc, render_plain(doc), t, kb) == []


JD = (
    "Design, build and own Python and Java microservices for payment orchestration and reconciliation. "
    "Run services on Kubernetes. Mentor junior engineers."
)


@pytest.fixture
def real_kb():
    from app.knowledge.loader import load_knowledge

    return load_knowledge()


def _with_bullets(doc, *texts):
    d = doc.model_copy(deep=True)
    d.experience[1].bullets = [Bullet(id=f"exp1.b{i}", text=t) for i, t in enumerate(texts)]
    return d


def test_new_jd_wording_flagged(doc, real_kb):
    d = _with_bullets(doc, "Handled support and bug fixes for the payments module")
    t = tailored_with(d, exp1_b0="Supported and fixed bugs in the payment orchestration module")
    flags = find_fabrications(d, render_plain(d), t, real_kb, jd_text=JD)
    assert [(f.target_id, f.tokens) for f in flags] == [("exp1.b0", ["orchestration"])]
    assert "job description" in flags[0].reason


def test_jd_verbs_synonyms_and_existing_words_not_flagged(doc, real_kb):
    d = _with_bullets(doc, "Made billing APIs for merchants", "Wrote SQL reports for reconciliation", "Ran jobs on k8s")
    t = tailored_with(
        d,
        exp1_b0="Designed billing APIs for merchants",  # JD verb: wording, not a fact
        exp1_b1="Built SQL reports for monthly reconciliation",  # "reconciliation" is already in the original
        exp1_b2="Ran jobs on Kubernetes",  # synonym of k8s
    )
    assert find_fabrications(d, render_plain(d), t, real_kb, jd_text=JD) == []


def test_new_jd_wording_in_summary_flagged(doc, real_kb):
    t = doc.model_copy(update={"summary": "Backend engineer with 4 years building payment orchestration APIs."})
    flags = find_fabrications(doc, render_plain(doc), t, real_kb, jd_text=JD)
    assert ("summary", ["orchestration"]) in [(f.target_id, f.tokens) for f in flags]


def test_without_jd_text_behaviour_is_unchanged(doc, real_kb):
    d = _with_bullets(doc, "Handled support and bug fixes for the payments module")
    t = tailored_with(d, exp1_b0="Supported and fixed bugs in the payment orchestration module")
    assert find_fabrications(d, render_plain(d), t, real_kb) == []


def test_years_of_experience_wording_is_not_a_claim(doc, real_kb):
    d = doc.model_copy(update={"summary": "Engineer who builds payment APIs."})
    t = d.model_copy(update={"summary": "Engineer with 4 years of experience building payment APIs."})
    jd = "3+ years of backend development experience."
    # the years figure itself is computed by code and passed as allowed, as the tailor service does
    assert find_fabrications(d, render_plain(d), t, real_kb, allowed={"4"}, jd_text=jd) == []


def test_intensifiers_are_not_claims(doc, real_kb):
    d = doc.model_copy(update={"summary": "Engineer who builds payment APIs."})
    t = d.model_copy(update={"summary": "Engineer with strong, proven and solid skills building payment APIs."})
    jd = "Strong problem solving. Proven, solid engineering skills."
    assert find_fabrications(d, render_plain(d), t, real_kb, jd_text=jd) == []
