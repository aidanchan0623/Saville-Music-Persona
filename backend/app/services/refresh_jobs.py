from __future__ import annotations

import logging
import threading
import time
import uuid
from contextvars import copy_context
from datetime import datetime, timezone
from typing import Any, Callable

from app.database.repository import JsonRepository
from app.session import current_session_namespace


JOB_KEY = "refresh_job"
ACTIVE_STATUSES = {"queued", "fetching", "normalizing", "enriching", "rebuilding", "saving"}
TERMINAL_STATUSES = {"complete", "failed"}
STAGE_PROGRESS = {
    "queued": 0,
    "fetching": 10,
    "normalizing": 35,
    "enriching": 55,
    "rebuilding": 78,
    "saving": 92,
    "complete": 100,
    "failed": 100,
}
Processor = Callable[[dict[str, bool], "RefreshCoordinator", float], None]


class RefreshAlreadyRunning(RuntimeError):
    pass


class RefreshCoordinator:
    """Run one refresh at a time and keep the previous profile usable until commit."""

    def __init__(self, repo: JsonRepository, timeout_seconds: int) -> None:
        self.repo = repo
        self.timeout_seconds = timeout_seconds
        self._lock = threading.Lock()
        self._active_scopes: set[str] = set()
        self._logger = logging.getLogger("saville.refresh")
        self.recover_interrupted_job()

    def recover_interrupted_job(self) -> None:
        job = self.status()
        if not job or job.get("status") not in ACTIVE_STATUSES:
            return
        job.update(
            {
                "status": "failed",
                "progress": 100,
                "message": "The backend restarted during refresh. Your previous profile is still available; retry refresh.",
                "errorCode": "backend_restarted",
                "finishedAt": utc_now(),
                "updatedAt": utc_now(),
            }
        )
        self.repo.save_json(JOB_KEY, job)

    def start(self, options: dict[str, bool], processor: Processor) -> dict[str, Any]:
        scope = current_session_namespace() or "local"
        with self._lock:
            if scope in self._active_scopes:
                raise RefreshAlreadyRunning("Music refresh is already running.")
            previous = self.status()
            if previous and previous.get("status") in ACTIVE_STATUSES:
                raise RefreshAlreadyRunning("Music refresh is already running.")
            self._active_scopes.add(scope)
        job = {
            "jobId": uuid.uuid4().hex,
            "status": "queued",
            "progress": 0,
            "message": "Music refresh is queued.",
            "errorCode": None,
            "useDemo": bool(options.get("use_demo")),
            "createdAt": utc_now(),
            "updatedAt": utc_now(),
            "finishedAt": None,
            "trackCount": None,
            "playCount": None,
            "warnings": [],
        }
        self.repo.save_json(JOB_KEY, job)
        context = copy_context()
        threading.Thread(target=context.run, args=(self._run, options, processor), name="music-refresh", daemon=True).start()
        return job

    def _run(self, options: dict[str, bool], processor: Processor) -> None:
        deadline = time.monotonic() + self.timeout_seconds
        try:
            processor(options, self, deadline)
        except TimeoutError:
            self.fail("Music refresh timed out. Your previous profile was preserved.", "refresh_timeout")
        except Exception:  # noqa: BLE001
            self._logger.exception("music refresh failed")
            self.fail("Music refresh failed safely. Your previous profile was preserved.", "refresh_failed")
        finally:
            scope = current_session_namespace() or "local"
            with self._lock:
                self._active_scopes.discard(scope)

    def stage(self, status: str, message: str, **fields: Any) -> dict[str, Any]:
        job = self.status() or {"jobId": uuid.uuid4().hex, "createdAt": utc_now()}
        job.update(
            {
                "status": status,
                "progress": STAGE_PROGRESS[status],
                "message": message,
                "errorCode": None,
                "updatedAt": utc_now(),
                **fields,
            }
        )
        if status in TERMINAL_STATUSES:
            job["finishedAt"] = utc_now()
        self.repo.save_json(JOB_KEY, job)
        return job

    def fail(self, message: str, error_code: str) -> dict[str, Any]:
        return self.stage("failed", message, errorCode=error_code)

    def status(self) -> dict[str, Any] | None:
        value = self.repo.load_json(JOB_KEY)
        return value if isinstance(value, dict) else None

    @staticmethod
    def check_timeout(deadline: float) -> None:
        if time.monotonic() > deadline:
            raise TimeoutError


def utc_now() -> str:
    return datetime.now(timezone.utc).isoformat()
