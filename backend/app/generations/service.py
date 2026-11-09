from datetime import UTC, datetime
from time import perf_counter
from uuid import uuid4

from pydantic import ValidationError

from app.er.models import ConceptualSchema
from app.er.validation import validate_schema
from app.generations.models import Generation, GenerationRequest
from app.generations.ports import GenerationStore, ProviderError, ProviderOutput, SchemaGenerator


class GenerationService:
    def __init__(
        self,
        generator: SchemaGenerator,
        repository: GenerationStore,
        *,
        agent_generator: SchemaGenerator | None = None,
    ):
        self.generator = generator
        self.agent_generator = agent_generator
        self.repository = repository

    def list_recent(self) -> list[Generation]:
        return self.repository.list_recent()

    def get(self, generation_id: str) -> Generation | None:
        return self.repository.get(generation_id)

    def generate(self, request: GenerationRequest) -> Generation:
        generator = self.agent_generator if request.flow == "B" else self.generator
        if generator is None:
            raise ProviderError("unsupported")
        start = perf_counter()
        try:
            raw = generator.generate(request.requirements)
            output = raw if isinstance(raw, ProviderOutput) else None
            content = output.content if output else raw
            schema = (
                ConceptualSchema.model_validate_json(content)
                if isinstance(content, str)
                else ConceptualSchema.model_validate(content)
            )
        except ProviderError:
            raise
        except (ValidationError, ValueError, TypeError, RuntimeError, TimeoutError) as exc:
            # Never expose raw output, prompts, credentials or SDK details to the client.
            code = "timeout" if isinstance(exc, TimeoutError) else "invalid_output"
            raise ProviderError(code) from None
        result = Generation(
            id=str(uuid4()),
            created_at=datetime.now(UTC).isoformat(),
            requirements=request.requirements,
            provider=generator.name,
            latency_ms=round((perf_counter() - start) * 1000, 3),
            schema_model=schema,
            validation=validate_schema(schema),
            flow=request.flow,
            model=output.model if output else None,
            prompt_version=output.prompt_version if output else None,
            output_mode=output.output_mode if output else None,
            input_tokens=output.input_tokens if output else None,
            output_tokens=output.output_tokens if output else None,
            call_count=output.call_count if output else None,
            total_latency_ms=round((perf_counter() - start) * 1000, 3),
            specialist_findings=output.specialist_findings if output else None,
        )
        # Structurally invalid, parseable results are retained with their issues.
        self.repository.save(result)
        return result
