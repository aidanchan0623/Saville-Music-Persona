from __future__ import annotations

import logging
import threading
import time
import uuid
from datetime import datetime, timezone
from typing import Any, Callable

from app.database.repository import JsonRepository


JOB_KEY = "genre_enrichment_job"
ACTIVE_STATUSES = {"queued", "resolving", "rebuilding"}
TERMINAL_STATUSES = {"complete", "failed"}
STAGE_PROGRESS = {"queued": 0, "resolving": 15, "rebuilding": 85, "complete": 100, "failed": 100}
Processor = Callable[["GenreEnrichmentCoordinator", float], None]


class GenreEnrichmentAlreadyRunning(RuntimeError):
    pass


class GenreEnrichmentCoordinator:
    def __init__(self, repo: JsonRepository, timeout_seconds: int) -> None:
        self.repo = repo
        self.timeout_seconds = timeout_seconds
        self._lock = threading.Lock()
        self._active = False
        self._logger = logging.getLogger("saville.genre_enrichment")
        self.recover_interrupted_job()

    def recover_interrupted_job(self) -> None:
        job = self.status()
        if not job or job.get("status") not in ACTIVE_STATUSES:
            return
        job.update(
            {
                "status": "failed",
                "progress": 100,
                "message": "The backend restarted during genre enrichment. Your previous profile is still available; retry enrichment.",
                "errorCode": "backend_restarted",
                "finishedAt": utc_now(),
            }
        )
        self.repo.save_json(JOB_KEY, job)

    def start(self, processor: Processor) -> dict[str, Any]:
        with self._lock:
            if self._active:
                raise GenreEnrichmentAlreadyRunning("Genre enrichment is already running.")
            previous = self.status()
            if previous and previous.get("status") in ACTIVE_STATUSES:
                raise GenreEnrichmentAlreadyRunning("Genre enrichment is already running.")
            self._active = True
        job = {
            "jobId": uuid.uuid4().hex,
            "status": "queued",
            "progress": 0,
            "message": "Genre metadata enrichment is queued.",
            "errorCode": None,
            "createdAt": utc_now(),
            "updatedAt": utc_now(),
            "finishedAt": None,
            "attempted": 0,
            "matched": 0,
        }
        self.repo.save_json(JOB_KEY, job)
        threading.Thread(target=self._run, args=(processor,), name="genre-enrichment", daemon=True).start()
        return job

    def _run(self, processor: Processor) -> None:
        deadline = time.monotonic() + self.timeout_seconds
        try:
            processor(self, deadline)
        except TimeoutError:
            self.fail("Genre enrichment timed out. Your current listening profile was preserved.", "genre_enrichment_timeout")
        except Exception:  # noqa: BLE001
            self._logger.exception("genre enrichment failed")
            self.fail("Genre enrichment failed safely. Your current listening profile was preserved.", "genre_enrichment_failed")
        finally:
            with self._lock:
                self._active = False

    def stage(self, status: str, message: str, **fields: Any) -> dict[str, Any]:
        job = self.status() or {"jobId": uuid.uuid4().hex, "createdAt": utc_now()}
        job.update({"status": status, "progress": STAGE_PROGRESS[status], "message": message, "errorCode": None, "updatedAt": utc_now(), **fields})
        if status in TERMINAL_STATUSES:
            job["finishedAt"] = utc_now()
        self.repo.save_json(JOB_KEY, job)
        return job

    def fail(self, message: str, error_code: str) -> dict[str, Any]:
        job = self.stage("failed", message)
        job["errorCode"] = error_code
        self.repo.save_json(JOB_KEY, job)
        return job

    def status(self) -> dict[str, Any] | None:
        value = self.repo.load_json(JOB_KEY)
        return value if isinstance(value, dict) else None


def utc_now() -> str:
    return datetime.now(timezone.utc).isoformat()
