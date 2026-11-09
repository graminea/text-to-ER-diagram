import json

import pytest
from fastapi.testclient import TestClient

from app.entrypoints.http import create_app
from app.settings import Settings
from tests.support import EXAMPLE_REQUIREMENTS, example_schema, response


def test_agent_flow_revises_draft_and_saves_only_the_final_model(monkeypatch, tmp_path, caplog):
    caplog.set_level("INFO", logger="uvicorn.error.er_agents")
    draft = example_schema()
    draft["relationships"][0]["participants"][0]["max_cardinality"] = 1
    expected = example_schema()
    findings = {
        "consistency": ["O texto sustenta Cliente e Pedido."],
        "cardinality": ["“vários pedidos” sustenta max_cardinality N no papel comprador."],
    }
    requests = []

    def complete(**request):
        requests.append(request)
        schema = request["response_format"]["json_schema"]
        messages = request["messages"]
        content = messages[1]["content"]
        if schema["name"] == "er_review":
            assert json.loads(content) == {"requirements": EXAMPLE_REQUIREMENTS, "draft": draft}
            role = "cardinality" if "limites mínimo e máximo" in messages[0]["content"] else (
                "consistency"
            )
            return response(json.dumps({"findings": findings[role]}))
        if content == EXAMPLE_REQUIREMENTS:
            return response(json.dumps(draft))
        assert json.loads(content) == {
            "requirements": EXAMPLE_REQUIREMENTS, "draft": draft, "reviews": findings,
        }
        return response(json.dumps(expected))

    monkeypatch.setattr("app.llm_provider.load_completion", lambda: complete)
    settings = Settings(model="openai/test", api_key="test-only")
    with TestClient(create_app(tmp_path / "history.db", settings=settings)) as client:
        result = client.post(
            "/api/generations", json={"requirements": EXAMPLE_REQUIREMENTS, "flow": "B"}
        )
        assert result.status_code == 201
        body = result.json()
        assert body["schema_model"] == expected
        assert body["validation"] == {"valid": True, "issues": []}
        assert body["flow"] == "B" and body["call_count"] == 4
        assert body["prompt_version"] == "er-agents-v1"
        assert body["input_tokens"] == 480 and body["output_tokens"] == 320
        assert client.get("/api/generations").json() == [body]
        assert client.get(f"/api/generations/{body['id']}").json() == body
    assert len(requests) == 4
    assert 0 < requests[-1]["timeout"] <= requests[0]["timeout"] <= settings.timeout
    calls = [
        dict(field.split("=", 1) for field in record.getMessage().split()[1:])
        for record in caplog.records if record.name == "uvicorn.error.er_agents"
    ]
    assert len(calls) == 4
    assert len({call["run_id"] for call in calls}) == 1
    assert {call["stage"] for call in calls} == {
        "coordinator.draft", "consistency.review", "cardinality.review", "coordinator.final",
    }
    assert all(call["outcome"] == "response" for call in calls)
    assert all(call["input_tokens"] == "120" and call["output_tokens"] == "80" for call in calls)
    assert EXAMPLE_REQUIREMENTS not in caplog.text
    assert "test-only" not in caplog.text
    assert all(finding[0] not in caplog.text for finding in findings.values())


@pytest.mark.parametrize(
    ("failed_stage", "expected_calls"),
    [("draft", 1), ("review", 3), ("final", 4), ("refusal", 1)],
)
def test_invalid_agent_output_is_sanitized_without_saving(
    monkeypatch, tmp_path, caplog, failed_stage, expected_calls,
):
    stages = []

    def complete(**request):
        schema = request["response_format"]["json_schema"]
        if schema["name"] == "er_review":
            stage = "review"
            payload = {"findings": []}
        else:
            content = request["messages"][1]["content"]
            stage = "draft" if content == EXAMPLE_REQUIREMENTS else "final"
            payload = example_schema()
        stages.append(stage)
        if failed_stage == "refusal":
            return response(refusal="private provider output")
        return response("private provider output" if stage == failed_stage else json.dumps(payload))

    monkeypatch.setattr("app.llm_provider.load_completion", lambda: complete)
    with TestClient(create_app(
        tmp_path / "history.db", settings=Settings(model="openai/test", api_key="test-only"),
    )) as client:
        result = client.post(
            "/api/generations", json={"requirements": EXAMPLE_REQUIREMENTS, "flow": "B"}
        )
        assert result.status_code == 502
        code = "refusal" if failed_stage == "refusal" else "invalid_output"
        assert result.json()["detail"]["code"] == code
        assert "private provider output" not in result.text + caplog.text
        assert client.get("/api/generations").json() == []
    assert len(stages) == expected_calls
    if failed_stage == "refusal":
        assert "stage=coordinator.draft outcome=error" in caplog.text
        assert "code=refusal" in caplog.text
