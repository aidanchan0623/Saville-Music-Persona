from __future__ import annotations

import time
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from app.api import routes
from app.database.repository import JsonRepository
from app.main import app
from app.services.takeout_import_jobs import TakeoutImportAlreadyRunning, TakeoutImportCoordinator
from app.session import current_session_namespace, is_shared_cache_key, session_scope


def anonymous_repository(path: Path) -> JsonRepository:
    return JsonRepository(
        path,
        namespace_resolver=current_session_namespace,
        shared_key_predicate=is_shared_cache_key,
    )


def test_anonymous_middleware_issues_isolated_http_only_sessions(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    repository = anonymous_repository(tmp_path / "sessions.db")
    monkeypatch.setattr(routes, "repo", repository)
    monkeypatch.setattr(routes.settings, "deployment_mode", "anonymous")
    monkeypatch.setattr(routes.settings, "session_cookie_secure", False)

    first = TestClient(app)
    second = TestClient(app)
    first_status = first.get("/api/session")
    second_status = second.get("/api/session")

    assert first_status.status_code == 200
    assert first_status.json()["anonymous"] is True
    assert first_status.json()["accountConnectionsEnabled"] is False
    assert "httponly" in first_status.headers["set-cookie"].casefold()
    assert first.cookies.get(routes.settings.session_cookie_name) != second.cookies.get(routes.settings.session_cookie_name)
    assert first.post("/api/auth/setup").status_code == 403
    assert first.post("/api/auth/setup", headers={"Origin": "https://untrusted.example"}).json()["code"] == "origin_not_allowed"
    assert first.get("/api/spotify/login", follow_redirects=False).status_code == 403
    assert first.get("/api/auth/status").json()["auth_file_path"] == ""


def test_import_worker_keeps_the_request_session_context(tmp_path: Path) -> None:
    repository = anonymous_repository(tmp_path / "worker.db")
    coordinator = TakeoutImportCoordinator(repository, timeout_seconds=10)
    upload = tmp_path / "upload.json"
    upload.write_text("[]", encoding="utf-8")
    session_id = "c" * 64

    def processor(job_id: str, _path: Path, active: TakeoutImportCoordinator, _deadline: float) -> None:
        repository.save_json("normalised", {"session": session_id})
        active.stage(job_id, "complete", "done")

    with session_scope(session_id):
        job_id = coordinator.reserve("json")
        coordinator.queue(job_id, upload, upload.stat().st_size, processor)
        deadline = time.monotonic() + 3
        while time.monotonic() < deadline:
            job = coordinator.get(job_id)
            if job and job["status"] == "complete":
                break
            time.sleep(0.01)
        assert repository.load_json("normalised") == {"session": session_id}

    with session_scope("d" * 64):
        assert repository.load_json("normalised") is None


def test_import_reservations_are_independent_between_sessions(tmp_path: Path) -> None:
    coordinator = TakeoutImportCoordinator(anonymous_repository(tmp_path / "reservations.db"), timeout_seconds=10)
    with session_scope("e" * 64):
        first_job = coordinator.reserve("zip")
        with pytest.raises(TakeoutImportAlreadyRunning):
            coordinator.reserve("zip")
    with session_scope("f" * 64):
        second_job = coordinator.reserve("zip")
        coordinator.release_reservation(second_job)
    with session_scope("e" * 64):
        coordinator.release_reservation(first_job)
