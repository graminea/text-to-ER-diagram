"""Composition root for generation providers."""

from app.generations.ports import SchemaGenerator
from app.settings import Settings


def create_generator(settings: Settings) -> SchemaGenerator:
    from app.generations.adapters.llm import LLMGenerator

    return LLMGenerator(settings)
