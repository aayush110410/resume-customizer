from tests.test_api_analyze import make_client, post, sse_events


def _analysis(monkeypatch, simple_pdf):
    client, fake = make_client(monkeypatch)
    return client, fake, sse_events(post(client, simple_pdf))[-1][1]["analysis"]


def test_rescore_is_code_only(monkeypatch, simple_pdf):
    client, fake, analysis = _analysis(monkeypatch, simple_pdf)
    calls = dict(fake.calls)
    r = client.post("/api/rescore", json={"analysis": analysis, "answers": {"stage": {"value": "early"}}})
    assert r.status_code == 200
    body = r.json()
    assert body["profile"]["stage"] == "early" and body["profile"]["answers"]["stage"]["value"] == "early"
    assert body["scores"]["subscores"]["match"] == analysis["scores"]["subscores"]["match"]
    assert set(body["insights"]) >= {"actions", "tips", "recruiter", "missing_keywords"}
    assert fake.calls == calls  # no model call


def test_rescore_rejects_unknown_question(monkeypatch, simple_pdf):
    client, _, analysis = _analysis(monkeypatch, simple_pdf)
    r = client.post("/api/rescore", json={"analysis": analysis, "answers": {"gap:1999-01": {"value": "health"}}})
    assert r.status_code == 422 and r.json()["error"]["code"] == "INVALID_ANSWERS"


def test_rescore_needs_a_profile(monkeypatch, simple_pdf):
    client, _, analysis = _analysis(monkeypatch, simple_pdf)
    analysis["profile"] = None
    r = client.post("/api/rescore", json={"analysis": analysis, "answers": {}})
    assert r.status_code == 422 and r.json()["error"]["code"] == "INVALID_ANSWERS"
