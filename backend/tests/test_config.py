from app.config import Settings, build_targets


def test_build_targets_skips_keyless_and_expands_models(monkeypatch):
    monkeypatch.setenv("OLLAMA_API_KEY", "k")
    monkeypatch.delenv("OPENROUTER_API_KEY", raising=False)
    monkeypatch.delenv("GROQ_API_KEY", raising=False)
    t = build_targets(Settings(_env_file=None))
    assert [x.model for x in t["writer"]] == ["kimi-k2.6", "minimax-m3", "gpt-oss:120b"]
    assert [x.model for x in t["analysis"]] == ["gpt-oss:120b", "minimax-m3"]
    assert all(x.provider == "ollama" and x.api_key == "k" for x in t["analysis"])


def test_build_targets_follows_order_and_local_ollama_needs_no_key(monkeypatch):
    monkeypatch.delenv("OLLAMA_API_KEY", raising=False)
    monkeypatch.setenv("OLLAMA_BASE_URL", "http://localhost:11434/v1")
    monkeypatch.setenv("OPENROUTER_API_KEY", "or")
    monkeypatch.setenv("LLM_PROVIDER_ORDER", "openrouter,ollama")
    t = build_targets(Settings(_env_file=None))
    assert [x.provider for x in t["analysis"]] == ["openrouter", "ollama", "ollama"]
    assert t["analysis"][1].api_key == "ollama"
