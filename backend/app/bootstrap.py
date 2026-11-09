"""Reusable runtime assembly and lifecycle, independent of HTTP entry points."""

import os
from collections.abc import Iterator
from contextlib import contextmanager
from dataclasses import dataclass, field
from pathlib import Path

from app.generations.adapters.sqlite import GenerationRepository
from app.generations.ports import RuntimeMetadata, SchemaGenerator
from app.generations.service import GenerationService
from app.providers import create_generator
from app.settings import Settings


@dataclass(frozen=True)
class Application:
    service: GenerationService
    runtime_metadata: RuntimeMetadata
    _repository: GenerationRepository = field(repr=False)

    @contextmanager
    def lifespan(self) -> Iterator["Application"]:
        """Initialize storage before use. SQLite connections close per operation."""
        self._repository.initialize()
        yield self


def build_application(
    db_path: Path | None = None,
    generator: SchemaGenerator | None = None,
    settings: Settings | None = None,
    *,
    runtime_metadata: RuntimeMetadata | None = None,
) -> Application:
    """Assemble without initializing storage; enter lifespan before calling services.

    An injected generator takes precedence over settings and environment selection.
    Custom generators may declare runtime_metadata or pass it explicitly here.
    Injected generators without metadata are reported as custom.
    """
    repository = GenerationRepository(db_path or Path(os.getenv("DB_PATH", "data/pilot.db")))
    selected = (
        generator if generator is not None else create_generator(settings or Settings.from_env())
    )
    if runtime_metadata is None:
        declared = getattr(selected, "runtime_metadata", None)
        runtime_metadata = (
            declared if isinstance(declared, RuntimeMetadata)
            else RuntimeMetadata(provider=selected.name, mode="custom")
        )
    return Application(GenerationService(selected, repository), runtime_metadata, repository)
