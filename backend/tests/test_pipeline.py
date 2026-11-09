from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from app.domain import ConceptualSchema
from app.main import create_app
from app.offline import DEMO_REQUIREMENTS, MockGenerator
from app.validation import validate_schema


def fixture_schema() -> dict:
    return MockGenerator().generate(DEMO_REQUIREMENTS)


def test_generation_history_survives_restart(tmp_path: Path) -> None:
    db = tmp_path / "test.db"
    with TestClient(create_app(db)) as client:
        result = client.post("/api/generations", json={"requirements": DEMO_REQUIREMENTS})
        assert result.status_code == 201
        payload = result.json()
        assert payload["validation"] == {"valid": True, "issues": []}
        assert payload["provider"] == "mock-fixture-v1"
        assert len(payload["schema_model"]["entities"]) == 2
    with TestClient(create_app(db)) as client:
        assert client.get("/api/generations").json() == [payload]
        assert client.get(f"/api/generations/{payload['id']}").json() == payload
        assert client.get("/api/generations/unknown").status_code == 404


@pytest.mark.parametrize("requirements", [" ", "short", "x" * 10001, 123, None])
def test_invalid_requirements(tmp_path: Path, requirements: object) -> None:
    with TestClient(create_app(tmp_path / "test.db")) as client:
        response = client.post("/api/generations", json={"requirements": requirements})
        assert response.status_code == 422
        assert client.get("/api/generations").json() == []


def test_mock_does_not_claim_to_understand_other_inputs(tmp_path: Path) -> None:
    with TestClient(create_app(tmp_path / "test.db")) as client:
        payload = client.post(
            "/api/generations", json={"requirements": "Uma biblioteca tem livros e autores."}
        ).json()
        assert payload["validation"]["valid"]
        assert payload["validation"]["issues"][0]["code"] == "unresolved_ambiguity"


def test_structural_issues_are_actionable() -> None:
    raw = fixture_schema()
    raw["entities"][1]["attributes"][0]["is_identifier"] = False
    raw["entities"][0]["attributes"].append(raw["entities"][0]["attributes"][0])
    raw["relationships"][0]["participants"][1]["entity"] = "Missing"
    report = validate_schema(ConceptualSchema.model_validate(raw))
    assert not report.valid
    assert {i.code for i in report.issues} == {
        "duplicate_name",
        "missing_identifier",
        "unknown_entity",
    }
    assert all(i.path for i in report.issues)


def test_names_are_unique_ignoring_case() -> None:
    raw = fixture_schema()
    raw["entities"][1]["name"] = "cliente"
    raw["relationships"][0]["participants"][1]["role"] = "COMPRADOR"
    codes = [i.code for i in validate_schema(ConceptualSchema.model_validate(raw)).issues]
    assert codes.count("duplicate_name") == 2


@pytest.mark.parametrize("value", [0, 2, -1, True, "1", "many"])
def test_cardinality_is_restricted(tmp_path: Path, value: object) -> None:
    raw = fixture_schema()
    raw["relationships"][0]["participants"][0]["max_cardinality"] = value
    with TestClient(create_app(tmp_path / "test.db")) as client:
        assert client.post("/api/validate", json=raw).status_code == 422


def test_binary_relationships_and_unknown_fields(tmp_path: Path) -> None:
    raw = fixture_schema()
    raw["relationships"][0]["participants"].pop()
    with TestClient(create_app(tmp_path / "test.db")) as client:
        assert client.post("/api/validate", json=raw).status_code == 422
        assert (
            client.post(
                "/api/generations", json={"requirements": DEMO_REQUIREMENTS, "execute_sql": True}
            ).status_code
            == 422
        )


def test_recursive_relationship_requires_distinct_roles() -> None:
    raw = fixture_schema()
    raw["relationships"][0]["participants"][1]["entity"] = "Cliente"
    assert validate_schema(ConceptualSchema.model_validate(raw)).valid


def test_untrusted_generator_output_is_rejected(tmp_path: Path) -> None:
    class BrokenGenerator:
        name = "broken"

        def generate(self, requirements: str) -> object:
            return {"secret": "must-not-leak"}

    with TestClient(create_app(tmp_path / "test.db", BrokenGenerator())) as client:
        response = client.post("/api/generations", json={"requirements": DEMO_REQUIREMENTS})
        assert response.status_code == 502
        assert "must-not-leak" not in response.text
        assert client.get("/api/generations").json() == []


def test_provider_failure_is_sanitized(tmp_path: Path) -> None:
    class OfflineGenerator:
        name = "offline"

        def generate(self, requirements: str) -> object:
            raise TimeoutError("secret-key")

    with TestClient(create_app(tmp_path / "test.db", OfflineGenerator())) as client:
        response = client.post("/api/generations", json={"requirements": DEMO_REQUIREMENTS})
        assert response.status_code == 504
        assert "secret-key" not in response.text


def test_parseable_invalid_output_is_saved_with_report(tmp_path: Path) -> None:
    class InvalidGenerator:
        name = "invalid"

        def generate(self, requirements: str) -> object:
            raw = fixture_schema()
            raw["relationships"][0]["participants"][0]["entity"] = "Ghost"
            return raw

    with TestClient(create_app(tmp_path / "test.db", InvalidGenerator())) as client:
        payload = client.post("/api/generations", json={"requirements": DEMO_REQUIREMENTS}).json()
        assert not payload["validation"]["valid"]
        assert payload["validation"]["issues"][0]["code"] == "unknown_entity"
        assert len(client.get("/api/generations").json()) == 1
