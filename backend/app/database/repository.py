from __future__ import annotations

import json
import sqlite3
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


class JsonRepository:
    def __init__(self, db_path: Path) -> None:
        self.db_path = db_path
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        self.initialise()

    def connect(self) -> sqlite3.Connection:
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        return conn

    def initialise(self) -> None:
        with self.connect() as conn:
            conn.execute(
                """
                CREATE TABLE IF NOT EXISTS json_cache (
                    key TEXT PRIMARY KEY,
                    value TEXT NOT NULL,
                    updated_at TEXT NOT NULL
                )
                """
            )

    def save_json(self, key: str, value: Any) -> str:
        updated_at = datetime.now(timezone.utc).isoformat()
        payload = json.dumps(value, ensure_ascii=True, default=str)
        with self.connect() as conn:
            conn.execute(
                """
                INSERT INTO json_cache(key, value, updated_at)
                VALUES (?, ?, ?)
                ON CONFLICT(key) DO UPDATE SET
                    value = excluded.value,
                    updated_at = excluded.updated_at
                """,
                (key, payload, updated_at),
            )
        return updated_at

    def save_json_batch(
        self,
        values: dict[str, Any],
        *,
        delete_keys: list[str] | None = None,
        delete_prefixes: list[str] | None = None,
    ) -> str:
        """Commit related cache values and invalidations in one transaction."""
        updated_at = datetime.now(timezone.utc).isoformat()
        rows = [
            (key, json.dumps(value, ensure_ascii=True, default=str), updated_at)
            for key, value in values.items()
        ]
        with self.connect() as conn:
            if delete_keys:
                conn.executemany("DELETE FROM json_cache WHERE key = ?", [(key,) for key in delete_keys])
            for prefix in delete_prefixes or []:
                conn.execute("DELETE FROM json_cache WHERE key LIKE ?", (f"{prefix}%",))
            conn.executemany(
                """
                INSERT INTO json_cache(key, value, updated_at)
                VALUES (?, ?, ?)
                ON CONFLICT(key) DO UPDATE SET
                    value = excluded.value,
                    updated_at = excluded.updated_at
                """,
                rows,
            )
        return updated_at

    def load_json(self, key: str) -> Any | None:
        with self.connect() as conn:
            row = conn.execute("SELECT value FROM json_cache WHERE key = ?", (key,)).fetchone()
        if not row:
            return None
        return json.loads(row["value"])

    def load_json_prefix(self, prefix: str) -> dict[str, Any]:
        with self.connect() as conn:
            rows = conn.execute(
                "SELECT key, value FROM json_cache WHERE key LIKE ? ORDER BY updated_at DESC",
                (f"{prefix}%",),
            ).fetchall()
        return {row["key"]: json.loads(row["value"]) for row in rows}

    def delete_json(self, key: str) -> None:
        with self.connect() as conn:
            conn.execute("DELETE FROM json_cache WHERE key = ?", (key,))

    def delete_json_many(self, keys: list[str]) -> None:
        if not keys:
            return
        with self.connect() as conn:
            conn.executemany("DELETE FROM json_cache WHERE key = ?", [(key,) for key in keys])

    def updated_at(self, key: str) -> str | None:
        with self.connect() as conn:
            row = conn.execute("SELECT updated_at FROM json_cache WHERE key = ?", (key,)).fetchone()
        return row["updated_at"] if row else None
