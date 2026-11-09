from pathlib import Path

from app.generation import GenerationRequest, GenerationService, GenerationStore
from app.offline import DEMO_REQUIREMENTS, MockGenerator
from app.persistence import GenerationRepository


def test_typed_storage_round_trip_survives_restart(tmp_path: Path) -> None:
    db = tmp_path / "nested" / "history.db"
    repository = GenerationRepository(db)
    repository.initialize()
    store: GenerationStore = repository
    service = GenerationService(MockGenerator(), store)
    result = service.generate(GenerationRequest(requirements=DEMO_REQUIREMENTS))

    restarted = GenerationRepository(db)
    restarted.initialize()
    assert restarted.get(result.id) == result
    assert restarted.list_recent() == [result]
    assert restarted.get("missing") is None
