from fastapi import Request

from app.cache import AsyncLRU
from app.config import Settings
from app.knowledge.loader import load_knowledge
from app.knowledge.models import Knowledge
from app.llm.client import LLM


def get_llm(request: Request) -> LLM:
    return request.app.state.llm


def get_kb() -> Knowledge:
    return load_knowledge()


def get_settings(request: Request) -> Settings:
    return request.app.state.settings


def get_cache(request: Request) -> AsyncLRU:
    return request.app.state.cache


def rate_limited(request: Request) -> None:
    request.app.state.limiter.check(request)
