"""Background jobs (data imports, ML recalculation) run outside the HTTP request.

Jobs run one at a time on a single worker thread, so an import and an ML recalculation never
read and write the same tables at once. Status and progress live in the background_jobs table,
which every browser can poll.
"""
import datetime
import queue
import threading
import traceback
from typing import Any, Callable, Dict, Optional

from sqlalchemy.orm import Session

from backend.app.core.database import SessionLocal
from backend.app.models.models import BackgroundJob

_queue: "queue.Queue[tuple]" = queue.Queue()
_worker: Optional[threading.Thread] = None
_worker_lock = threading.Lock()


class JobContext:
    """Handed to a job function: its own DB session plus progress reporting."""
    def __init__(self, job_id: int, db: Session):
        self.job_id = job_id
        self.db = db

    def progress(self, done: int, total: Optional[int] = None, message: Optional[str] = None) -> None:
        job = self.db.get(BackgroundJob, self.job_id)
        job.progress_done = done
        if total is not None:
            job.progress_total = total
        if message is not None:
            job.message = message
        self.db.commit()


def _run_one(job_id: int, fn: Callable[[JobContext], Dict[str, Any]]) -> None:
    db = SessionLocal()
    try:
        job = db.get(BackgroundJob, job_id)
        job.status = "RUNNING"
        job.started_at = datetime.datetime.utcnow()
        db.commit()
        result = fn(JobContext(job_id, db)) or {}
        job = db.get(BackgroundJob, job_id)
        job.status = "ERROR" if result.get("status") == "ERROR" else "SUCCESS"
        job.result = result
        job.message = result.get("message", job.message)
    except Exception as e:
        db.rollback()
        traceback.print_exc()
        job = db.get(BackgroundJob, job_id)
        job.status = "ERROR"
        job.message = str(e)
    finally:
        job.finished_at = datetime.datetime.utcnow()
        db.commit()
        db.close()


def _work_forever() -> None:
    while True:
        job_id, fn = _queue.get()
        try:
            _run_one(job_id, fn)
        finally:
            _queue.task_done()


def _ensure_worker() -> None:
    global _worker
    with _worker_lock:
        if _worker is None or not _worker.is_alive():
            _worker = threading.Thread(target=_work_forever, name="background-jobs", daemon=True)
            _worker.start()


def submit(db: Session, kind: str, fn: Callable[[JobContext], Dict[str, Any]],
           params: Optional[Dict[str, Any]] = None, message: Optional[str] = None) -> BackgroundJob:
    job = BackgroundJob(kind=kind, status="QUEUED", params=params or {}, message=message or "Waiting to start")
    db.add(job)
    db.commit()
    db.refresh(job)
    _ensure_worker()
    _queue.put((job.id, fn))
    return job


def active_job(db: Session, kind: str) -> Optional[BackgroundJob]:
    return (db.query(BackgroundJob)
            .filter(BackgroundJob.kind == kind, BackgroundJob.status.in_(["QUEUED", "RUNNING"]))
            .order_by(BackgroundJob.id.desc()).first())


def mark_interrupted_jobs(db: Session) -> None:
    """Jobs left QUEUED/RUNNING by a previous server process will never finish; say so."""
    for job in db.query(BackgroundJob).filter(BackgroundJob.status.in_(["QUEUED", "RUNNING"])).all():
        job.status = "ERROR"
        job.message = "Interrupted because the server restarted. Please run it again."
        job.finished_at = datetime.datetime.utcnow()
    db.commit()


def job_to_dict(job: BackgroundJob) -> Dict[str, Any]:
    pct = None
    if job.progress_total:
        pct = round(min(100.0, job.progress_done * 100.0 / job.progress_total), 1)
    return {
        "id": job.id,
        "kind": job.kind,
        "status": job.status,
        "progress_done": job.progress_done or 0,
        "progress_total": job.progress_total,
        "progress_pct": pct,
        "message": job.message,
        "params": job.params or {},
        "result": job.result,
        "started_at": job.started_at.isoformat() if job.started_at else None,
        "finished_at": job.finished_at.isoformat() if job.finished_at else None,
        "created_at": job.created_at.isoformat() if job.created_at else None,
    }
