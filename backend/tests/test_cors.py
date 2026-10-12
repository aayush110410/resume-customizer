from fastapi.testclient import TestClient


def test_cors_allows_configured_origin_only(monkeypatch):
    monkeypatch.setenv("ALLOWED_ORIGINS", "https://rc-web.onrender.com,http://localhost:3000")
    from app.main import create_app

    client = TestClient(create_app())
    ok = client.get("/health", headers={"Origin": "https://rc-web.onrender.com"})
    assert ok.headers.get("access-control-allow-origin") == "https://rc-web.onrender.com"
    bad = client.get("/health", headers={"Origin": "https://evil.example"})
    assert "access-control-allow-origin" not in bad.headers
