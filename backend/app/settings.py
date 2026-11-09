"""Explicit startup configuration, independent of providers and HTTP."""

import math
import os
from dataclasses import dataclass, field
from urllib.parse import urlsplit


@dataclass(frozen=True)
class Settings:
    model: str = ""
    api_key: str = field(default="", repr=False)
    api_base: str | None = None
    timeout: float = 60
    max_tokens: int = 4096
    output_mode: str = "json_schema"

    def __post_init__(self) -> None:
        if not self.model.strip() or not self.api_key.strip():
            raise ValueError("Configure MODEL e API_KEY para gerar diagramas.")
        if self.model and (len(self.model) > 200 or any(c.isspace() for c in self.model)):
            raise ValueError("MODEL deve ser um identificador de modelo.")
        if not math.isfinite(self.timeout) or not 0 < self.timeout <= 300:
            raise ValueError("TIMEOUT deve estar entre 0 e 300 segundos.")
        if not 1 <= self.max_tokens <= 32768:
            raise ValueError("MAX_TOKENS deve estar entre 1 e 32768.")
        if self.output_mode not in {"json_schema", "json_object"}:
            raise ValueError("OUTPUT_MODE deve ser json_schema ou json_object.")
        if self.api_base:
            url = urlsplit(self.api_base)
            if (
                url.scheme not in {"http", "https"}
                or not url.hostname
                or url.username
                or url.password
            ):
                raise ValueError("API_BASE deve ser uma URL HTTP sem credenciais.")

    @classmethod
    def from_env(cls) -> "Settings":
        if os.getenv("MODE", "llm") != "llm":
            raise ValueError("Remova MODE e configure MODEL e API_KEY para gerar diagramas.")
        try:
            timeout = float(os.getenv("TIMEOUT", "60"))
            max_tokens = int(os.getenv("MAX_TOKENS", "4096"))
        except ValueError:
            raise ValueError("Timeout e limite de saída devem ser números válidos.") from None
        return cls(
            model=os.getenv("MODEL", ""),
            api_key=os.getenv("API_KEY", ""),
            api_base=os.getenv("API_BASE") or None,
            timeout=timeout,
            max_tokens=max_tokens,
            output_mode=os.getenv("OUTPUT_MODE", "json_schema"),
        )
