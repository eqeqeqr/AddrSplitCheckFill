from __future__ import annotations

from threading import Lock

_cancelled_jobs: set[str] = set()
_lock = Lock()


def request_cancel(job_id: str) -> None:
    with _lock:
        _cancelled_jobs.add(job_id)


def is_cancelled(job_id: str) -> bool:
    with _lock:
        return job_id in _cancelled_jobs


def clear_cancel(job_id: str) -> None:
    with _lock:
        _cancelled_jobs.discard(job_id)
