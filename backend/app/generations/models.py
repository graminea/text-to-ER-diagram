from typing import Annotated, Literal

from pydantic import StringConstraints

from app.er.models import ConceptualSchema, Contract, ValidationReport


class GenerationRequest(Contract):
    requirements: Annotated[
        str, StringConstraints(strip_whitespace=True, min_length=10, max_length=10000)
    ]
    flow: Literal["A", "B"] = "A"


class Generation(Contract):
    id: str
    created_at: str
    requirements: str
    provider: str
    latency_ms: float
    schema_model: ConceptualSchema
    validation: ValidationReport
    flow: str = "A"
    model: str | None = None
    prompt_version: str | None = None
    output_mode: str | None = None
    input_tokens: int | None = None
    output_tokens: int | None = None
    call_count: int | None = None
    total_latency_ms: float | None = None
