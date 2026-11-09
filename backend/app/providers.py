"""Composition root for generation providers."""

from app.generations.ports import SchemaGenerator
from app.settings import Settings


def create_generators(settings: Settings) -> tuple[SchemaGenerator, SchemaGenerator]:
    from app.generations.adapters.agents import AgentGenerator
    from app.generations.adapters.llm import LLMGenerator

    direct = LLMGenerator(settings)
    return direct, AgentGenerator(direct)
