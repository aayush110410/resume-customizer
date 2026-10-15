import json

from fastapi.testclient import TestClient

from app.api.deps import get_llm
from tests.fakes import FakeLLM
from tests.test_api_analyze import sse_events
from tests.test_api_tailor import analysis_json  # noqa: F401  (fixture)

BODY = {
    "opening": "I am a software engineer at Razorpay applying for the Backend Engineer role.",
    "proof": [
        "At Razorpay I reduced p99 latency by 30% for 2M daily payments.",
        "I also ran a blockchain team of 40 engineers.",
    ],
    "motivation": "Your platform handles payments at scale.",
    "closing": "I would welcome a conversation about the role.",
}


def client(llm):
    from app.main import create_app

    app = create_app()
    app.dependency_overrides[get_llm] = lambda: llm
    return TestClient(app)


def post(llm, analysis, **extra):
    body = {"analysis": analysis, "resume": analysis["resume"]} | extra
    return sse_events(client(llm).post("/api/cover-letter", json=body))


def test_letter_is_assembled_and_checked(analysis_json):  # noqa: F811
    ev = post(FakeLLM({"LetterBody": [BODY]}), analysis_json)
    assert ev[-1][0] == "done"
    done = ev[-1][1]
    text = done["text"]
    assert "reduced p99 latency by 30% for 2M daily payments" in text
    assert "blockchain" not in text and done["letter"]["removed"]  # invented claim dropped by code
    assert text.split("\n\n")[-1].endswith("Arjun Mehta")
    assert "".join(d["text"] for e, d in ev if e == "token").strip() == text.strip()


def test_prompt_mentions_notice_period_only_when_given(analysis_json):  # noqa: F811
    with_np, without = FakeLLM({"LetterBody": [BODY]}), FakeLLM({"LetterBody": [BODY]})
    post(with_np, analysis_json, notice_period="30 days")
    post(without, analysis_json)
    assert "30 days" in with_np.prompts[0]["user"]
    assert "Do not mention notice period" in without.prompts[0]["user"]


def test_model_failure_is_an_error_event(analysis_json):  # noqa: F811
    ev = post(FakeLLM(fail=True), analysis_json)
    assert ev[-1][0] == "error"


def test_letter_facts_come_from_the_original_resume(analysis_json):  # noqa: F811
    tailored = json.loads(json.dumps(analysis_json["resume"]))
    tailored["experience"][0]["bullets"][0]["text"] = "Built Snowflake pipelines for 2M daily payments"
    body = BODY | {"proof": ["I built Snowflake pipelines for the payments team.", BODY["proof"][0]]}
    ev = sse_events(
        client(FakeLLM({"LetterBody": [body]})).post(
            "/api/cover-letter", json={"analysis": analysis_json, "resume": tailored}
        )
    )
    assert "Snowflake" not in ev[-1][1]["text"]


def test_naming_the_role_is_not_a_claim(analysis_json):  # noqa: F811
    title = analysis_json["jd"]["title"]
    body = BODY | {"opening": f"I am applying for the {title} role."}
    ev = post(FakeLLM({"LetterBody": [body]}), analysis_json)
    assert f"applying for the {title} role" in ev[-1][1]["text"]
