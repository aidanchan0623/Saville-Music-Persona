from __future__ import annotations

import json
import logging
import threading
import time
import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Callable

from app.database.repository import JsonRepository


TERMINAL_STATUSES = {"complete", "failed"}
ACTIVE_STATUSES = {"queued", "parsing", "normalizing", "saving", "rebuilding"}
STAGE_PROGRESS = {
    "queued": 0,
    "parsing": 15,
    "normalizing": 45,
    "rebuilding": 65,
    "saving": 85,
    "complete": 100,
    "failed": 100,
}
JOB_PREFIX = "takeout_import_job:"


class TakeoutImportAlreadyRunning(RuntimeError):
    pass


class TakeoutImportTimedOut(TimeoutError):
    pass


Processor = Callable[[str, Path, "TakeoutImportCoordinator", float], None]


class TakeoutImportCoordinator:
    def __init__(self, repo: JsonRepository, timeout_seconds: int) -> None:
        self.repo = repo
        self.timeout_seconds = timeout_seconds
        self._state_lock = threading.Lock()
        self._active_job_id: str | None = None
        self._logger = logging.getLogger("saville.takeout_import")
        self._logger.setLevel(logging.INFO)
        self.recover_interrupted_jobs()

    def recover_interrupted_jobs(self) -> None:
        for key, job in self.repo.load_json_prefix(JOB_PREFIX).items():
            if isinstance(job, dict) and job.get("status") in ACTIVE_STATUSES:
                job.update(
                    {
                        "status": "failed",
                        "progress": 100,
                        "message": "The backend restarted during import. Your previous profile is still available; retry the import.",
                        "errorCode": "backend_restarted",
                        "finishedAt": utc_now(),
                    }
                )
                self.repo.save_json(key, job)
                self.log(job.get("jobId", "unknown"), "failure", stage="restart_recovery", errorCode="backend_restarted")

    def reserve(self, file_type: str) -> str:
        with self._state_lock:
            if self._active_job_id:
                raise TakeoutImportAlreadyRunning("Another Takeout import is already running.")
            job_id = uuid.uuid4().hex
            self._active_job_id = job_id
        self.log(job_id, "upload_received", fileType=file_type)
        return job_id

    def release_reservation(self, job_id: str) -> None:
        with self._state_lock:
            if self._active_job_id == job_id:
                self._active_job_id = None

    def queue(self, job_id: str, path: Path, file_size: int, processor: Processor) -> dict[str, Any]:
        job = {
            "jobId": job_id,
            "status": "queued",
            "progress": STAGE_PROGRESS["queued"],
            "message": "Takeout upload received. Waiting to parse locally.",
            "errorCode": None,
            "fileSize": file_size,
            "createdAt": utc_now(),
            "updatedAt": utc_now(),
            "importedCount": None,
            "trackCount": None,
            "playCount": None,
        }
        self.repo.save_json(self.key(job_id), job)
        self.log(job_id, "file_size", fileSize=file_size)
        thread = threading.Thread(
            target=self._run,
            args=(job_id, path, processor),
            name=f"takeout-import-{job_id[:8]}",
            daemon=True,
        )
        thread.start()
        return job

    def _run(self, job_id: str, path: Path, processor: Processor) -> None:
        deadline = time.monotonic() + self.timeout_seconds
        try:
            processor(job_id, path, self, deadline)
        except TakeoutImportTimedOut:
            self.fail(job_id, "Import exceeded the local processing timeout. Your previous profile was preserved.", "import_timeout", "timeout")
        except Exception:  # noqa: BLE001
            self._logger.exception(json.dumps({"event": "takeout_import_failure", "jobId": job_id, "stage": "unexpected", "errorCode": "import_internal_error"}))
            self.fail(job_id, "Takeout import failed safely. Your previous profile was preserved.", "import_internal_error", "unexpected")
        finally:
            try:
                path.unlink(missing_ok=True)
            finally:
                self.release_reservation(job_id)

    def stage(self, job_id: str, status: str, message: str, **fields: Any) -> dict[str, Any]:
        job = self.get(job_id) or {"jobId": job_id, "createdAt": utc_now()}
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
        self.repo.save_json(self.key(job_id), job)
        return job

    def fail(self, job_id: str, message: str, error_code: str, stage: str) -> dict[str, Any]:
        job = self.get(job_id) or {"jobId": job_id, "createdAt": utc_now()}
        job.update(
            {
                "status": "failed",
                "progress": STAGE_PROGRESS["failed"],
                "message": message,
                "errorCode": error_code,
                "failureStage": stage,
                "updatedAt": utc_now(),
                "finishedAt": utc_now(),
            }
        )
        self.repo.save_json(self.key(job_id), job)
        self.log(job_id, "failure", stage=stage, errorCode=error_code)
        return job

    def get(self, job_id: str) -> dict[str, Any] | None:
        value = self.repo.load_json(self.key(job_id))
        return value if isinstance(value, dict) else None

    def check_timeout(self, deadline: float) -> None:
        if time.monotonic() > deadline:
            raise TakeoutImportTimedOut

    def log(self, job_id: str, event: str, **fields: Any) -> None:
        payload = {"event": f"takeout_import_{event}", "jobId": job_id, **fields}
        self._logger.info(json.dumps(payload, sort_keys=True, default=str))

    @staticmethod
    def key(job_id: str) -> str:
        return f"{JOB_PREFIX}{job_id}"


def utc_now() -> str:
    return datetime.now(timezone.utc).isoformat()
