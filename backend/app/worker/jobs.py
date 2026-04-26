import logging
import os
import shutil
import time
from datetime import datetime, timezone
from pathlib import Path

from sqlalchemy.orm import Session

from ..database import SessionLocal
from ..models.config_kv import AppConfigKV
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


def _model_dir() -> Path:
    return Path(os.environ.get("MODEL_DIR", "/app/models/saved")).resolve()


def _data_dir() -> Path:
    return Path(os.environ.get("DATA_DIR", "/app/data")).resolve()


def _set_active_model(db: Session, active_path: str) -> None:
    now = datetime.now(timezone.utc)
    row = db.get(AppConfigKV, "model")
    if row and isinstance(row.value_json, dict) and row.value_json.get("auto_activate") is False:
        return

    value = dict(row.value_json) if row and isinstance(row.value_json, dict) else {}
    current = value.get("active_path") if isinstance(value.get("active_path"), str) else None
    history = value.get("history") if isinstance(value.get("history"), list) else []
    if current and current != active_path:
        history = [h for h in history if isinstance(h, str) and h != active_path]
        history.insert(0, current)
        history = history[:20]
    value["active_path"] = active_path
    value["history"] = history
    value.setdefault("auto_activate", True)
    if row:
        row.value_json = value
        row.updated_at = now
    else:
        db.add(AppConfigKV(key="model", value_json=value, updated_at=now))


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

        params = run.params_json or {}
        dataset = str(params.get("dataset") or "mosquitodl")
        imgsz = int(params.get("img_size") or 224)
        lr0 = float(params.get("learning_rate") or 0.001)
        batch = int(params.get("batch_size") or 32)
        base_model = str(params.get("base_model") or "yolo26n-cls.pt")
        aug = (params.get("augmentation") or {}) if isinstance(params.get("augmentation"), dict) else {}
        aug_enabled = bool(aug.get("enabled", True))

        data_root = _data_dir() / "processed" / dataset
        if not (data_root / "train").exists():
            raise FileNotFoundError(f"Processed dataset not found: {data_root} (run preprocess first)")

        model_dir = _model_dir()
        model_dir.mkdir(parents=True, exist_ok=True)
        project_dir = model_dir.parent / "runs"

        _add_event(
            db,
            run_id,
            "INFO",
            "Starting Ultralytics YOLO training (classification)",
            {"dataset_root": str(data_root), "base_model": base_model, "imgsz": imgsz, "batch": batch, "lr0": lr0},
        )
        db.commit()

        from ultralytics import YOLO

        yolo = YOLO(base_model)

        val_acc_history: list[float] = []
        val_loss_history: list[float] = []

        def _on_epoch_end(trainer):
            try:
                epoch_idx = int(getattr(trainer, "epoch", 0)) + 1
                epochs_total = int(getattr(trainer, "epochs", run.total_epochs) or run.total_epochs)
                run_db = db.get(TrainingRun, run_id)
                if not run_db:
                    return
                run_db.current_epoch = epoch_idx
                run_db.progress = round((epoch_idx / max(1, epochs_total)) * 100.0, 2)

                metrics = getattr(trainer, "metrics", None) or {}
                fitness = metrics.get("fitness") if isinstance(metrics, dict) else None
                top1 = metrics.get("metrics/top1") if isinstance(metrics, dict) else None
                if top1 is None and isinstance(metrics, dict):
                    top1 = metrics.get("top1")

                loss_items = getattr(trainer, "loss_items", None)
                val_loss = None
                if isinstance(loss_items, (list, tuple)) and loss_items:
                    try:
                        val_loss = float(loss_items[0])
                    except Exception:
                        val_loss = None

                if top1 is not None:
                    try:
                        val_acc_history.append(round(float(top1), 6))
                    except Exception:
                        pass
                if val_loss is not None:
                    val_loss_history.append(round(float(val_loss), 6))

                run_db.metrics_json = {
                    "val_accuracy": val_acc_history[-1] if val_acc_history else None,
                    "val_loss": val_loss_history[-1] if val_loss_history else None,
                    "fitness": fitness,
                    "history": {"val_accuracy": val_acc_history, "val_loss": val_loss_history},
                }
                _add_event(db, run_id, "INFO", f"Epoch {epoch_idx}/{epochs_total} completed", run_db.metrics_json)
                db.commit()
            except Exception:
                db.rollback()

        try:
            yolo.add_callback("on_train_epoch_end", _on_epoch_end)
        except Exception:
            _add_event(db, run_id, "WARNING", "YOLO callback API not available; progress will be coarse-grained.")
            db.commit()

        train_kwargs = {
            "data": str(data_root),
            "epochs": int(run.total_epochs),
            "imgsz": imgsz,
            "batch": batch,
            "lr0": lr0,
            "device": "cpu",
            "project": str(project_dir),
            "name": run_id,
            "exist_ok": True,
            "verbose": False,
        }

        if aug_enabled:
            train_kwargs.update(
                {
                    "hsv_h": float(aug.get("hsv_h", 0.015)),
                    "hsv_s": float(aug.get("hsv_s", 0.7)),
                    "hsv_v": float(aug.get("hsv_v", 0.4)),
                    "degrees": float(aug.get("degrees", 10.0)),
                    "translate": float(aug.get("translate", 0.1)),
                    "scale": float(aug.get("scale", 0.5)),
                    "shear": float(aug.get("shear", 2.0)),
                    "perspective": float(aug.get("perspective", 0.0)),
                    "fliplr": float(aug.get("fliplr", 0.5)),
                    "flipud": float(aug.get("flipud", 0.0)),
                    "mosaic": float(aug.get("mosaic", 0.8)),
                    "mixup": float(aug.get("mixup", 0.0)),
                    "copy_paste": float(aug.get("copy_paste", 0.0)),
                    "erasing": float(aug.get("erasing", 0.0)),
                }
            )
        else:
            train_kwargs.update({"hsv_h": 0.0, "hsv_s": 0.0, "hsv_v": 0.0, "degrees": 0.0, "translate": 0.0, "scale": 0.0, "shear": 0.0, "perspective": 0.0, "fliplr": 0.0, "flipud": 0.0, "mosaic": 0.0, "mixup": 0.0, "copy_paste": 0.0, "erasing": 0.0})

        yolo.train(**train_kwargs)

        best = Path(train_kwargs["project"]) / train_kwargs["name"] / "weights" / "best.pt"
        last = Path(train_kwargs["project"]) / train_kwargs["name"] / "weights" / "last.pt"
        src = best if best.exists() else last if last.exists() else None
        if not src:
            raise FileNotFoundError(f"Training finished but no weights found under {Path(train_kwargs['project'])/train_kwargs['name']}/weights")

        run_specific = model_dir / f"{run_id}_best.pt"
        shutil.copy2(src, run_specific)

        # Backward compatible "active" aliases.
        alias_pt = model_dir / "best_model.pt"
        alias_pth = model_dir / "best_model.pth"
        shutil.copy2(run_specific, alias_pt)
        shutil.copy2(run_specific, alias_pth)

        run.status = "succeeded"
        run.progress = 100.0
        run.artifact_path = str(run_specific)
        _set_active_model(db, str(run_specific))
        _add_event(db, run_id, "INFO", "Training succeeded", {"artifact_path": run.artifact_path, "active_path": str(run_specific)})
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
