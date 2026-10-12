from fastapi.testclient import TestClient

from app.api.deps import get_llm
from tests.fakes import FakeLLM
from tests.test_api_analyze import sse_events
from tests.test_api_tailor import analysis_json  # noqa: F401  (fixture)

LETTER = ["Dear Hiring Manager,\n\n", "I build payment APIs at scale.", "\n\nRegards,\nArjun Mehta"]


def client(llm):
    from app.main import create_app

    app = create_app()
    app.dependency_overrides[get_llm] = lambda: llm
    return TestClient(app)


def test_cover_letter_streams_tokens_then_done(analysis_json):  # noqa: F811
    llm = FakeLLM(stream=LETTER)
    ev = sse_events(
        client(llm).post("/api/cover-letter", json={"analysis": analysis_json, "resume": analysis_json["resume"]})
    )
    tokens = [d["text"] for e, d in ev if e == "token"]
    assert len(tokens) == 3 and ev[-1][0] == "done"
    assert ev[-1][1] == {"text": "".join(LETTER), "model": "fake:writer"}


def test_prompt_mentions_notice_period_only_when_given(analysis_json):  # noqa: F811
    with_np, without = FakeLLM(stream=LETTER), FakeLLM(stream=LETTER)
    body = {"analysis": analysis_json, "resume": analysis_json["resume"]}
    client(with_np).post("/api/cover-letter", json=body | {"notice_period": "30 days"})
    client(without).post("/api/cover-letter", json=body)
    assert "30 days" in with_np.prompts[0]["user"]
    assert "Do not mention notice period" in without.prompts[0]["user"]
    assert "Dear Hiring Manager" in with_np.prompts[0]["user"]  # India convention from the region pack
