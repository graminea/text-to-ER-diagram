"""Legacy imports refer to the capability implementations, without duplicate types."""

from importlib import import_module

import pytest


@pytest.mark.parametrize(
    ("legacy", "canonical", "names"),
    [
        ("domain", "er.models", (
            "Name", "Text", "Contract", "Attribute", "Entity", "Participation",
            "Relationship", "ConceptualSchema", "Issue", "ValidationReport",
        )),
        ("validation", "er.validation", ("validate_schema",)),
        ("generation", "generations.models", ("Generation", "GenerationRequest")),
        ("generation", "generations.ports", ("GenerationStore",)),
        ("generation", "generations.service", ("GenerationService",)),
        ("provider_contract", "generations.ports", (
            "RuntimeMetadata", "ProviderOutput", "SchemaGenerator", "ProviderError",
        )),
        ("persistence", "generations.adapters.sqlite", ("GenerationRepository",)),
        ("offline", "generations.adapters.offline", ("DEMO_REQUIREMENTS", "MockGenerator")),
        ("prompts", "generations.adapters.prompts", ("PROMPT_VERSION", "SYSTEM_PROMPT")),
        ("llm_provider", "generations.adapters.llm", (
            "Completion", "LLMGenerator", "load_completion", "output_schema", "translate_error",
        )),
        ("main", "entrypoints.http", ("create_app",)),
    ],
)
def test_legacy_exports_share_identity(legacy: str, canonical: str, names: tuple[str, ...]) -> None:
    old = import_module(f"app.{legacy}")
    new = import_module(f"app.{canonical}")
    for name in names:
        assert getattr(old, name) is getattr(new, name)


def test_legacy_llm_module_keeps_loader_injection() -> None:
    assert import_module("app.llm_provider") is import_module("app.generations.adapters.llm")
