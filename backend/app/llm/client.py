"""LLM access through an ordered chain of OpenAI-compatible providers (Ollama Cloud → OpenRouter → Groq).

Structured calls: JSON-schema response_format → json_object fallback → one repair round → next target.
Streams fall back only until the first non-empty chunk has arrived.
"""

import json
import logging
import re
import time
from collections.abc import AsyncIterator, Callable
from dataclasses import dataclass
from typing import Any, Generic, Literal, Protocol, TypeVar

import openai
from openai import AsyncOpenAI
from pydantic import BaseModel, ValidationError

log = logging.getLogger("llm")
Role = Literal["analysis", "writer"]
Effort = Literal["low", "medium", "high"]
T = TypeVar("T", bound=BaseModel)


@dataclass(frozen=True)
class Target:
    provider: str
    base_url: str
    api_key: str
    model: str

    @property
    def label(self) -> str:
        return f"{self.provider}:{self.model}"


@dataclass
class Structured(Generic[T]):
    value: T
    model: str


class LLMUnavailable(Exception):
    def __init__(self, attempts: list[str]):
        super().__init__("All LLM providers failed: " + ", ".join(attempts))
        self.attempts = attempts


class _BadOutput(Exception):
    pass


_THINK = re.compile(r"<think>.*?</think>", re.S)
_FENCE = re.compile(r"```(?:json)?\s*(.*?)```", re.S)


def extract_json(text: str) -> dict:
    text = _THINK.sub("", text or "")
    fenced = _FENCE.search(text)
    if fenced:
        text = fenced.group(1)
    start, end = text.find("{"), text.rfind("}")
    if start == -1 or end <= start:
        raise ValueError("no JSON object in model output")
    return json.loads(text[start : end + 1])


class TextStream:
    def __init__(self, model: str, first: str, rest: AsyncIterator[Any]):
        self.model = model
        self._first = first
        self._rest = rest

    async def __aiter__(self) -> AsyncIterator[str]:
        yield self._first
        async for chunk in self._rest:
            text = _delta(chunk)
            if text:
                yield text


def _delta(chunk: Any) -> str:
    choices = getattr(chunk, "choices", None) or []
    return (getattr(choices[0].delta, "content", None) or "") if choices else ""


class LLM(Protocol):
    async def structured(
        self,
        role: Role,
        system: str,
        user: str,
        schema: type[T],
        *,
        temperature: float = 0.0,
        reasoning_effort: Effort | None = None,
        model: str | None = None,
    ) -> Structured[T]: ...

    async def open_stream(
        self, role: Role, system: str, user: str, *, temperature: float = 0.4, model: str | None = None
    ) -> TextStream: ...


class LLMClient:
    def __init__(
        self,
        targets: dict[Role, list[Target]],
        timeout_s: float,
        make_client: Callable[[Target], Any] | None = None,
    ):
        self.targets = targets
        self.timeout_s = timeout_s
        self._make = make_client or self._default_client
        self._clients: dict[tuple[str, str], Any] = {}

    def _default_client(self, t: Target) -> AsyncOpenAI:
        headers = {"HTTP-Referer": "https://github.com/aayush110410/resume-customizer", "X-Title": "Resume Customizer"}
        return AsyncOpenAI(
            base_url=t.base_url,
            api_key=t.api_key,
            timeout=self.timeout_s,
            max_retries=0,
            default_headers=headers if t.provider == "openrouter" else None,
        )

    def _client(self, t: Target) -> Any:
        key = (t.base_url, t.api_key)
        if key not in self._clients:
            self._clients[key] = self._make(t)
        return self._clients[key]

    def _chain(self, role: Role, model: str | None) -> list[Target]:
        chain = list(self.targets[role])
        if model and ":" in model:
            provider, name = model.split(":", 1)
            known = next((t for ts in self.targets.values() for t in ts if t.provider == provider), None)
            if known:
                chain.insert(0, Target(provider, known.base_url, known.api_key, name))
        return chain

    async def structured(
        self,
        role: Role,
        system: str,
        user: str,
        schema: type[T],
        *,
        temperature: float = 0.0,
        reasoning_effort: Effort | None = None,
        model: str | None = None,
    ) -> Structured[T]:
        attempts = []
        for t in self._chain(role, model):
            started = time.perf_counter()
            try:
                value = await self._structured_on(t, system, user, schema, temperature, reasoning_effort)
                log.info("llm ok %s %s %.1fs", t.label, schema.__name__, time.perf_counter() - started)
                return Structured(value, t.label)
            except (openai.APIError, _BadOutput) as e:
                log.warning("llm fail %s %s: %s", t.label, schema.__name__, type(e).__name__)
                attempts.append(t.label)
        raise LLMUnavailable(attempts)

    async def _structured_on(
        self, t: Target, system: str, user: str, schema: type[T], temperature: float, effort: Effort | None
    ) -> T:
        create = self._client(t).chat.completions.create
        kwargs: dict[str, Any] = {"model": t.model, "temperature": temperature}
        if effort and "gpt-oss" in t.model:
            kwargs["extra_body"] = {"reasoning_effort": effort}
        # The schema also goes in the prompt: some OpenAI-compatible servers accept json_schema without enforcing it.
        json_schema = schema.model_json_schema()
        note = "\n\nReturn ONLY a JSON object that matches this JSON Schema exactly (same keys):\n" + json.dumps(
            json_schema
        )
        messages = [{"role": "system", "content": system + note}, {"role": "user", "content": user}]
        fmt: dict[str, Any] = {"type": "json_schema", "json_schema": {"name": schema.__name__, "schema": json_schema}}
        try:
            resp = await create(messages=messages, response_format=fmt, **kwargs)
        except openai.BadRequestError:
            fmt = {"type": "json_object"}
            resp = await create(messages=messages, response_format=fmt, **kwargs)

        content = resp.choices[0].message.content or ""
        try:
            return schema.model_validate(extract_json(content))
        except (ValueError, ValidationError) as first_error:
            repair = messages + [
                {"role": "assistant", "content": content},
                {
                    "role": "user",
                    "content": f"Your JSON failed validation: {str(first_error)[:1500]}. Return only corrected JSON.",
                },
            ]
            resp = await create(messages=repair, response_format=fmt, **kwargs)
            try:
                return schema.model_validate(extract_json(resp.choices[0].message.content or ""))
            except (ValueError, ValidationError) as e:
                raise _BadOutput(str(e)) from e

    async def open_stream(
        self, role: Role, system: str, user: str, *, temperature: float = 0.4, model: str | None = None
    ) -> TextStream:
        attempts = []
        for t in self._chain(role, model):
            try:
                stream = await self._client(t).chat.completions.create(
                    model=t.model,
                    temperature=temperature,
                    stream=True,
                    messages=[{"role": "system", "content": system}, {"role": "user", "content": user}],
                )
                it = stream.__aiter__()
                async for chunk in it:
                    first = _delta(chunk)
                    if first:
                        log.info("llm stream %s", t.label)
                        return TextStream(t.label, first, it)
                attempts.append(t.label)  # stream ended without content
            except openai.APIError as e:
                log.warning("llm stream fail %s: %s", t.label, type(e).__name__)
                attempts.append(t.label)
        raise LLMUnavailable(attempts)
