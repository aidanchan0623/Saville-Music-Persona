from __future__ import annotations

import json
import time
import zipfile
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from app.api import routes
from app.analysis.duration import usable_duration_seconds
from app.analysis.normalizer import normalise_collection
from app.analysis.spotify_adapter import spotify_raw_to_collection
from app.database.repository import JsonRepository
from app.main import app
from app.services.spotify_history_service import SpotifyHistoryParseError, parse_spotify_history_file
from app.services.takeout_import_jobs import TakeoutImportCoordinator


def extended_record(*, timestamp: str, title: str = "History Song", milliseconds: int = 180_000) -> dict[str, object]:
    return {
        "ts": timestamp,
        "ms_played": milliseconds,
        "master_metadata_track_name": title,
        "master_metadata_album_artist_name": "History Artist",
        "master_metadata_album_album_name": "History Album",
        "spotify_track_uri": "spotify:track:abc123",
        "episode_name": None,
        "spotify_episode_uri": None,
    }


def test_extended_zip_combines_files_and_only_deduplicates_exact_event_copies(tmp_path: Path) -> None:
    first = extended_record(timestamp="2026-07-01T10:00:00Z")
    second = extended_record(timestamp="2026-07-02T10:00:00Z")
    podcast = {
        "ts": "2026-07-03T10:00:00Z",
        "ms_played": 60_000,
        "master_metadata_track_name": None,
        "master_metadata_album_artist_name": None,
        "episode_name": "Podcast episode",
        "spotify_episode_uri": "spotify:episode:pod123",
    }
    path = tmp_path / "spotify.zip"
    with zipfile.ZipFile(path, "w") as archive:
        archive.writestr("Spotify Extended Streaming History/Streaming_History_Audio_2025.json", json.dumps([first, second]))
        archive.writestr("Spotify Extended Streaming History/Streaming_History_Audio_2026.json", json.dumps([first, podcast]))
        archive.writestr("Account/Playlist1.json", json.dumps({"name": "not history"}))

    parsed = parse_spotify_history_file(path)

    assert parsed.raw_event_count == 4
    assert len(parsed.entries) == 2
    assert parsed.diagnostics["duplicates"] == 1
    assert parsed.diagnostics["non_music_events"] == 1
    assert parsed.entries[0]["playback_seconds"] == 180


def test_legacy_streaming_history_json_is_supported(tmp_path: Path) -> None:
    path = tmp_path / "StreamingHistory_music_0.json"
    path.write_text(
        json.dumps([{"endTime": "2026-07-04 12:30", "artistName": "Legacy Artist", "trackName": "Legacy Song", "msPlayed": 90_000}]),
        encoding="utf-8",
    )

    parsed = parse_spotify_history_file(path)

    assert parsed.entries[0]["played"] == "2026-07-04T12:30:00Z"
    assert parsed.entries[0]["source_track_id"].startswith("spotify:track:local:")


def test_unrelated_json_is_rejected_as_no_usable_history(tmp_path: Path) -> None:
    path = tmp_path / "profile.json"
    path.write_text(json.dumps({"displayName": "Example"}), encoding="utf-8")
    with pytest.raises(SpotifyHistoryParseError, match="list of listening records"):
        parse_spotify_history_file(path)


def test_spotify_export_uses_actual_playback_seconds_for_minutes(tmp_path: Path) -> None:
    path = tmp_path / "history.json"
    path.write_text(json.dumps([extended_record(timestamp="2026-07-01T10:00:00Z", milliseconds=42_000)]), encoding="utf-8")
    parsed = parse_spotify_history_file(path)
    collection = spotify_raw_to_collection({"source": "spotify", "streaming_history": parsed.entries})
    normalised = normalise_collection(collection)

    event = normalised["play_events"][0]
    assert event["playback_seconds"] == 42
    assert usable_duration_seconds(event) == 42


def test_spotify_import_rebuilds_source_specific_cache(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    repository = JsonRepository(tmp_path / "spotify-import.db")
    coordinator = TakeoutImportCoordinator(
        repository,
        timeout_seconds=30,
        job_prefix="spotify_history_import_job:",
        source_label="Spotify history",
    )
    monkeypatch.setattr(routes, "repo", repository)
    path = tmp_path / "history.json"
    path.write_text(
        json.dumps(
            [
                extended_record(timestamp="2026-07-01T10:00:00Z"),
                extended_record(timestamp="2026-07-02T10:00:00Z"),
            ]
        ),
        encoding="utf-8",
    )
    coordinator.stage("spotify-test", "queued", "queued")

    routes.process_spotify_history_import("spotify-test", path, coordinator, time.monotonic() + 30)

    assert coordinator.get("spotify-test")["status"] == "complete"
    assert repository.load_json("spotify_normalised")["metadata"]["play_count"] == 2
    assert repository.load_json("spotify_analysis")["top_tracks"][0]["title"] == "History Song"
    assert repository.load_json("normalised") is None


def test_spotify_upload_endpoint_queues_and_exposes_import_status(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    repository = JsonRepository(tmp_path / "spotify-endpoint.db")
    coordinator = TakeoutImportCoordinator(
        repository,
        timeout_seconds=30,
        job_prefix="spotify_history_import_job:",
        source_label="Spotify history",
    )
    monkeypatch.setattr(routes, "repo", repository)
    monkeypatch.setattr(routes, "spotify_history_imports", coordinator)
    client = TestClient(app)
    payload = json.dumps([extended_record(timestamp="2026-07-08T11:00:00Z")]).encode()

    response = client.post(
        "/api/data/import-spotify-history",
        files={"file": ("spotify-history.json", payload, "application/json")},
    )

    assert response.status_code == 202
    job_id = response.json()["jobId"]
    deadline = time.monotonic() + 5
    while time.monotonic() < deadline:
        status_response = client.get(f"/api/data/import-spotify-history/{job_id}")
        assert status_response.status_code == 200
        job = status_response.json()
        if job["status"] in {"complete", "failed"}:
            break
        time.sleep(0.01)
    assert job["status"] == "complete"
    assert job["playCount"] == 1
