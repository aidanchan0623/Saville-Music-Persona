from __future__ import annotations

import json
import sqlite3
from pathlib import Path

from app.database.repository import JsonRepository


def test_cached_json_reuses_parsed_value_until_version_changes(tmp_path: Path) -> None:
    repository = JsonRepository(tmp_path / "cache.db")
    repository.save_json("normalised", {"tracks": ["first"]})

    first = repository.load_json_cached("normalised")
    second = repository.load_json_cached("normalised")

    assert first is second

    with sqlite3.connect(repository.db_path) as conn:
        conn.execute(
            "UPDATE json_cache SET value = ?, updated_at = ? WHERE key = ?",
            (json.dumps({"tracks": ["external"]}), "2099-01-01T00:00:00+00:00", "normalised"),
        )

    refreshed = repository.load_json_cached("normalised")
    assert refreshed == {"tracks": ["external"]}
    assert refreshed is not first


def test_cached_json_tracks_batch_writes_and_deletes(tmp_path: Path) -> None:
    repository = JsonRepository(tmp_path / "batch.db")
    repository.save_json_batch({"normalised": {"version": 1}, "analysis": {"version": 1}})

    assert repository.load_json_cached("normalised") == {"version": 1}
    repository.save_json_batch({"normalised": {"version": 2}}, delete_keys=["analysis"])

    assert repository.load_json_cached("normalised") == {"version": 2}
    assert repository.load_json_cached("analysis") is None
