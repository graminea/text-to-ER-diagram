"""Application use cases exercised without HTTP or SQLite."""

import pytest

from app.generation import Generation, GenerationRequest, GenerationService, GenerationStore
from app.provider_contract import ProviderError
from tests.support import EXAMPLE_REQUIREMENTS, FixtureGenerator, example_schema


class MemoryStore:
    def __init__(self) -> None:
        self.records: dict[str, Generation] = {}

    def save(self, generation: Generation) -> None:
        self.records[generation.id] = generation

    def list_recent(self) -> list[Generation]:
        return sorted(
            self.records.values(), key=lambda item: (item.created_at, item.id), reverse=True
        )[:20]

    def get(self, generation_id: str) -> Generation | None:
        return self.records.get(generation_id)


def test_generate_and_retrieve_without_http_or_database() -> None:
    store: GenerationStore = MemoryStore()
    service = GenerationService(FixtureGenerator(), store)
    assert service.list_recent() == []
    assert service.get("missing") is None
    result = service.generate(GenerationRequest(requirements=EXAMPLE_REQUIREMENTS))
    assert result.validation.valid
    assert result.requirements == EXAMPLE_REQUIREMENTS
    assert result.provider == "test-fixture"
    assert result.id and result.created_at
    assert result.total_latency_ms >= result.latency_ms
    assert service.get(result.id) == result
    assert service.list_recent() == [result]


@pytest.mark.parametrize("failure", ["parse", "contract", "timeout", "provider"])
def test_rejected_generation_is_not_saved(failure: str) -> None:
    class Generator:
        name = "test"

        def generate(self, requirements: str) -> object:
            if failure == "timeout":
                raise TimeoutError("private-data")
            if failure == "provider":
                raise ProviderError("rate_limit")
            return "not JSON" if failure == "parse" else {"private-data": True}

    service = GenerationService(Generator(), MemoryStore())
    with pytest.raises(ProviderError) as caught:
        service.generate(GenerationRequest(requirements=EXAMPLE_REQUIREMENTS))
    expected = {"timeout": "timeout", "provider": "rate_limit"}.get(failure, "invalid_output")
    assert caught.value.code == expected
    assert "private-data" not in str(caught.value)
    assert service.list_recent() == []


def test_structurally_invalid_generation_is_saved_with_report() -> None:
    class Generator:
        name = "test"

        def generate(self, requirements: str) -> object:
            raw = example_schema()
            raw["relationships"][0]["participants"][0]["entity"] = "Missing"
            raw["assumptions"] = ["Preserved assumption"]
            raw["ambiguities"] = ["Preserved ambiguity"]
            return raw

    service = GenerationService(Generator(), MemoryStore())
    result = service.generate(GenerationRequest(requirements=EXAMPLE_REQUIREMENTS))
    assert not result.validation.valid
    assert {issue.code for issue in result.validation.issues} == {
        "unknown_entity", "unresolved_ambiguity",
    }
    assert result.schema_model.assumptions == ["Preserved assumption"]
    assert result.schema_model.ambiguities == ["Preserved ambiguity"]
    assert service.get(result.id) == result
