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
from ..models.schemas import TrainingEventOut, TrainingRunCreate, TrainingRunOut
from ..models.training import TrainingEvent, TrainingRun
from ..worker.jobs import run_training_job

router = APIRouter(prefix="/api/admin/training", tags=["admin-training"], dependencies=[Depends(require_admin)])
log = logging.getLogger("admin.training")


def _queue() -> Queue:
    redis_conn = Redis.from_url(settings.redis_url)
    return Queue("training", connection=redis_conn)


@router.post("/runs", response_model=TrainingRunOut)
def create_run(payload: TrainingRunCreate, db: Session = Depends(get_db)):
    run_id = uuid.uuid4().hex
    now = datetime.now(timezone.utc)
    run = TrainingRun(
        id=run_id,
        created_at=now,
        created_by="admin",
        status="queued",
        progress=0.0,
        current_epoch=0,
        total_epochs=payload.total_epochs,
    )
    db.add(run)
    db.commit()

    _queue().enqueue(run_training_job, run_id, job_timeout="6h")
    log.info("enqueue training run_id=%s total_epochs=%s", run_id, payload.total_epochs)
    return TrainingRunOut.model_validate(run, from_attributes=True)


@router.get("/runs", response_model=list[TrainingRunOut])
def list_runs(db: Session = Depends(get_db)):
    runs = db.execute(select(TrainingRun).order_by(TrainingRun.created_at.desc())).scalars().all()
    return [TrainingRunOut.model_validate(r, from_attributes=True) for r in runs]


@router.get("/runs/{run_id}", response_model=TrainingRunOut)
def get_run(run_id: str, db: Session = Depends(get_db)):
    run = db.get(TrainingRun, run_id)
    if not run:
        raise HTTPException(status_code=404, detail="Run not found")
    return TrainingRunOut.model_validate(run, from_attributes=True)


@router.get("/runs/{run_id}/events", response_model=list[TrainingEventOut])
def get_events(run_id: str, db: Session = Depends(get_db), limit: int = 200):
    limit = max(1, min(1000, limit))
    events = (
        db.execute(
            select(TrainingEvent)
            .where(TrainingEvent.run_id == run_id)
            .order_by(TrainingEvent.id.desc())
            .limit(limit)
        )
        .scalars()
        .all()
    )
    events = list(reversed(events))
    return [TrainingEventOut.model_validate(e, from_attributes=True) for e in events]
