"""Regression tests for the final-review findings."""

import io
from types import SimpleNamespace

import docx
from fastapi.testclient import TestClient
from pydantic import BaseModel

from app.api.ratelimit import RateLimiter, client_key
from app.export.docx import render_resume_docx
from app.knowledge.loader import load_knowledge
from app.llm.client import LLMClient, Target


def req(xff=None, host="10.0.0.1"):
    headers = {"x-forwarded-for": xff} if xff else {}
    return SimpleNamespace(headers=headers, client=SimpleNamespace(host=host))


def test_client_key_uses_rightmost_forwarded_entry():
    assert client_key(req("6.6.6.6, 9.9.9.9")) == "9.9.9.9"
    assert client_key(req()) == "10.0.0.1"


def test_spoofed_leftmost_forwarded_for_does_not_bypass_limit():
    limiter = RateLimiter("2/hour")
    limiter.check(req("1.1.1.1, 9.9.9.9"))
    limiter.check(req("2.2.2.2, 9.9.9.9"))
    try:
        limiter.check(req("3.3.3.3, 9.9.9.9"))
        raise AssertionError("expected RATE_LIMITED")
    except Exception as e:
        assert getattr(e, "code", None) == "RATE_LIMITED"


def test_limiter_prunes_idle_clients():
    limiter = RateLimiter("5/second")
    limiter.check(req(host="a"))
    limiter._hits["a"][0] -= 10  # age the hit past the window
    limiter.check(req(host="b"))
    assert "a" not in limiter._hits


def test_oversized_request_body_rejected():
    from app.main import create_app

    r = TestClient(create_app()).post("/api/tailor", content=b"x", headers={"content-length": str(50 * 1024 * 1024)})
    assert r.status_code == 413 and r.json()["error"]["code"] == "REQUEST_TOO_LARGE"


class X(BaseModel):
    x: int


def fake_client(scripts):
    calls = {m: [] for m in scripts}

    def make(target):
        async def create(**kw):
            calls[kw["model"]].append(kw)
            item = scripts[kw["model"]].pop(0)
            return (
                item
                if isinstance(item, SimpleNamespace)
                else SimpleNamespace(choices=[SimpleNamespace(message=SimpleNamespace(content=item))])
            )

        return SimpleNamespace(chat=SimpleNamespace(completions=SimpleNamespace(create=create)))

    targets = [Target(p, "http://x", "k", m) for p, m in zip(["ollama", "openrouter"], scripts, strict=False)]
    return LLMClient({"analysis": targets, "writer": targets}, 5, make_client=make), calls


async def test_unknown_model_override_is_ignored():
    c, calls = fake_client({"a": ['{"x": 1}']})
    r = await c.structured("analysis", "s", "u", X, model="ollama:some-paid-model")
    assert r.model == "ollama:a" and "some-paid-model" not in calls


async def test_malformed_200_response_falls_back():
    c, _ = fake_client({"a": [SimpleNamespace(choices=None)], "b": ['{"x": 2}']})
    assert (await c.structured("analysis", "s", "u", X)).model == "openrouter:b"


def test_docx_strips_control_characters(sample_doc):
    sample_doc.summary = "Payments\x00 engineer\x07"
    d = docx.Document(io.BytesIO(render_resume_docx(sample_doc, load_knowledge().regions["india"])))
    assert any(p.text == "Payments engineer" for p in d.paragraphs)


def test_allowed_origins_trailing_slash(monkeypatch):
    monkeypatch.setenv("ALLOWED_ORIGINS", "https://web.example.com/")
    from app.main import create_app

    r = TestClient(create_app()).get("/health", headers={"Origin": "https://web.example.com"})
    assert r.headers.get("access-control-allow-origin") == "https://web.example.com"
