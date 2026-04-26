import os
import shutil
from datetime import datetime, timezone
from pathlib import Path

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field
from sqlalchemy import select
from sqlalchemy.orm import Session

from ..config import settings
from ..database import get_db
from ..deps import require_admin
from ..models.config_kv import AppConfigKV
from ..models.training import TrainingRun

router = APIRouter(prefix="/api/admin/models", tags=["admin-models"], dependencies=[Depends(require_admin)])


def _model_dir() -> Path:
    env_dir = os.environ.get("MODEL_DIR")
    if env_dir:
        return Path(env_dir).resolve()
    return Path(settings.model_path).resolve().parent


def _ensure_model_config(db: Session) -> AppConfigKV:
    row = db.get(AppConfigKV, "model")
    if row and isinstance(row.value_json, dict):
        return row
    now = datetime.now(timezone.utc)
    row = AppConfigKV(key="model", value_json={"auto_activate": True, "history": []}, updated_at=now)
    db.add(row)
    db.commit()
    return row


def _safe_within(path: Path, base: Path) -> bool:
    try:
        path.resolve().relative_to(base.resolve())
        return True
    except Exception:
        return False


def _update_aliases(active_path: Path) -> None:
    md = _model_dir()
    md.mkdir(parents=True, exist_ok=True)
    shutil.copy2(active_path, md / "best_model.pt")
    shutil.copy2(active_path, md / "best_model.pth")


class ActivatePayload(BaseModel):
    run_id: str | None = Field(default=None, max_length=64)
    artifact_path: str | None = Field(default=None, max_length=1024)


class SettingsPayload(BaseModel):
    auto_activate: bool = True


@router.get("")
def list_models(db: Session = Depends(get_db), limit: int = 50):
    limit = max(1, min(200, limit))
    cfg = _ensure_model_config(db)
    cfg_val = cfg.value_json if isinstance(cfg.value_json, dict) else {}
    active_path = cfg_val.get("active_path")
    auto_activate = bool(cfg_val.get("auto_activate", True))
    history = cfg_val.get("history") if isinstance(cfg_val.get("history"), list) else []

    runs = (
        db.execute(
            select(TrainingRun)
            .where(TrainingRun.status == "succeeded")
            .where(TrainingRun.artifact_path.is_not(None))
            .order_by(TrainingRun.created_at.desc())
            .limit(limit)
        )
        .scalars()
        .all()
    )

    base = _model_dir()
    items = []
    for r in runs:
        ap = r.artifact_path or ""
        size = None
        mtime = None
        exists = False
        try:
            p = Path(ap)
            if p.exists() and p.is_file():
                exists = True
                st = p.stat()
                size = st.st_size
                mtime = st.st_mtime
        except Exception:
            pass

        items.append(
            {
                "run_id": r.id,
                "created_at": r.created_at,
                "artifact_path": ap,
                "artifact_exists": exists,
                "artifact_within_model_dir": _safe_within(Path(ap), base) if ap else False,
                "artifact_size_bytes": size,
                "artifact_mtime": mtime,
                "metrics_json": r.metrics_json,
                "params_json": r.params_json,
                "is_active": bool(active_path) and isinstance(active_path, str) and active_path == ap,
            }
        )

    return {"active_path": active_path, "auto_activate": auto_activate, "history": history, "versions": items}


@router.put("/settings")
def put_settings(payload: SettingsPayload, db: Session = Depends(get_db)):
    cfg = _ensure_model_config(db)
    val = cfg.value_json if isinstance(cfg.value_json, dict) else {}
    val["auto_activate"] = bool(payload.auto_activate)
    cfg.value_json = val
    cfg.updated_at = datetime.now(timezone.utc)
    db.commit()
    return {"status": "ok", "auto_activate": val["auto_activate"]}


@router.post("/activate")
def activate(payload: ActivatePayload, db: Session = Depends(get_db)):
    cfg = _ensure_model_config(db)
    val = cfg.value_json if isinstance(cfg.value_json, dict) else {}
    current = val.get("active_path") if isinstance(val.get("active_path"), str) else None
    history = val.get("history") if isinstance(val.get("history"), list) else []

    target_path = None
    if payload.run_id:
        run = db.get(TrainingRun, payload.run_id)
        if not run or not run.artifact_path:
            raise HTTPException(status_code=404, detail="Run not found or has no artifact")
        target_path = run.artifact_path
    elif payload.artifact_path:
        target_path = payload.artifact_path
    else:
        raise HTTPException(status_code=400, detail="Provide run_id or artifact_path")

    p = Path(str(target_path)).resolve()
    if not (p.exists() and p.is_file()):
        raise HTTPException(status_code=400, detail="Artifact file not found on disk")

    base = _model_dir()
    if not _safe_within(p, base):
        raise HTTPException(status_code=400, detail="Artifact path is outside MODEL_DIR")

    if current and current != str(p):
        history = [h for h in history if isinstance(h, str) and h != str(p)]
        history.insert(0, current)
        history = history[:20]

    val["active_path"] = str(p)
    val["history"] = history
    val["last_switched_at"] = datetime.now(timezone.utc).isoformat()
    cfg.value_json = val
    cfg.updated_at = datetime.now(timezone.utc)
    db.commit()

    _update_aliases(p)
    return {"status": "ok", "active_path": val["active_path"], "history": history}


@router.post("/rollback")
def rollback(db: Session = Depends(get_db)):
    cfg = _ensure_model_config(db)
    val = cfg.value_json if isinstance(cfg.value_json, dict) else {}
    current = val.get("active_path") if isinstance(val.get("active_path"), str) else None
    history = val.get("history") if isinstance(val.get("history"), list) else []

    if not history:
        raise HTTPException(status_code=400, detail="No history to rollback")

    next_path = history.pop(0)
    if not isinstance(next_path, str) or not next_path:
        raise HTTPException(status_code=400, detail="Invalid history entry")

    p = Path(next_path).resolve()
    if not (p.exists() and p.is_file()):
        raise HTTPException(status_code=400, detail="History artifact file not found on disk")

    base = _model_dir()
    if not _safe_within(p, base):
        raise HTTPException(status_code=400, detail="History artifact path is outside MODEL_DIR")

    if current and current != str(p):
        history.insert(0, current)
        history = history[:20]

    val["active_path"] = str(p)
    val["history"] = history
    val["last_switched_at"] = datetime.now(timezone.utc).isoformat()
    cfg.value_json = val
    cfg.updated_at = datetime.now(timezone.utc)
    db.commit()

    _update_aliases(p)
    return {"status": "ok", "active_path": val["active_path"], "history": history}

