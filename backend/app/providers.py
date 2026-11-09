"""Composition root. Offline and real providers do not depend on each other."""

from app.generations.ports import SchemaGenerator
from app.settings import Settings


def create_generator(settings: Settings) -> SchemaGenerator:
    if settings.mode == "mock":
        from app.generations.adapters.offline import MockGenerator

        return MockGenerator()
    from app.generations.adapters.llm import LLMGenerator

    return LLMGenerator(settings)
