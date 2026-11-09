"""Offline tests exercise the real adapter/service with an injected API boundary."""

import json
from types import SimpleNamespace
from unittest.mock import Mock

import pytest
from fastapi.testclient import TestClient

from app.domain import ConceptualSchema
from app.llm_provider import LLMGenerator
from app.main import create_app
from app.offline import DEMO_REQUIREMENTS, MockGenerator
from app.settings import Settings


def settings(**overrides):
    return Settings(mode="llm", api_key="test-secret", **{"model": "openai/test", **overrides})


def response(content=None, finish="stop", refusal=None, usage=True):
    return SimpleNamespace(
        choices=[
            SimpleNamespace(
                finish_reason=finish,
                message=SimpleNamespace(
                    content=content
                    if content is not None
                    else json.dumps(MockGenerator().generate(DEMO_REQUIREMENTS)),
                    refusal=refusal,
                ),
            )
        ],
        usage=SimpleNamespace(prompt_tokens=120, completion_tokens=80) if usage else None,
    )


@pytest.fixture(autouse=True)
def isolated_environment(monkeypatch):
    for name in (
        "MODEL",
        "API_KEY",
        "TIMEOUT",
        "MAX_TOKENS",
        "OUTPUT_MODE",
        "API_BASE",
    ):
        monkeypatch.delenv(name, raising=False)
    monkeypatch.setenv("MODE", "mock")


@pytest.mark.parametrize("model", ["openai/test", "gemini/test", "anthropic/test", "deepseek/test"])
def test_single_call_contract_validation_and_history(tmp_path, model):
    payload = MockGenerator().generate(DEMO_REQUIREMENTS)
    # A different entity proves this is the adapter's result, not a fixture fallback.
    payload["entities"][0]["name"] = "Biblioteca"
    payload["relationships"][0]["participants"][0]["entity"] = "Biblioteca"
    transport = Mock(return_value=response(json.dumps(payload)))
    adapter = LLMGenerator(settings(model=model), transport)
    db = tmp_path / "history.db"
    with TestClient(create_app(db, adapter)) as client:
        result = client.post(
            "/api/generations", json={"requirements": "Uma biblioteca registra pedidos."}
        )
        assert result.status_code == 201
        body = result.json()
        assert body["schema_model"] == payload
        assert body["validation"]["valid"]
        assert body["flow"] == "A" and body["call_count"] == 1
        assert body["model"] == model
        assert body["input_tokens"] == 120 and body["output_tokens"] == 80
        assert body["total_latency_ms"] >= body["latency_ms"]
        assert "test-secret" not in result.text
        assert client.get("/api/health").json()["mode"] == "llm"
        assert "test-secret" not in client.get("/api/health").text
    with TestClient(create_app(db, MockGenerator())) as client:
        assert client.get(f"/api/generations/{body['id']}").json() == body
    transport.assert_called_once()
    args = transport.call_args.kwargs
    assert args["model"] == model and args["api_key"] == "test-secret"
    assert args["num_retries"] == args["max_retries"] == 0
    assert args["timeout"] == 60 and args["max_tokens"] == 4096
    assert args["drop_params"] is False
    assert args["messages"][1]["content"] == "Uma biblioteca registra pedidos."
    schema = args["response_format"]["json_schema"]["schema"]
    assert set(schema["required"]) == set(schema["properties"])
    for definition in schema["$defs"].values():
        assert set(definition["required"]) == set(definition["properties"])
    assert "test-secret" not in json.dumps(args["messages"])


@pytest.mark.parametrize(
    ("fake", "code"),
    [
        (response("not JSON"), "invalid_output"),
        (response('{"entities": []}'), "invalid_output"),
        (response(finish="length"), "truncated"),
        (response(finish="content_filter"), "refusal"),
        (response(refusal="private refusal"), "refusal"),
        (SimpleNamespace(choices=[]), "invalid_output"),
    ],
)
def test_rejected_outputs_are_not_saved_or_retried(tmp_path, fake, code):
    transport = Mock(return_value=fake)
    with TestClient(create_app(tmp_path / "db", LLMGenerator(settings(), transport))) as client:
        result = client.post("/api/generations", json={"requirements": DEMO_REQUIREMENTS})
        assert result.status_code == 502
        assert result.json()["detail"]["code"] == code
        assert "private refusal" not in result.text
        assert client.get("/api/generations").json() == []
    transport.assert_called_once()


