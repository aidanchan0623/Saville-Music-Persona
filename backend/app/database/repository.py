from __future__ import annotations

import json
import sqlite3
import threading
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Callable


class JsonRepository:
    def __init__(
        self,
        db_path: Path,
        *,
        namespace_resolver: Callable[[], str | None] | None = None,
        shared_key_predicate: Callable[[str], bool] | None = None,
    ) -> None:
        self.db_path = db_path
        self.namespace_resolver = namespace_resolver
        self.shared_key_predicate = shared_key_predicate
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        self._memory_cache: dict[str, tuple[str, Any]] = {}
        self._memory_cache_lock = threading.RLock()
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
        key = self._storage_key(key)
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
        self._remember(key, value, updated_at)
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
        scoped_values = {self._storage_key(key): value for key, value in values.items()}
        scoped_delete_keys = [self._storage_key(key) for key in delete_keys or []]
        scoped_delete_prefixes = [self._storage_prefix(prefix) for prefix in delete_prefixes or []]
        rows = [
            (key, json.dumps(value, ensure_ascii=True, default=str), updated_at)
            for key, value in scoped_values.items()
        ]
        with self.connect() as conn:
            if scoped_delete_keys:
                conn.executemany("DELETE FROM json_cache WHERE key = ?", [(key,) for key in scoped_delete_keys])
            for prefix in scoped_delete_prefixes:
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
        for key in scoped_delete_keys:
            self._forget(key)
        for prefix in scoped_delete_prefixes:
            self._forget_prefix(prefix)
        for key, value in scoped_values.items():
            self._remember(key, value, updated_at)
        return updated_at

    def load_json(self, key: str) -> Any | None:
        key = self._storage_key(key)
        with self.connect() as conn:
            row = conn.execute("SELECT value FROM json_cache WHERE key = ?", (key,)).fetchone()
        if not row:
            return None
        return json.loads(row["value"])

    def load_json_cached(self, key: str) -> Any | None:
        """Reuse parsed large payloads until their persisted version changes."""
        key = self._storage_key(key)
        with self.connect() as conn:
            version_row = conn.execute("SELECT updated_at FROM json_cache WHERE key = ?", (key,)).fetchone()
        if not version_row:
            self._forget(key)
            return None
        version = str(version_row["updated_at"])
        with self._memory_cache_lock:
            cached = self._memory_cache.get(key)
            if cached and cached[0] == version:
                return cached[1]
        with self.connect() as conn:
            row = conn.execute("SELECT value, updated_at FROM json_cache WHERE key = ?", (key,)).fetchone()
        if not row:
            self._forget(key)
            return None
        value = json.loads(row["value"])
        self._remember(key, value, str(row["updated_at"]))
        return value

    def load_json_prefix(self, prefix: str) -> dict[str, Any]:
        storage_prefix = self._storage_prefix(prefix)
        with self.connect() as conn:
            rows = conn.execute(
                "SELECT key, value FROM json_cache WHERE key LIKE ? ORDER BY updated_at DESC",
                (f"{storage_prefix}%",),
            ).fetchall()
        return {self._logical_key(str(row["key"])): json.loads(row["value"]) for row in rows}

    def delete_json(self, key: str) -> None:
        key = self._storage_key(key)
        with self.connect() as conn:
            conn.execute("DELETE FROM json_cache WHERE key = ?", (key,))
        self._forget(key)

    def delete_json_many(self, keys: list[str]) -> None:
        if not keys:
            return
        keys = [self._storage_key(key) for key in keys]
        with self.connect() as conn:
            conn.executemany("DELETE FROM json_cache WHERE key = ?", [(key,) for key in keys])
        for key in keys:
            self._forget(key)

    def updated_at(self, key: str) -> str | None:
        key = self._storage_key(key)
        with self.connect() as conn:
            row = conn.execute("SELECT updated_at FROM json_cache WHERE key = ?", (key,)).fetchone()
        return row["updated_at"] if row else None

    def _remember(self, key: str, value: Any, updated_at: str) -> None:
        with self._memory_cache_lock:
            self._memory_cache[key] = (updated_at, value)

    def _forget(self, key: str) -> None:
        with self._memory_cache_lock:
            self._memory_cache.pop(key, None)

    def _forget_prefix(self, prefix: str) -> None:
        with self._memory_cache_lock:
            for key in [candidate for candidate in self._memory_cache if candidate.startswith(prefix)]:
                self._memory_cache.pop(key, None)

    def _storage_key(self, key: str) -> str:
        namespace = self.namespace_resolver() if self.namespace_resolver else None
        if not namespace or (self.shared_key_predicate and self.shared_key_predicate(key)):
            return key
        return f"{namespace}:{key}"

    def _storage_prefix(self, prefix: str) -> str:
        namespace = self.namespace_resolver() if self.namespace_resolver else None
        if not namespace or (self.shared_key_predicate and self.shared_key_predicate(prefix)):
            return prefix
        return f"{namespace}:{prefix}"

    def _logical_key(self, key: str) -> str:
        namespace = self.namespace_resolver() if self.namespace_resolver else None
        marker = f"{namespace}:" if namespace else ""
        return key.removeprefix(marker) if marker else key
