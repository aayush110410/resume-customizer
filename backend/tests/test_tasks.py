from app.knowledge.loader import load_knowledge
from app.llm.tasks import analyze_jd, match_evidence, structure_resume
from app.resume_ops import assign_ids
from tests.fakes import FakeLLM

RESUME_TEXT = "Arjun Mehta\nEXPERIENCE\nSoftware Engineer, Razorpay\nReduced p99 latency by 30% for 2M daily payments\n"


def extraction(*bullets):
    return {
        "contact": {"name": "Arjun Mehta"},
        "experience": [
            {"title": "Software Engineer", "organization": "Razorpay", "bullets": [{"text": b} for b in bullets]}
        ],
    }


async def test_structure_assigns_ids_and_drops_ungrounded():
    llm = FakeLLM(
        {
            "ResumeDoc": [
                extraction("Led a 40-person team at Google", "Reduced p99 latency by 30% for 2M daily payments")
            ]
        }
    )
    doc = (await structure_resume(llm, RESUME_TEXT)).value
    assert [(b.id, b.text[:7]) for b in doc.experience[0].bullets] == [("exp0.b0", "Reduced")]
    assert "<resume>" in llm.prompts[0]["user"]


def jd_payload(n_reqs, family="software_engineering"):
    imp = ["nice", "should", "must"]
    return {
        "is_job_description": True,
        "title": "SDE",
        "role_family": family,
        "employer_type": "product_startup",
        "seniority": "mid",
        "suggested_region": "india",
        "requirements": [{"text": f"Skill {i}", "type": "hard_skill", "importance": imp[i % 3]} for i in range(n_reqs)],
        "ats_keywords": ["Python", "python", " Go ", "Kafka"],
    }


async def test_analyze_jd_ids_cap_order_and_family():
    kb = load_knowledge()
    jd = (await analyze_jd(FakeLLM({"JDAnalysis": [jd_payload(30, family="astronaut")]}), "JD text", kb)).value
    assert len(jd.requirements) == 25 and jd.requirements[0].id == "r1" and jd.requirements[24].id == "r25"
    assert [q.importance for q in jd.requirements[:10]] == ["must"] * 10
    assert jd.role_family == "general" and jd.ats_keywords == ["Python", "Go", "Kafka"]


async def test_match_normalizes_ids_and_verifies(sample_doc, jd_factory):
    kb = load_knowledge()
    doc = assign_ids(sample_doc)
    reqs = [
        {"id": f"r{i}", "text": t, "type": "hard_skill", "importance": "must"}
        for i, t in enumerate(["Python", "Go", "Rust"], 1)
    ]
    jd = jd_factory(requirements=reqs)
    payload = {
        "matches": [
            {
                "requirement_id": "r1",
                "status": "strong",
                "bullet_ids": ["exp0.b0"],
                "quote": "Reduced p99 latency by 30%",
                "rationale": "x",
            },
            {"requirement_id": "r1", "status": "missing", "rationale": "duplicate"},
            {"requirement_id": "r99", "status": "strong", "rationale": "unknown"},
            {
                "requirement_id": "r2",
                "status": "strong",
                "bullet_ids": [],
                "quote": "Wrote Go at Google",
                "rationale": "x",
            },
        ],
        "gaps": [
            {"requirement_id": "r99", "title": "t", "action": "a"},
            {"requirement_id": "r3", "title": "t", "action": "a"},
        ],
        "recruiter": {"decision": "maybe", "first_impression": "ok", "reasons": []},
        "tips": [{"tip_id": "made-up", "advice": "x"}],
    }
    ev = (await match_evidence(FakeLLM({"Evidence": [payload]}), doc, "raw", jd, kb.regions["india"], kb)).value
    assert [(m.requirement_id, m.status) for m in ev.matches] == [
        ("r1", "strong"),
        ("r2", "partial"),
        ("r3", "missing"),
    ]
    assert ev.matches[1].quote == "Go" and ev.matches[1].verified  # code fact replaces the unverifiable claim
    assert [g.requirement_id for g in ev.gaps] == ["r3"] and ev.tips == []


async def test_structure_computes_years_and_level_from_dates():
    payload = extraction("Reduced p99 latency by 30% for 2M daily payments")
    payload["experience"][0] |= {"start": "Jan 2015", "end": "Dec 2022"}
    payload |= {"total_years_experience": 1.0, "level": "junior"}
    doc = (await structure_resume(FakeLLM({"ResumeDoc": [payload]}), RESUME_TEXT)).value
    assert doc.total_years_experience == 8.0 and doc.level == "senior"


async def test_match_code_facts_floor_and_hints(sample_doc, jd_factory):
    kb = load_knowledge()
    doc = assign_ids(sample_doc.model_copy(update={"total_years_experience": 4.0}))
    reqs = [
        {"id": "r1", "text": "3+ years of backend experience", "type": "experience", "importance": "must"},
        {"id": "r2", "text": "Go", "type": "hard_skill", "importance": "must", "keywords": ["go"]},
        {"id": "r3", "text": "Kafka", "type": "tool", "importance": "should", "keywords": ["kafka"]},
    ]
    payload = {
        "matches": [
            {"requirement_id": "r1", "status": "missing", "rationale": "model thinks no"},
            {"requirement_id": "r2", "status": "missing", "rationale": "model missed the skills list"},
            {
                "requirement_id": "r3",
                "status": "strong",
                "bullet_ids": ["exp0.b0"],
                "quote": "Kafka streams at scale",
                "rationale": "invented",
            },
        ],
        "gaps": [
            {"requirement_id": "r1", "title": "t", "action": "a"},
            {"requirement_id": "r3", "title": "Kafka", "action": "a"},
        ],
        "recruiter": {"decision": "maybe", "first_impression": "ok", "reasons": []},
    }
    llm = FakeLLM({"Evidence": [payload]})
    ev = (await match_evidence(llm, doc, "raw", jd_factory(requirements=reqs), kb.regions["india"], kb)).value
    assert [(m.requirement_id, m.status) for m in ev.matches] == [
        ("r1", "strong"),
        ("r2", "partial"),
        ("r3", "missing"),
    ]
    assert [g.requirement_id for g in ev.gaps] == ["r3"]  # no gap for a requirement code proved
    prompt = llm.prompts[0]["user"]
    assert "r1: DECIDED" in prompt and "r2: listed" in prompt and "r3: no keyword hit" in prompt


async def test_structured_jd_requirements_come_from_code_not_the_model():
    from pathlib import Path

    kb = load_knowledge()
    jd_text = (Path(__file__).parent.parent / "evals/golden/jd_sde2_bengaluru.txt").read_text()
    jd = (await analyze_jd(FakeLLM({"JDAnalysis": [jd_payload(5)]}), jd_text, kb)).value
    texts = [q.text for q in jd.requirements]
    assert texts[0] == "3+ years of backend development experience." and "Skill 0" not in texts
    assert [q.id for q in jd.requirements[:2]] == ["r1", "r2"] and jd.requirements[0].type == "experience"
    assert jd.min_years == 3 and jd.ats_keywords[:2] == ["Python", "Java"]
    docker = next(q for q in jd.requirements if q.text == "Experience with Docker")
    assert docker.importance == "must" and docker.keywords == ["Docker"]


async def test_prose_jd_keeps_model_requirements():
    jd = (
        await analyze_jd(FakeLLM({"JDAnalysis": [jd_payload(5)]}), "We need a great engineer. " * 30, load_knowledge())
    ).value
    assert [q.text for q in jd.requirements][:1] == ["Skill 2"]
