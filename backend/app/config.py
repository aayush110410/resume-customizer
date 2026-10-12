"""Runtime settings from environment / .env, and the LLM provider chain derived from them."""

from typing import Literal

from pydantic_settings import BaseSettings, SettingsConfigDict

from app.llm.client import Target

Role = Literal["analysis", "writer"]
PROVIDERS = ("ollama", "openrouter", "groq")


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    ollama_api_key: str = ""
    ollama_base_url: str = "https://ollama.com/v1"
    ollama_analysis_models: str = "gpt-oss:120b,gpt-oss:20b"
    ollama_writer_models: str = "gpt-oss:120b,gpt-oss:20b"

    openrouter_api_key: str = ""
    openrouter_base_url: str = "https://openrouter.ai/api/v1"
    openrouter_analysis_models: str = "nvidia/nemotron-3-super-120b-a12b:free,google/gemma-4-31b-it:free"
    openrouter_writer_models: str = "nvidia/nemotron-3-super-120b-a12b:free,google/gemma-4-31b-it:free"

    groq_api_key: str = ""
    groq_base_url: str = "https://api.groq.com/openai/v1"
    groq_analysis_models: str = "openai/gpt-oss-120b"
    groq_writer_models: str = "openai/gpt-oss-120b"

    llm_provider_order: str = "ollama,openrouter,groq"
    llm_timeout_s: float = 90

    allowed_origins: str = "http://localhost:3000"
    max_upload_mb: int = 5
    max_pages: int = 5
    jd_min_chars: int = 300
    jd_max_chars: int = 20000
    rate_limit: str = "20/hour"
    export_rate_limit: str = "60/hour"
    max_request_mb: int = 8


def _split(value: str) -> list[str]:
    return [v.strip() for v in value.split(",") if v.strip()]


def build_targets(s: Settings) -> dict[Role, list[Target]]:
    targets: dict[Role, list[Target]] = {"analysis": [], "writer": []}
    for provider in _split(s.llm_provider_order):
        if provider not in PROVIDERS:
            continue
        base_url: str = getattr(s, f"{provider}_base_url")
        api_key: str = getattr(s, f"{provider}_api_key")
        if not api_key:
            if not base_url.startswith("http://localhost"):
                continue
            api_key = "ollama"
        for role in ("analysis", "writer"):
            for model in _split(getattr(s, f"{provider}_{role}_models")):
                targets[role].append(Target(provider, base_url, api_key, model))
    return targets
