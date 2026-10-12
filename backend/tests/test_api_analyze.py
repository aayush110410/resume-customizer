import pytest
from fastapi.testclient import TestClient

from app.api.deps import get_llm
from tests.fakes import FakeLLM
from tests.payloads import JD_TEXT, evidence_payload, jd_payload, resume_payload


def sse_events(response):
    events = []
    for block in response.text.replace("\r\n", "\n").split("\n\n"):
        name, data = None, None
        for line in block.split("\n"):
            if line.startswith("event:"):
                name = line[6:].strip()
            elif line.startswith("data:"):
                data = line[5:].strip()
        if name:
            import json

            events.append((name, json.loads(data) if data else None))
    return events


def make_client(monkeypatch, llm=None, **env):
    for k, v in env.items():
        monkeypatch.setenv(k, v)
    from app.main import create_app

    app = create_app()
    fake = llm or FakeLLM(
        {"ResumeDoc": [resume_payload()], "JDAnalysis": [jd_payload()], "Evidence": [evidence_payload()]}
    )
    app.dependency_overrides[get_llm] = lambda: fake
    return TestClient(app), fake


def post(client, pdf, jd=JD_TEXT, region="india", name="cv.pdf"):
    return client.post(
        "/api/analyze", files={"file": (name, pdf, "application/pdf")}, data={"jd": jd, "region": region}
    )


def test_analyze_streams_in_order(monkeypatch, simple_pdf):
    client, _ = make_client(monkeypatch)
    events = sse_events(post(client, simple_pdf))
    names = [e for e, _ in events]
    assert names[0] == "stage" and names[-1] == "done"
    assert names.index("resume") < names.index("evidence") < names.index("scores") < names.index("insights")
    analysis = events[-1][1]["analysis"]
    assert {"resume", "jd", "evidence", "scores", "insights", "prompt_version", "models"} <= set(analysis)
    assert analysis["scores"]["overall"] > 0 and analysis["region"] == "india"


@pytest.mark.parametrize("jd,code", [("short", "JD_TOO_SHORT"), ("x" * 20001, "JD_TOO_LONG")])
def test_jd_validation(monkeypatch, simple_pdf, jd, code):
    client, _ = make_client(monkeypatch)
    r = post(client, simple_pdf, jd=jd)
    assert r.status_code == 422 and r.json()["error"]["code"] == code


def test_rejects_large_and_wrong_type(monkeypatch):
    client, _ = make_client(monkeypatch)
    big = post(client, b"%PDF" + b"0" * (5 * 1024 * 1024 + 1))
    assert big.status_code == 413 and big.json()["error"]["code"] == "FILE_TOO_LARGE"
    gif = post(client, b"GIF89a" + b"0" * 500, name="cv.gif")
    assert gif.status_code == 415 and gif.json()["error"]["code"] == "INVALID_FILE_TYPE"


def test_scanned_pdf_rejected_before_streaming(monkeypatch, scanned_pdf):
    client, _ = make_client(monkeypatch)
    r = post(client, scanned_pdf)
    assert r.status_code == 422 and r.json()["error"]["code"] == "SCANNED_PDF"


def test_llm_failure_becomes_error_event(monkeypatch, simple_pdf):
    client, _ = make_client(monkeypatch, llm=FakeLLM(fail=True))
    name, data = sse_events(post(client, simple_pdf))[-1]
    assert name == "error" and data["code"] == "LLM_UNAVAILABLE" and data["retryable"] is True


def test_not_a_jd_warning(monkeypatch, simple_pdf):
    fake = FakeLLM(
        {"ResumeDoc": [resume_payload()], "JDAnalysis": [jd_payload(is_jd=False)], "Evidence": [evidence_payload()]}
    )
    client, _ = make_client(monkeypatch, llm=fake)
    assert "NOT_A_JD" in [d["code"] for e, d in sse_events(post(client, simple_pdf)) if e == "warning"]


def test_rate_limit(monkeypatch, simple_pdf):
    fake = FakeLLM(
        {"ResumeDoc": [resume_payload()] * 3, "JDAnalysis": [jd_payload()] * 3, "Evidence": [evidence_payload()] * 3}
    )
    client, _ = make_client(monkeypatch, llm=fake, RATE_LIMIT="2/hour")
    post(client, simple_pdf), post(client, simple_pdf)
    r = post(client, simple_pdf)
    assert r.status_code == 429 and r.json()["error"]["code"] == "RATE_LIMITED"


def test_identical_inputs_hit_cache(monkeypatch, simple_pdf):
    fake = FakeLLM(
        {"ResumeDoc": [resume_payload()] * 2, "JDAnalysis": [jd_payload()] * 2, "Evidence": [evidence_payload()] * 2}
    )
    client, _ = make_client(monkeypatch, llm=fake)
    post(client, simple_pdf), post(client, simple_pdf)
    assert fake.calls["ResumeDoc"] == 1 and fake.calls["JDAnalysis"] == 1 and fake.calls["Evidence"] == 2


def test_meta_lists_regions_and_limits(monkeypatch):
    client, _ = make_client(monkeypatch)
    meta = client.get("/api/meta").json()
    assert [r["key"] for r in meta["regions"]] == ["india", "international"]
    assert meta["limits"]["jd_min_chars"] == 300 and "summary" in meta["sections"]
