"""Provider-independent boundary; importing it never imports an LLM SDK."""

from dataclasses import dataclass
from typing import Literal, Protocol

from app.generations.models import Generation


@dataclass(frozen=True)
class RuntimeMetadata:
    """Public runtime identity only; never includes provider configuration or secrets."""

    provider: str
    mode: Literal["custom", "llm"]
    model: str | None = None


@dataclass(frozen=True)
class ProviderOutput:
    content: object
    model: str
    prompt_version: str
    input_tokens: int | None = None
    output_tokens: int | None = None
    call_count: int = 1
    output_mode: str | None = None


class SchemaGenerator(Protocol):
    name: str

    def generate(self, requirements: str) -> object:
        """Return untrusted data; parsing and ER validation belong to the service."""
        ...


class ProviderError(Exception):
    """Only fixed, public messages may cross the provider boundary."""

    def __init__(self, code: str = "provider_error"):
        messages = {
            "authentication": "Chave ou permissões rejeitadas. Verifique o provedor.",
            "rate_limit": "Limite de uso atingido. Verifique sua cota e tente novamente.",
            "timeout": "O provedor demorou demais para responder. Tente novamente.",
            "unsupported": "Configuração não suportada. Verifique o modelo e o formato de saída.",
            "refusal": "O provedor recusou a geração. Revise os requisitos e tente novamente.",
            "truncated": "A resposta ficou incompleta. Aumente o limite de saída no backend.",
            "invalid_output": "Resposta fora do contrato ER. Tente novamente.",
            "connection": (
                "Não foi possível conectar ao provedor. Confira a conexão e tente novamente."
            ),
            "provider_unavailable": (
                "O provedor está indisponível. Tente novamente em alguns minutos."
            ),
        }
        self.code = code
        super().__init__(messages.get(code, "Não foi possível gerar o modelo ER. Tente novamente."))


class GenerationStore(Protocol):
    """Typed application boundary; adapters own serialization and storage lifecycle."""

    def save(self, generation: Generation) -> None: ...

    def list_recent(self) -> list[Generation]:
        """Return at most 20 records ordered by created_at DESC, then id DESC."""
        ...

    def get(self, generation_id: str) -> Generation | None: ...
