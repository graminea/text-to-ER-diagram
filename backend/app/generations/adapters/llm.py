"""Single-call LiteLLM transport and direct ER generator."""

import importlib
import json
import logging
import os
from collections.abc import Callable
from typing import Any

from app.er.models import ConceptualSchema, Contract
from app.generations.adapters.prompts import PROMPT_VERSION, SYSTEM_PROMPT
from app.generations.ports import ProviderError, ProviderOutput, RuntimeMetadata
from app.settings import Settings

Completion = Callable[..., Any]
logger = logging.getLogger("app.llm_provider")


def output_schema(contract: type[Contract] = ConceptualSchema) -> dict[str, Any]:
    """Provider strict schemas require every property, including defaulted fields."""
    schema = contract.model_json_schema()

    def visit(node: Any) -> None:
        if isinstance(node, dict):
            node.pop("default", None)
            if "properties" in node:
                node["required"] = list(node["properties"])
                node["additionalProperties"] = False
            for child in node.values():
                visit(child)
        elif isinstance(node, list):
            for child in node:
                visit(child)

    visit(schema)
    return schema


def load_completion() -> Completion:
    # Avoid fetching SDK pricing metadata or logging request/response content.
    os.environ["LITELLM_LOCAL_MODEL_COST_MAP"] = "True"
    os.environ["LITELLM_LOCAL_ANTHROPIC_BETA_HEADERS"] = "True"
    try:
        sdk: Any = importlib.import_module("litellm")
    except ImportError:
        raise ValueError("Instale o extra llm do backend para usar geração real.") from None
    sdk.suppress_debug_info = True
    sdk.turn_off_message_logging = True
    sdk.set_verbose = False
    sdk.num_retries = 0
    return sdk.completion  # type: ignore[no-any-return]


def translate_error(exc: Exception) -> ProviderError:
    # SDK exception messages can contain prompts, headers and credentials. Never forward them.
    names = {cls.__name__ for cls in type(exc).__mro__}
    if names & {"ContentPolicyViolationError"}:
        return ProviderError("refusal")
    if names & {"AuthenticationError", "PermissionDeniedError"}:
        return ProviderError("authentication")
    if names & {"RateLimitError", "PaymentRequiredError"}:
        return ProviderError("rate_limit")
    if names & {"Timeout", "TimeoutError", "APITimeoutError"}:
        return ProviderError("timeout")
    if names & {"BadRequestError", "UnsupportedParamsError", "NotFoundError"}:
        return ProviderError("unsupported")
    if names & {"APIConnectionError", "ConnectError", "ConnectTimeout", "NetworkError"}:
        return ProviderError("connection")
    if names & {"InternalServerError", "ServiceUnavailableError", "APIStatusError"}:
        return ProviderError("provider_unavailable")
    return ProviderError()


class LLMGenerator:
    name = "litellm"

    def __init__(self, settings: Settings, completion: Completion | None = None):
        self.settings = settings
        self.completion = completion if completion is not None else load_completion()

    @property
    def runtime_metadata(self) -> RuntimeMetadata:
        return RuntimeMetadata(provider=self.name, mode="llm", model=self.settings.model)

    def generate(self, requirements: str) -> ProviderOutput:
        return self.complete(requirements, instructions=SYSTEM_PROMPT)

    def complete(
        self,
        user_input: str,
        *,
        instructions: str,
        contract: type[Contract] = ConceptualSchema,
        schema_name: str = "conceptual_er",
        timeout: float | None = None,
    ) -> ProviderOutput:
        schema = output_schema(contract)
        response_format: dict[str, object] = {"type": self.settings.output_mode}
        if self.settings.output_mode == "json_schema":
            response_format["json_schema"] = {
                "name": schema_name,
                "strict": True,
                "schema": schema,
            }
        kwargs: dict[str, Any] = {
            "model": self.settings.model,
            "api_key": self.settings.api_key,
            "messages": [
                {
                    "role": "system",
                    "content": instructions + "\nContrato JSON:\n" + json.dumps(schema),
                },
                {"role": "user", "content": user_input},
            ],
            "response_format": response_format,
            "timeout": self.settings.timeout if timeout is None else timeout,
            "max_tokens": self.settings.max_tokens,
            "num_retries": 0,
            "max_retries": 0,
            "stream": False,
            "drop_params": False,
        }
        if self.settings.api_base:
            kwargs["api_base"] = self.settings.api_base
        try:
            response = self.completion(**kwargs)
        except Exception as exc:
            status = getattr(exc, "status_code", None)
            safe_status = status if type(status) is int and 400 <= status <= 599 else None
            # Provider exception messages may contain prompts, response bodies or credentials.
            logger.warning(
                "LLM request failed: exception_type=%s http_status=%s",
                type(exc).__name__,
                safe_status if safe_status is not None else "unknown",
            )
            raise translate_error(exc) from None
        try:
            choice = response.choices[0]
            if getattr(choice.message, "refusal", None) or choice.finish_reason == "content_filter":
                raise ProviderError("refusal")
            if choice.finish_reason in {"length", "max_tokens"}:
                raise ProviderError("truncated")
            if choice.finish_reason != "stop" or not isinstance(choice.message.content, str):
                raise ProviderError("invalid_output")
            usage = getattr(response, "usage", None)

            def tokens(name: str) -> int | None:
                value = getattr(usage, name, None)
                return value if type(value) is int and value >= 0 else None

            return ProviderOutput(
                content=choice.message.content,
                model=self.settings.model,
                prompt_version=PROMPT_VERSION,
                input_tokens=tokens("prompt_tokens"),
                output_tokens=tokens("completion_tokens"),
                output_mode=self.settings.output_mode,
            )
        except ProviderError:
            raise
        except (AttributeError, IndexError, TypeError):
            raise ProviderError("invalid_output") from None
