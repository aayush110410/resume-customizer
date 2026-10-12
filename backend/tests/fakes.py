"""Scripted LLM double implementing the app.llm.client.LLM protocol."""

import json

from pydantic import BaseModel

from app.llm.client import LLMUnavailable, Structured, TextStream


class FakeLLM:
    def __init__(self, responses: dict[str, list] | None = None, stream: list[str] | None = None, fail: bool = False):
        self.responses = {k: list(v) for k, v in (responses or {}).items()}
        self.stream_chunks = stream or []
        self.fail = fail
        self.prompts: list[dict] = []
        self.calls: dict[str, int] = {}

    async def structured(self, role, system, user, schema, *, temperature=0.0, reasoning_effort=None, model=None):
        name = schema.__name__
        self.prompts.append({"role": role, "system": system, "user": user, "schema": name, "model": model})
        self.calls[name] = self.calls.get(name, 0) + 1
        if self.fail or not self.responses.get(name):
            raise LLMUnavailable([f"fake:{name}"])
        item = self.responses[name].pop(0)
        if isinstance(item, BaseModel):
            item = item.model_dump()
        value = schema.model_validate(json.loads(item) if isinstance(item, str) else item)
        return Structured(value, f"fake:{role}")

    async def open_stream(self, role, system, user, *, temperature=0.4, model=None):
        self.prompts.append({"role": role, "system": system, "user": user, "schema": "stream", "model": model})
        if self.fail or not self.stream_chunks:
            raise LLMUnavailable(["fake:stream"])
        first, *rest = self.stream_chunks
        return TextStream(f"fake:{role}", first, aiter_chunks(rest))


def aiter_chunks(chunks):
    class _It:
        def __init__(self):
            self._i = iter(chunks)

        def __aiter__(self):
            return self

        async def __anext__(self):
            try:
                c = next(self._i)
            except StopIteration:
                raise StopAsyncIteration from None
            from types import SimpleNamespace

            return SimpleNamespace(choices=[SimpleNamespace(delta=SimpleNamespace(content=c))])

    return _It()
