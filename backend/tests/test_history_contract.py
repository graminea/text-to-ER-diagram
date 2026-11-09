"""HTTP and SQLite compatibility checks shared by the storage refactor."""

import json
import sqlite3
from pathlib import Path

from fastapi.testclient import TestClient

from app.entrypoints.http import create_app
from tests.support import EXAMPLE_REQUIREMENTS, FixtureGenerator, example_schema


def legacy_payload(index: int) -> dict:
    return {
        "id": f"generation-{index:02}",
        "created_at": "2026-01-01T00:00:00+00:00",
        "requirements": EXAMPLE_REQUIREMENTS,
        "provider": "mock-fixture-v1",
        "latency_ms": 1.0,
        "schema_model": example_schema(),
        "validation": {"valid": True, "issues": []},
    }


def test_history_limit_order_and_legacy_payloads(tmp_path: Path) -> None:
    db = tmp_path / "history.db"
    with TestClient(create_app(db, FixtureGenerator())) as client:
        with sqlite3.connect(db) as connection:
            # Insert out of order; timestamps tie except for the oldest record.
            for index in reversed(range(22)):
                payload = legacy_payload(index)
                if index == 21:
                    payload["created_at"] = "2025-01-01T00:00:00+00:00"
                connection.execute(
                    "INSERT INTO generations VALUES (?, ?, ?)",
                    (payload["id"], json.dumps(payload), payload["created_at"]),
                )
        response = client.get("/api/generations")
        assert response.status_code == 200
        history = response.json()
        assert [item["id"] for item in history] == [
            f"generation-{index:02}" for index in reversed(range(1, 21))
        ]
        for item in history:
            assert item["flow"] == "A"
            assert item["provider"] == "mock-fixture-v1"
            for field in (
                "model", "prompt_version", "output_mode", "input_tokens",
                "output_tokens", "call_count", "total_latency_ms", "specialist_findings",
            ):
                assert item[field] is None
        assert client.get("/api/generations/generation-20").json() == history[0]
        # Records omitted by the list limit are still individually retrievable.
        assert client.get("/api/generations/generation-21").status_code == 200


def test_empty_history_health_and_error_contracts(tmp_path: Path) -> None:
    with TestClient(create_app(tmp_path / "history.db", FixtureGenerator())) as client:
        assert client.get("/api/generations").json() == []
        missing = client.get("/api/generations/missing")
        assert missing.status_code == 404
        assert missing.json() == {"detail": "Generation not found"}
        assert client.get("/api/health").json() == {
            "status": "ok", "provider": "test-fixture", "mode": "custom", "model": None,
        }
        invalid = client.post("/api/generations", json={"requirements": "short"})
        assert invalid.status_code == 422
        assert invalid.json()["detail"][0]["loc"] == ["body", "requirements"]
