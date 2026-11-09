from collections.abc import AsyncIterator
from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import FastAPI, HTTPException

from app.bootstrap import build_application
from app.er.models import ConceptualSchema, ValidationReport
from app.er.validation import validate_schema
from app.generations.models import Generation, GenerationRequest
from app.generations.ports import ProviderError, RuntimeMetadata, SchemaGenerator
from app.settings import Settings


def create_app(
    db_path: Path | None = None,
    generator: SchemaGenerator | None = None,
    settings: Settings | None = None,
    *,
    runtime_metadata: RuntimeMetadata | None = None,
    agent_generator: SchemaGenerator | None = None,
) -> FastAPI:
    application = build_application(
        db_path, generator, settings,
        runtime_metadata=runtime_metadata, agent_generator=agent_generator,
    )
    service = application.service
    metadata = application.runtime_metadata

    @asynccontextmanager
    async def lifespan(_: FastAPI) -> AsyncIterator[None]:
        with application.lifespan():
            yield

    api = FastAPI(title="Text to ER", version="0.1.0", lifespan=lifespan)

    @api.get("/api/health")
    def health() -> dict[str, str | None]:
        return {
            "status": "ok",
            "provider": metadata.provider,
            "mode": metadata.mode,
            "model": metadata.model,
        }

    @api.post("/api/generations", response_model=Generation, status_code=201)
    def generate(request: GenerationRequest) -> Generation:
        try:
            return service.generate(request)
        except ProviderError as exc:
            raise HTTPException(
                status_code=504 if exc.code == "timeout" else 502,
                detail={"code": exc.code, "message": str(exc)},
            ) from None

    @api.get("/api/generations", response_model=list[Generation])
    def history() -> list[Generation]:
        return service.list_recent()

    @api.get("/api/generations/{generation_id}", response_model=Generation)
    def get_generation(generation_id: str) -> Generation:
        result = service.get(generation_id)
        if result is None:
            raise HTTPException(status_code=404, detail="Generation not found")
        return result

    @api.post("/api/validate", response_model=ValidationReport)
    def validate(schema: ConceptualSchema) -> ValidationReport:
        return validate_schema(schema)

    return api
