import logging
import os
import threading
from pathlib import Path

from sqlalchemy import select

from ..config import settings
from ..database import SessionLocal
from ..models.config_kv import AppConfigKV
from ..models.training import TrainingRun

log = logging.getLogger("model")


class ModelNotReady(RuntimeError):
    pass


_lock = threading.Lock()
_loaded_path: str | None = None
_loaded_mtime: float | None = None
_yolo = None


def _get_active_model_path() -> str | None:
    # 1) DB config override: app_config key "model" with {"active_path": "..."}.
    try:
        db = SessionLocal()
        row = db.get(AppConfigKV, "model")
        if row and isinstance(row.value_json, dict):
            active = row.value_json.get("active_path")
            if isinstance(active, str) and active.strip():
                p = Path(active.strip())
                if p.exists() and p.is_file():
                    return str(p)
    except Exception:
        pass
    finally:
        try:
            db.close()  # type: ignore[has-type]
        except Exception:
            pass

    # 2) ENV default (compose sets this).
    p = Path(settings.model_path)
    if p.exists() and p.is_file():
        return str(p)

    # 3) Latest succeeded training artifact.
    try:
        db = SessionLocal()
        run = (
            db.execute(
                select(TrainingRun)
                .where(TrainingRun.status == "succeeded")
                .where(TrainingRun.artifact_path.is_not(None))
                .order_by(TrainingRun.created_at.desc())
                .limit(1)
            )
            .scalars()
            .first()
        )
        if run and run.artifact_path:
            ap = Path(run.artifact_path)
            if ap.exists() and ap.is_file():
                return str(ap)
    except Exception:
        pass
    finally:
        try:
            db.close()  # type: ignore[has-type]
        except Exception:
            pass

    return None


def _load_yolo(model_path: str):
    from ultralytics import YOLO  # local import so backend can still boot without ML deps

    return YOLO(model_path)


def get_model():
    global _loaded_path, _loaded_mtime, _yolo
    model_path = _get_active_model_path()
    if not model_path:
        raise ModelNotReady("No model available yet. Train first or set app_config:model.active_path / MODEL_PATH.")

    mtime = None
    try:
        mtime = os.path.getmtime(model_path)
    except Exception:
        mtime = None

    with _lock:
        if _yolo is not None and _loaded_path == model_path and _loaded_mtime == mtime:
            return _yolo

        log.info("loading yolo model path=%s", model_path)
        _yolo = _load_yolo(model_path)
        _loaded_path = model_path
        _loaded_mtime = mtime
        return _yolo


def predict_image(image_path: str) -> tuple[str, float]:
    model = get_model()
    res = model.predict(source=image_path, device="cpu", verbose=False)
    if not res:
        raise RuntimeError("No prediction results")

    r0 = res[0]
    probs = getattr(r0, "probs", None)
    names = getattr(r0, "names", None)
    if probs is None or names is None:
        raise RuntimeError("Model is not a classification model (missing probs/names)")

    top1 = int(probs.top1)
    conf = float(probs.top1conf)
    label = names.get(top1) if isinstance(names, dict) else None
    if not isinstance(label, str):
        label = str(top1)
    return label, round(conf, 6)
