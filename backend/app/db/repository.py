import json
import sqlite3
from pathlib import Path

from app.models.schemas import RunResult


class RunRepository:
    def __init__(self, database_path: str, jsonl_path: str) -> None:
        self.database_path = Path(database_path)
        self.jsonl_path = Path(jsonl_path)
        self.database_path.parent.mkdir(parents=True, exist_ok=True)
        self.jsonl_path.parent.mkdir(parents=True, exist_ok=True)
        self._init()

    def _connect(self) -> sqlite3.Connection:
        conn = sqlite3.connect(self.database_path)
        conn.row_factory = sqlite3.Row
        return conn

    def _init(self) -> None:
        with self._connect() as conn:
            conn.execute(
                """
                CREATE TABLE IF NOT EXISTS runs (
                    id TEXT PRIMARY KEY,
                    created_at TEXT NOT NULL,
                    prompt TEXT NOT NULL,
                    provider TEXT NOT NULL,
                    payload TEXT NOT NULL
                )
                """
            )

    def save(self, run: RunResult) -> RunResult:
        payload = run.model_dump_json()
        with self._connect() as conn:
            conn.execute(
                """
                INSERT INTO runs (id, created_at, prompt, provider, payload)
                VALUES (?, ?, ?, ?, ?)
                """,
                (run.id, run.created_at.isoformat(), run.prompt, run.provider, payload),
            )
        with self.jsonl_path.open("a", encoding="utf-8") as handle:
            handle.write(payload + "\n")
        return run

    def list(self) -> list[RunResult]:
        with self._connect() as conn:
            rows = conn.execute(
                "SELECT payload FROM runs ORDER BY created_at DESC LIMIT 50"
            ).fetchall()
        return [RunResult.model_validate(json.loads(row["payload"])) for row in rows]

    def get(self, run_id: str) -> RunResult | None:
        with self._connect() as conn:
            row = conn.execute("SELECT payload FROM runs WHERE id = ?", (run_id,)).fetchone()
        return RunResult.model_validate(json.loads(row["payload"])) if row else None
