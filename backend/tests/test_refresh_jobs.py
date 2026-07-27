from __future__ import annotations

import time
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from app.api import routes
from app.database.repository import JsonRepository
from app.main import app
from app.services.refresh_jobs import RefreshAlreadyRunning, RefreshCoordinator


def wait_for_terminal(coordinator: RefreshCoordinator, timeout: float = 5) -> dict:
    deadline = time.monotonic() + timeout
    while time.monotonic() < deadline:
        job = coordinator.status()
        if job and job.get("status") in {"complete", "failed"}:
            return job
        time.sleep(0.01)
    raise AssertionError("refresh job did not finish")


def test_demo_refresh_builds_and_commits_a_usable_profile(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    repository = JsonRepository(tmp_path / "refresh.db")
    coordinator = RefreshCoordinator(repository, timeout_seconds=30)
    monkeypatch.setattr(routes, "repo", repository)

    coordinator.start({"use_demo": True, "enrich_durations": False}, routes.process_refresh)
    job = wait_for_terminal(coordinator)

    assert job["status"] == "complete"
    assert job["trackCount"] > 0
    assert job["playCount"] > 0
    assert repository.load_json("normalised")["metadata"]["play_count"] == job["playCount"]
    assert repository.load_json("analysis")["coverage"] == job["coverage"]


def test_failed_refresh_preserves_previous_profile(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    repository = JsonRepository(tmp_path / "preserve.db")
    previous = {"metadata": {"play_count": 7}, "tracks": [{"title": "Previous"}], "play_events": []}
    repository.save_json("normalised", previous)
    repository.save_json("analysis", {"top_tracks": [{"title": "Previous"}]})
    coordinator = RefreshCoordinator(repository, timeout_seconds=30)
    monkeypatch.setattr(routes, "repo", repository)
    monkeypatch.setattr(routes, "build_analysis", lambda _normalised: (_ for _ in ()).throw(RuntimeError("boom")))

    coordinator.start({"use_demo": True, "enrich_durations": False}, routes.process_refresh)
    job = wait_for_terminal(coordinator)

    assert job["status"] == "failed"
    assert job["errorCode"] == "refresh_failed"
    assert repository.load_json("normalised") == previous
    assert repository.load_json("analysis")["top_tracks"][0]["title"] == "Previous"


def test_duplicate_refresh_and_backend_restart_are_safe(tmp_path: Path) -> None:
    repository = JsonRepository(tmp_path / "restart.db")
    coordinator = RefreshCoordinator(repository, timeout_seconds=30)

    def finish_after_delay(_options: dict[str, bool], active: RefreshCoordinator, _deadline: float) -> None:
        time.sleep(0.2)
        active.stage("complete", "done")

    coordinator.start({"use_demo": True}, finish_after_delay)
    with pytest.raises(RefreshAlreadyRunning):
        coordinator.start({"use_demo": True}, lambda *_args: None)
    wait_for_terminal(coordinator)

    repository.save_json("refresh_job", {"jobId": "old", "status": "rebuilding", "progress": 78, "message": "working"})
    RefreshCoordinator(repository, timeout_seconds=30)
    recovered = repository.load_json("refresh_job")
    assert recovered["status"] == "failed"
    assert recovered["errorCode"] == "backend_restarted"


def test_refresh_endpoint_returns_job_and_status(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    repository = JsonRepository(tmp_path / "endpoint.db")
    coordinator = RefreshCoordinator(repository, timeout_seconds=30)
    monkeypatch.setattr(routes, "repo", repository)
    monkeypatch.setattr(routes, "refresh_jobs", coordinator)
    client = TestClient(app)

    queued = client.post("/api/data/refresh", json={"use_demo": True})
    assert queued.status_code == 202
    job_id = queued.json()["jobId"]

    deadline = time.monotonic() + 5
    while time.monotonic() < deadline:
        response = client.get(f"/api/data/refresh/{job_id}")
        assert response.status_code == 200
        if response.json()["status"] in {"complete", "failed"}:
            break
        time.sleep(0.01)
    assert response.json()["status"] == "complete"
    assert response.json()["progress"] == 100
