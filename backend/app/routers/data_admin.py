import logging
import uuid
from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException
from redis import Redis
from rq import Queue
from sqlalchemy import select
from sqlalchemy.orm import Session

from ..config import settings
from ..database import get_db
from ..deps import require_admin
from ..models.admin_job import AdminJobEvent, AdminJobRun
from ..models.schemas import AdminJobCreate, AdminJobEventOut, AdminJobOut
from ..worker.jobs_data import download_data_job, preprocess_job

router = APIRouter(prefix="/api/admin/data", tags=["admin-data"], dependencies=[Depends(require_admin)])
log = logging.getLogger("admin.data")


def _queue() -> Queue:
    redis_conn = Redis.from_url(settings.redis_url)
    return Queue("admin", connection=redis_conn)


@router.post("/download", response_model=AdminJobOut)
def start_download(payload: AdminJobCreate, db: Session = Depends(get_db)):
    job_id = uuid.uuid4().hex
    now = datetime.now(timezone.utc)
    run = AdminJobRun(
        id=job_id,
        kind="download_data",
        created_at=now,
        created_by="admin",
        status="queued",
        progress=0.0,
        params_json={"dataset": payload.dataset},
    )
    db.add(run)
    db.commit()

    _queue().enqueue(download_data_job, job_id, payload.dataset, job_timeout="3h")
    log.info("enqueue download job_id=%s dataset=%s", job_id, payload.dataset)
    return AdminJobOut.model_validate(run, from_attributes=True)


@router.post("/preprocess", response_model=AdminJobOut)
def start_preprocess(payload: AdminJobCreate, db: Session = Depends(get_db)):
    if payload.val_ratio + payload.test_ratio >= 0.9:
        raise HTTPException(status_code=400, detail="val_ratio + test_ratio too large")

    job_id = uuid.uuid4().hex
    now = datetime.now(timezone.utc)
    run = AdminJobRun(
        id=job_id,
        kind="preprocess",
        created_at=now,
        created_by="admin",
        status="queued",
        progress=0.0,
        params_json={
            "dataset": payload.dataset,
            "max_per_label": payload.max_per_label,
            "val_ratio": payload.val_ratio,
            "test_ratio": payload.test_ratio,
            "seed": payload.seed,
        },
    )
    db.add(run)
    db.commit()

    _queue().enqueue(
        preprocess_job,
        job_id,
        payload.dataset,
        payload.max_per_label,
        payload.val_ratio,
        payload.test_ratio,
        payload.seed,
        job_timeout="6h",
    )
    log.info("enqueue preprocess job_id=%s dataset=%s", job_id, payload.dataset)
    return AdminJobOut.model_validate(run, from_attributes=True)


@router.get("/jobs", response_model=list[AdminJobOut])
def list_jobs(db: Session = Depends(get_db), limit: int = 50):
    limit = max(1, min(200, limit))
    jobs = db.execute(select(AdminJobRun).order_by(AdminJobRun.created_at.desc()).limit(limit)).scalars().all()
    return [AdminJobOut.model_validate(j, from_attributes=True) for j in jobs]


@router.get("/jobs/{job_id}", response_model=AdminJobOut)
def get_job(job_id: str, db: Session = Depends(get_db)):
    job = db.get(AdminJobRun, job_id)
    if not job:
        raise HTTPException(status_code=404, detail="Job not found")
    return AdminJobOut.model_validate(job, from_attributes=True)


@router.get("/jobs/{job_id}/events", response_model=list[AdminJobEventOut])
def get_job_events(job_id: str, db: Session = Depends(get_db), limit: int = 200):
    limit = max(1, min(1000, limit))
    events = (
        db.execute(
            select(AdminJobEvent).where(AdminJobEvent.job_id == job_id).order_by(AdminJobEvent.id.desc()).limit(limit)
        )
        .scalars()
        .all()
    )
    events = list(reversed(events))
    return [AdminJobEventOut.model_validate(e, from_attributes=True) for e in events]

