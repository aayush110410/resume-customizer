"""LLM access through an ordered chain of OpenAI-compatible providers."""

from dataclasses import dataclass


@dataclass(frozen=True)
class Target:
    provider: str
    base_url: str
    api_key: str
    model: str
