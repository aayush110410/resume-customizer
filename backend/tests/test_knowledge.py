import re

from app.knowledge.loader import build_context_brief, drop_patterns, load_knowledge, select_tips


def test_packs_load_and_weights():
    kb = load_knowledge()
    assert set(kb.regions) == {"india", "international"}
    assert kb.regions["india"].weights == {"match": 0.35, "ats": 0.20, "quality": 0.15, "region": 0.10, "story": 0.20}
    assert kb.regions["international"].weights == {
        "match": 0.35,
        "ats": 0.20,
        "quality": 0.20,
        "region": 0.10,
        "story": 0.15,
    }
    assert kb.regions["india"].page_size == "a4" and kb.regions["international"].page_size == "us-letter"


def test_all_rule_patterns_compile_and_tip_families_exist():
    kb = load_knowledge()
    for pack in kb.regions.values():
        for rule in [*pack.personal_rules, *pack.term_rules, *pack.drop_sections, *pack.expectations]:
            for p in rule.patterns:
                re.compile(p, re.I | re.M)
        for tip in pack.tips:
            assert set(tip.role_families) <= set(kb.role_families), tip.id


def test_select_tips_filters_by_employer(jd_factory):
    india = load_knowledge().regions["india"]
    psu = " ".join(t.text for t in select_tips(india, jd_factory(employer_type="psu_govt"), "fresher"))
    product = " ".join(t.text for t in select_tips(india, jd_factory(employer_type="product_startup"), "junior"))
    assert "GATE" in psu and "LeetCode" not in psu
    assert "LeetCode" in product


def test_context_brief_contains_region_and_role(jd_factory):
    kb = load_knowledge()
    brief = build_context_brief(kb.regions["international"], jd_factory(role_family="software_engineering"), "mid", kb)
    assert "International" in brief and kb.role_families["software_engineering"].signals[0] in brief
    assert "authori" in brief.lower()


def test_drop_patterns_respect_psu():
    india = load_knowledge().regions["india"]
    assert drop_patterns(india, "psu_govt") == []
    assert any(re.fullmatch(p, "declaration", re.I) for p in drop_patterns(india, "product_startup"))


def test_synonyms_and_lexicons():
    kb = load_knowledge()
    assert "k8s" in kb.synonyms.variants("Kubernetes")
    assert "kubernetes" in kb.synonyms.variants("K8s")
    assert kb.synonyms.variants("unknown-skill-xyz") == {"unknown-skill-xyz"}
    assert "spearheaded" in kb.lexicons.action_verbs and "responsible for" in kb.lexicons.weak_openers
    assert len(kb.lexicons.action_verbs) >= 150


def test_employers_loaded():
    kb = load_knowledge()
    assert kb.employers["infosys"] == "it_services"
    assert kb.employers["hcl"] == "it_services"
    assert kb.employers["google"] == "mega_mnc"
    assert kb.employers["razorpay"] == "product"
    assert kb.employers["isro"] == "govt"


def test_story_rules_by_region():
    kb = load_knowledge()
    india, intl = kb.regions["india"].story, kb.regions["international"].story
    assert (india.gap_months, india.gap_penalty, india.short_stint_months) == (6, {"short": 30, "long": 50}, 12)
    assert (intl.gap_months, intl.gap_penalty, intl.short_stint_months) == (9, {"short": 15, "long": 25}, 9)
    assert "exam_prep" in india.accepted_gap_reasons


def test_role_family_titles():
    kb = load_knowledge()
    assert "bde" in kb.role_families["sales_bd"].titles
    assert "developer" in kb.role_families["software_engineering"].titles


def test_tutorial_list():
    assert "todo" in load_knowledge().tutorial_projects
