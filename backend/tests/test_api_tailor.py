import json

import pytest
from fastapi.testclient import TestClient

from app.api.deps import get_llm
from tests.fakes import FakeLLM
from tests.payloads import JD_TEXT, evidence_payload, jd_payload, resume_payload
from tests.test_api_analyze import sse_events

JSONL = [
    '{"type":"summary","text":"Backend engineer who scaled payment APIs in Python and Go."}\n',
    '{"type":"bullet","entry_id":"exp0","source_id":"exp0.b1","text":"Designed REST APIs in Python and Go","addresses":["r1","r2"]}\n',
    '{"type":"change","target_id":"exp0.b1","what":"Led with design","why":"JD stresses API design","requirement_ids":["r2"]}\n',
    '{"type":"bullet","entry_id":"exp0","source_id":"exp0.b0","text":"Reduced p99 latency by 45% for 2M daily payments."}\n',
]


@pytest.fixture
def analysis_json(monkeypatch, simple_pdf):
    from app.main import create_app

    app = create_app()
    app.dependency_overrides[get_llm] = lambda: FakeLLM(
        {"ResumeDoc": [resume_payload()], "JDAnalysis": [jd_payload()], "Evidence": [evidence_payload()]}
    )
    r = TestClient(app).post(
        "/api/analyze", files={"file": ("cv.pdf", simple_pdf, "application/pdf")}, data={"jd": JD_TEXT}
    )
    return sse_events(r)[-1][1]["analysis"]


def tailor_client(llm):
    from app.main import create_app

    app = create_app()
    app.dependency_overrides[get_llm] = lambda: llm
    return TestClient(app)


def test_tailor_streams_items_then_version_with_flags_and_scores(analysis_json):
    llm = FakeLLM({"Evidence": [evidence_payload()]}, stream=JSONL)
    r = tailor_client(llm).post(
        "/api/tailor", json={"analysis": analysis_json, "settings": {"sections": ["summary", "experience"]}}
    )
    events = sse_events(r)
    assert [e for e, _ in events].count("item") == 4
    version = events[-1][1]["version"]
    assert events[-1][0] == "done" and version["model"] == "fake:writer"
    assert version["resume"]["experience"][0]["bullets"][0]["text"] == "Designed REST APIs in Python and Go"
    assert {"target_id": "exp0.b0", "tokens": ["45%"], "reason": "Not in the original bullet"} in version["flags"]
    assert 0 < version["scores"]["overall"] <= 100 and version["changes"][0]["target_id"] == "exp0.b1"


def test_zero_items_triggers_structured_fallback(analysis_json):
    batch = {"items": [json.loads(JSONL[0])]}
    llm = FakeLLM({"TailorBatch": [batch], "Evidence": [evidence_payload()]}, stream=["Sorry, ", "I can't do JSONL."])
    events = sse_events(
        tailor_client(llm).post("/api/tailor", json={"analysis": analysis_json, "settings": {"sections": ["summary"]}})
    )
    assert llm.calls.get("TailorBatch") == 1
    assert events[-1][1]["version"]["resume"]["summary"].startswith("Backend engineer who scaled")


def test_tailor_llm_down_is_error_event(analysis_json):
    events = sse_events(
        tailor_client(FakeLLM(fail=True)).post(
            "/api/tailor", json={"analysis": analysis_json, "settings": {"sections": ["summary"]}}
        )
    )
    assert events[-1][0] == "error" and events[-1][1]["code"] == "LLM_UNAVAILABLE"


def test_must_rewrite_lines_returned_unchanged_get_one_repair_call(analysis_json):
    a = json.loads(json.dumps(analysis_json))
    a["resume"]["experience"][0]["bullets"][2]["text"] = "Responsible for migration to Kubernetes."
    unchanged = (
        '{"type":"bullet","entry_id":"exp0","source_id":"exp0.b2","text":"Responsible for migration to Kubernetes."}\n'
    )
    repair = {
        "items": [
            {"type": "bullet", "entry_id": "exp0", "source_id": "exp0.b2", "text": "Led migration to Kubernetes."}
        ]
    }
    llm = FakeLLM({"TailorBatch": [repair], "Evidence": [evidence_payload()]}, stream=[unchanged])
    events = sse_events(
        tailor_client(llm).post("/api/tailor", json={"analysis": a, "settings": {"sections": ["experience"]}})
    )
    bullets = events[-1][1]["version"]["resume"]["experience"][0]["bullets"]
    assert next(b["text"] for b in bullets if b["id"] == "exp0.b2") == "Led migration to Kubernetes."
    assert llm.calls["TailorBatch"] == 1 and "MUST REWRITE" in llm.prompts[-2]["user"]


def test_tailor_carries_confirmed_answers(analysis_json):
    analysis_json["profile"]["answers"] = {"stage": {"value": "mid", "text": None, "state_on_resume": False}}
    llm = FakeLLM({"Evidence": [evidence_payload()]}, stream=JSONL)
    r = tailor_client(llm).post(
        "/api/tailor", json={"analysis": analysis_json, "settings": {"sections": ["summary", "experience"]}}
    )
    events = sse_events(r)
    assert events[-1][0] == "done"
    writer = next(p for p in llm.prompts if p["schema"] == "stream")
    assert "CONFIRMED BY THE CANDIDATE" in writer["user"] and "<confirmed>\n(none)\n</confirmed>" in writer["user"]
    assert "story" in events[-1][1]["version"]["scores"]["subscores"]