@pytest.mark.parametrize(
    ("exception_name", "code", "status"),
    [
        ("AuthenticationError", "authentication", 502),
        ("PermissionDeniedError", "authentication", 502),
        ("RateLimitError", "rate_limit", 502),
        ("Timeout", "timeout", 504),
        ("UnsupportedParamsError", "unsupported", 502),
        ("APIConnectionError", "connection", 502),
    ],
)
def test_api_errors_are_sanitized_without_retry(tmp_path, exception_name, code, status, caplog):
    transport = Mock(side_effect=type(exception_name, (Exception,), {})("test-secret raw prompt"))
    with TestClient(create_app(tmp_path / "db", LLMGenerator(settings(), transport))) as client:
        result = client.post("/api/generations", json={"requirements": DEMO_REQUIREMENTS})
        assert result.status_code == status
        assert result.json()["detail"]["code"] == code
        assert "test-secret" not in result.text + caplog.text
        assert client.get("/api/generations").json() == []
    transport.assert_called_once()


def test_static_issues_survive_and_missing_usage_is_unknown(tmp_path):
    payload = MockGenerator().generate(DEMO_REQUIREMENTS)
    payload["relationships"][0]["participants"][0]["entity"] = "Missing"
    adapter = LLMGenerator(
        settings(), Mock(return_value=response(json.dumps(payload), usage=False))
    )
    with TestClient(create_app(tmp_path / "db", adapter)) as client:
        result = client.post("/api/generations", json={"requirements": DEMO_REQUIREMENTS}).json()
        assert result["validation"]["valid"] is False
        assert result["validation"]["issues"][0]["code"] == "unknown_entity"
        assert result["input_tokens"] is None and result["output_tokens"] is None
        assert len(client.get("/api/generations").json()) == 1


def test_explicit_json_mode_and_custom_endpoint():
    transport = Mock(return_value=response())
    LLMGenerator(
        settings(output_mode="json_object", api_base="http://localhost:1234/v1"), transport
    ).generate(DEMO_REQUIREMENTS)
    assert transport.call_args.kwargs["response_format"] == {"type": "json_object"}
    assert transport.call_args.kwargs["api_base"] == "http://localhost:1234/v1"
    assert "Contrato JSON" in transport.call_args.kwargs["messages"][0]["content"]


@pytest.mark.parametrize(
    "overrides",
    [
        {"mode": "unknown"},
        {"mode": "llm"},
        {"timeout": float("nan")},
        {"timeout": -1},
        {"max_tokens": 0},
        {"output_mode": "automatic"},
        {"api_base": "https://user:secret@example.com"},
    ],
)
def test_invalid_configuration_fails_explicitly(overrides):
    with pytest.raises(ValueError):
        Settings(**overrides)


def test_real_mode_never_falls_back_and_configuration_does_not_leak(monkeypatch, tmp_path):
    monkeypatch.setenv("MODE", "llm")
    with pytest.raises(ValueError, match="MODEL"):
        create_app(tmp_path / "db")
    assert "test-secret" not in repr(settings())


def test_old_history_payload_remains_readable(tmp_path):
    from app.generation import Generation

    old = {
        "id": "old",
        "created_at": "2026-01-01",
        "requirements": DEMO_REQUIREMENTS,
        "provider": "mock-fixture-v1",
        "latency_ms": 1.0,
        "schema_model": MockGenerator().generate(DEMO_REQUIREMENTS),
        "validation": {"valid": True, "issues": []},
    }
    result = Generation.model_validate(old)
    assert result.model is None and result.call_count is None
    assert ConceptualSchema.model_validate(result.schema_model)
