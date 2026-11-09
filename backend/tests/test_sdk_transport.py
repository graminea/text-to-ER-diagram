"""Optional SDK integration: actual request serialization, mocked HTTP, no inference."""

import json

import httpx
import pytest

from app.llm_provider import LLMGenerator
from app.provider_contract import ProviderError
from app.settings import Settings
from tests.support import EXAMPLE_REQUIREMENTS, example_schema


@pytest.mark.parametrize("status", [200, 401, 429, 500])
def test_real_sdk_uses_one_http_request_without_leaking_secrets(monkeypatch, capsys, status):
    monkeypatch.setenv("LITELLM_LOCAL_MODEL_COST_MAP", "True")
    monkeypatch.setenv("LITELLM_LOCAL_ANTHROPIC_BETA_HEADERS", "True")
    pytest.importorskip("litellm")
    requests = []

    def send(client, request, **kwargs):
        requests.append(request)
        if status != 200:
            return httpx.Response(
                status,
                request=request,
                json={"error": {"message": "test-secret private-prompt", "type": "api_error"}},
            )
        return httpx.Response(
            200,
            request=request,
            json={
                "id": "offline",
                "object": "chat.completion",
                "created": 1,
                "model": "gpt-4o-mini",
                "choices": [
                    {
                        "index": 0,
                        "finish_reason": "stop",
                        "message": {
                            "role": "assistant",
                            "content": json.dumps(example_schema()),
                        },
                    }
                ],
                "usage": {"prompt_tokens": 10, "completion_tokens": 20, "total_tokens": 30},
            },
        )

    monkeypatch.setattr(httpx.Client, "send", send)
    adapter = LLMGenerator(Settings(model="openai/gpt-4o-mini", api_key="test-secret"))
    if status == 200:
        result = adapter.generate(EXAMPLE_REQUIREMENTS)
        assert result.input_tokens == 10 and result.output_tokens == 20
    else:
        with pytest.raises(ProviderError) as caught:
            adapter.generate(EXAMPLE_REQUIREMENTS)
        assert "test-secret" not in str(caught.value)
    assert len(requests) == 1
    body = json.loads(requests[0].content)
    assert body["response_format"]["type"] == "json_schema"
    assert "test-secret" not in requests[0].content.decode()
    captured = capsys.readouterr()
    assert "test-secret" not in captured.out + captured.err


@pytest.mark.parametrize("provider", ["gemini", "anthropic"])
def test_native_provider_request_and_response_mapping(monkeypatch, provider):
    monkeypatch.setenv("LITELLM_LOCAL_MODEL_COST_MAP", "True")
    monkeypatch.setenv("LITELLM_LOCAL_ANTHROPIC_BETA_HEADERS", "True")
    pytest.importorskip("litellm")
    payload = json.dumps(example_schema())
    requests = []

    def send(client, request, **kwargs):
        requests.append(request)
        body = (
            {
                "candidates": [
                    {
                        "content": {"role": "model", "parts": [{"text": payload}]},
                        "finishReason": "STOP",
                        "index": 0,
                    }
                ],
                "usageMetadata": {
                    "promptTokenCount": 10,
                    "candidatesTokenCount": 20,
                    "totalTokenCount": 30,
                },
            }
            if provider == "gemini"
            else {
                "id": "offline",
                "type": "message",
                "role": "assistant",
                "model": "claude-sonnet-4-5-20250929",
                "content": [{"type": "text", "text": payload}],
                "stop_reason": "end_turn",
                "stop_sequence": None,
                "usage": {"input_tokens": 10, "output_tokens": 20},
            }
        )
        return httpx.Response(200, request=request, json=body)

    monkeypatch.setattr(httpx.Client, "send", send)
    model = (
        "gemini/gemini-2.5-flash"
        if provider == "gemini"
        else "anthropic/claude-sonnet-4-5-20250929"
    )
    result = LLMGenerator(Settings(model=model, api_key="test-secret")).generate(
        EXAMPLE_REQUIREMENTS
    )
    assert json.loads(result.content) == json.loads(payload)
    assert result.input_tokens == 10 and result.output_tokens == 20
    assert len(requests) == 1
