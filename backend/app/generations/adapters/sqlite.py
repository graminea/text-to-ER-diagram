import sqlite3
from pathlib import Path

from app.generations.models import Generation


class GenerationRepository:
    def __init__(self, path: Path):
        self.path = path

    def initialize(self) -> None:
        self.path.parent.mkdir(parents=True, exist_ok=True)
        with sqlite3.connect(self.path) as connection:
            connection.execute(
                "CREATE TABLE IF NOT EXISTS generations "
                "(id TEXT PRIMARY KEY, payload TEXT NOT NULL, created_at TEXT NOT NULL)"
            )

    def save(self, generation: Generation) -> None:
        with sqlite3.connect(self.path) as connection:
            connection.execute(
                "INSERT INTO generations VALUES (?, ?, ?)",
                (generation.id, generation.model_dump_json(), generation.created_at),
            )

    def list_recent(self) -> list[Generation]:
        with sqlite3.connect(self.path) as connection:
            return [
                Generation.model_validate_json(row[0])
                for row in connection.execute(
                    "SELECT payload FROM generations ORDER BY created_at DESC, id DESC LIMIT 20"
                )
            ]

    def get(self, generation_id: str) -> Generation | None:
        with sqlite3.connect(self.path) as connection:
            row = connection.execute(
                "SELECT payload FROM generations WHERE id = ?", (generation_id,)
            ).fetchone()
            return Generation.model_validate_json(row[0]) if row else None
