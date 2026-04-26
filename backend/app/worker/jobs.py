import logging
import random
import time
from datetime import datetime, timezone

from sqlalchemy import select
from sqlalchemy.orm import Session

from ..database import SessionLocal
from ..models.training import TrainingEvent, TrainingRun

log = logging.getLogger("worker.jobs")


def _add_event(db: Session, run_id: str, level: str, message: str, payload: dict | None = None) -> None:
    db.add(
        TrainingEvent(
            run_id=run_id,
            ts=datetime.now(timezone.utc),
            level=level,
            message=message,
            payload_json=payload,
        )
    )


def run_training_job(run_id: str) -> None:
    db = SessionLocal()
    try:
        run = db.get(TrainingRun, run_id)
        if not run:
            log.error("training run not found run_id=%s", run_id)
            return

        run.status = "running"
        run.progress = 0.0
        run.current_epoch = 0
        _add_event(db, run_id, "INFO", "Training started", {"total_epochs": run.total_epochs})
        db.commit()

        total_epochs = max(1, int(run.total_epochs))
        val_acc_history: list[float] = []
        val_loss_history: list[float] = []
        for epoch in range(1, total_epochs + 1):
            time.sleep(1.0)
            val_acc = min(0.99, 0.6 + (epoch / total_epochs) * 0.35 + random.uniform(-0.01, 0.01))
            val_loss = max(0.01, 1.2 - (epoch / total_epochs) * 1.0 + random.uniform(-0.03, 0.03))
            val_acc_history.append(round(val_acc, 4))
            val_loss_history.append(round(val_loss, 4))
            run.current_epoch = epoch
            run.progress = round((epoch / total_epochs) * 100.0, 2)
            _add_event(db, run_id, "INFO", f"Epoch {epoch}/{total_epochs} completed")
            run.metrics_json = {
                "val_accuracy": val_acc_history[-1],
                "val_loss": val_loss_history[-1],
                "history": {"val_accuracy": val_acc_history, "val_loss": val_loss_history},
            }
            db.commit()

        run.status = "succeeded"
        run.metrics_json = run.metrics_json or {"val_accuracy": 0.9}
        run.artifact_path = f"/app/models/saved/{run_id}_model.pth"
        _add_event(db, run_id, "INFO", "Training succeeded", {"artifact_path": run.artifact_path})
        db.commit()
    except Exception as exc:
        db.rollback()
        run = db.get(TrainingRun, run_id)
        if run:
            run.status = "failed"
            run.error_message = str(exc)
            _add_event(db, run_id, "ERROR", "Training failed", {"error": str(exc)})
            db.commit()
        raise
    finally:
        db.close()
