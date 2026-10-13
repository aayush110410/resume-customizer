from types import SimpleNamespace

import httpx
import openai
import pytest
from pydantic import BaseModel

from app.llm.client import LLMClient, LLMUnavailable, Target, extract_json


class X(BaseModel):
    x: int


def err(cls, status):
    return cls("boom", response=httpx.Response(status, request=httpx.Request("POST", "http://t")), body=None)


def completion(content):
    return SimpleNamespace(choices=[SimpleNamespace(message=SimpleNamespace(content=content))])


class FakeStream:
    def __init__(self, chunks):
        self.chunks = chunks

    def __aiter__(self):
        async def gen():
            for c in self.chunks:
                yield SimpleNamespace(choices=[SimpleNamespace(delta=SimpleNamespace(content=c))])

        return gen()


def client_with(scripts, *, providers=None, role="analysis"):
    """scripts: {model: [response | Exception | list-of-stream-chunks, ...]} consumed in order per model."""
    calls: dict[str, list[dict]] = {m: [] for m in scripts}
    providers = providers or {m: p for m, p in zip(scripts, ["ollama", "openrouter", "groq"], strict=False)}

    def make(target):
        async def create(**kw):
            calls[kw["model"]].append(kw)
            item = scripts[kw["model"]].pop(0)
            if isinstance(item, Exception):
                raise item
            return FakeStream(item) if kw.get("stream") else completion(item)

        return SimpleNamespace(chat=SimpleNamespace(completions=SimpleNamespace(create=create)))

    targets = [Target(providers[m], f"http://{m}", "k", m) for m in scripts]
    return LLMClient({"analysis": targets, "writer": targets}, timeout_s=5, make_client=make), calls


async def test_falls_back_on_rate_limit():
    c, _ = client_with({"a": [err(openai.RateLimitError, 429)], "b": ['{"x": 1}']})
    r = await c.structured("analysis", "s", "u", X)
    assert r.value.x == 1 and r.model == "openrouter:b"


async def test_json_schema_rejected_then_json_object_same_target():
    c, calls = client_with({"a": [err(openai.BadRequestError, 400), '{"x": 2}']})
    r = await c.structured("analysis", "s", "u", X)
    assert r.value.x == 2
    assert calls["a"][0]["response_format"]["type"] == "json_schema"
    assert calls["a"][1]["response_format"] == {"type": "json_object"}
    assert '"x"' in calls["a"][1]["messages"][0]["content"]  # schema appended to system prompt


async def test_repair_once_then_success():
    c, calls = client_with({"a": ['{"x": "oops"}', '{"x": 3}']})
    r = await c.structured("analysis", "s", "u", X)
    assert r.value.x == 3 and len(calls["a"]) == 2
    assert "failed validation" in calls["a"][1]["messages"][-1]["content"]


async def test_second_invalid_output_moves_to_next_target():
    c, _ = client_with({"a": ["nope", "still nope"], "b": ['{"x": 4}']})
    assert (await c.structured("analysis", "s", "u", X)).model == "openrouter:b"


def test_extract_json_handles_think_and_fences():
    assert extract_json('<think>{"x": 9}</think>```json\n{"x": 1}\n```') == {"x": 1}
    with pytest.raises(ValueError):
        extract_json("no json here")


async def test_all_fail_raises_with_attempts():
    c, _ = client_with({"a": [err(openai.InternalServerError, 503)], "b": [err(openai.AuthenticationError, 401)]})
    with pytest.raises(LLMUnavailable) as e:
        await c.structured("analysis", "s", "u", X)
    assert e.value.attempts == ["ollama:a", "openrouter:b"]


async def test_reasoning_effort_only_for_gpt_oss():
    c, calls = client_with({"gpt-oss:120b": ['{"x": 1}'], "kimi": ['{"x": 1}']})
    await c.structured("analysis", "s", "u", X, reasoning_effort="medium")
    await c.structured("analysis", "s", "u", X, reasoning_effort="medium", model="openrouter:kimi")
    assert calls["gpt-oss:120b"][0]["extra_body"] == {"reasoning_effort": "medium"}
    assert "extra_body" not in calls["kimi"][0]


async def test_stream_falls_back_before_first_chunk():
    c, _ = client_with({"a": [err(openai.RateLimitError, 429)], "b": [["", "hel", "lo"]]})
    s = await c.open_stream("writer", "s", "u")
    assert s.model == "openrouter:b" and "".join([t async for t in s]) == "hello"


async def test_empty_stream_counts_as_failure():
    c, _ = client_with({"a": [[]], "b": [["ok"]]})
    s = await c.open_stream("writer", "s", "u")
    assert s.model == "openrouter:b"


async def test_override_tried_first():
    c, calls = client_with({"a": ['{"x": 1}'], "c": ['{"x": 5}']}, providers={"a": "ollama", "c": "groq"})
    r = await c.structured("analysis", "s", "u", X, model="groq:c")
    assert r.value.x == 5 and calls["a"] == []


async def test_schema_always_in_system_prompt():
    # Some OpenAI-compatible servers accept json_schema but don't enforce it; the schema must be in the prompt too.
    c, calls = client_with({"a": ['{"x": 1}']})
    await c.structured("analysis", "SYS", "u", X)
    system = calls["a"][0]["messages"][0]["content"]
    assert system.startswith("SYS") and '"x"' in system and calls["a"][0]["response_format"]["type"] == "json_schema"


async def test_structured_calls_use_a_fixed_seed():
    c, calls = client_with({"a": ['{"x": 1}']})
    await c.structured("analysis", "s", "u", X)
    assert calls["a"][0]["seed"] == 7
