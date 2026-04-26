import logging
import os
import random
import shutil
import subprocess
from datetime import datetime, timezone
from pathlib import Path

from sqlalchemy import select
from sqlalchemy.orm import Session

from ..database import SessionLocal
from ..models.admin_job import AdminJobEvent, AdminJobRun

log = logging.getLogger("worker.data")


def _data_dir() -> Path:
    return Path(os.environ.get("DATA_DIR", "/app/data")).resolve()


def _raw_dir() -> Path:
    return _data_dir() / "raw"


def _processed_dir() -> Path:
    return _data_dir() / "processed"


def _add_event(db: Session, job_id: str, level: str, message: str, payload: dict | None = None) -> None:
    db.add(
        AdminJobEvent(
            job_id=job_id,
            ts=datetime.now(timezone.utc),
            level=level,
            message=message,
            payload_json=payload,
        )
    )


def _set_progress(db: Session, run: AdminJobRun, progress: float, message: str | None = None) -> None:
    run.progress = float(max(0.0, min(100.0, progress)))
    if message:
        _add_event(db, run.id, "INFO", message)


def _image_files(root: Path) -> list[Path]:
    exts = {".jpg", ".jpeg", ".png", ".bmp", ".webp"}
    files: list[Path] = []
    for p in root.rglob("*"):
        if p.is_file() and p.suffix.lower() in exts:
            files.append(p)
    return files


def _infer_label(path: Path, root: Path) -> str:
    try:
        rel = path.relative_to(root)
    except ValueError:
        return "unknown"
    parts = list(rel.parts)
    if len(parts) >= 2:
        return parts[0].lower()
    return "unknown"


def download_data_job(job_id: str, dataset: str) -> None:
    db = SessionLocal()
    try:
        run = db.get(AdminJobRun, job_id)
        if not run:
            log.error("admin job not found job_id=%s", job_id)
            return

        run.status = "running"
        run.progress = 0.0
        _add_event(db, job_id, "INFO", "Download started", {"dataset": dataset})
        db.commit()

        raw = _raw_dir()
        raw.mkdir(parents=True, exist_ok=True)

        if dataset.lower() != "mosquitodl":
            raise ValueError("Only dataset=mosquitodl is supported for now")

        repo_url = "https://github.com/jypark1994/MosquitoDL.git"
        dest = raw / "mosquitodl"

        _set_progress(db, run, 5, f"Preparing {dest}")
        db.commit()

        if dest.exists() and (dest / ".git").exists():
            _set_progress(db, run, 20, "Updating existing repo (git pull)")
            db.commit()
            subprocess.check_call(["git", "-C", str(dest), "fetch", "--all", "--prune"])
            subprocess.check_call(["git", "-C", str(dest), "reset", "--hard", "origin/master"])
        else:
            if dest.exists():
                shutil.rmtree(dest)
            _set_progress(db, run, 20, "Cloning MosquitoDL")
            db.commit()
            subprocess.check_call(["git", "clone", "--depth", "1", repo_url, str(dest)])

        _set_progress(db, run, 80, "Indexing files")
        db.commit()
        files = _image_files(dest)
        run.result_json = {"dataset": dataset, "raw_path": str(dest), "image_count": len(files)}

        run.status = "succeeded"
        run.progress = 100.0
        _add_event(db, job_id, "INFO", "Download succeeded", run.result_json)
        db.commit()
    except Exception as exc:
        db.rollback()
        run = db.get(AdminJobRun, job_id)
        if run:
            run.status = "failed"
            run.error_message = str(exc)
            _add_event(db, job_id, "ERROR", "Download failed", {"error": str(exc)})
            db.commit()
        raise
    finally:
        db.close()


def preprocess_job(job_id: str, dataset: str, max_per_label: int, val_ratio: float, test_ratio: float, seed: int) -> None:
    db = SessionLocal()
    try:
        run = db.get(AdminJobRun, job_id)
        if not run:
            log.error("admin job not found job_id=%s", job_id)
            return

        run.status = "running"
        run.progress = 0.0
        _add_event(
            db,
            job_id,
            "INFO",
            "Preprocess started",
            {"dataset": dataset, "max_per_label": max_per_label, "val_ratio": val_ratio, "test_ratio": test_ratio},
        )
        db.commit()

        if dataset.lower() != "mosquitodl":
            raise ValueError("Only dataset=mosquitodl is supported for now")

        raw_root = _raw_dir() / "mosquitodl"
        if not raw_root.exists():
            raise FileNotFoundError("Raw dataset not found. Run download first.")

        files = _image_files(raw_root)
        if not files:
            raise ValueError("No image files found in raw dataset")

        _set_progress(db, run, 10, f"Found {len(files)} images. Inferring labels.")
        db.commit()

        by_label: dict[str, list[Path]] = {}
        for f in files:
            label = _infer_label(f, raw_root)
            by_label.setdefault(label, []).append(f)

        rng = random.Random(seed)
        processed_root = _processed_dir()
        target = processed_root / "mosquitodl"
        if target.exists():
            shutil.rmtree(target)
        (target / "train").mkdir(parents=True, exist_ok=True)
        (target / "val").mkdir(parents=True, exist_ok=True)
        (target / "test").mkdir(parents=True, exist_ok=True)

        labels = sorted(by_label.keys())
        _add_event(db, job_id, "INFO", f"Labels: {labels}")
        db.commit()

        total_selected = 0
        total_copied = 0
        for idx, label in enumerate(labels):
            paths = by_label[label]
            rng.shuffle(paths)
            selected = paths[: max_per_label if max_per_label > 0 else len(paths)]
            total_selected += len(selected)

            n_test = int(len(selected) * test_ratio)
            n_val = int(len(selected) * val_ratio)
            n_train = max(0, len(selected) - n_test - n_val)

            splits = {
                "train": selected[:n_train],
                "val": selected[n_train : n_train + n_val],
                "test": selected[n_train + n_val : n_train + n_val + n_test],
            }

            for split_name, split_paths in splits.items():
                out_dir = target / split_name / label
                out_dir.mkdir(parents=True, exist_ok=True)
                for src in split_paths:
                    dst = out_dir / src.name
                    shutil.copy2(src, dst)
                    total_copied += 1

            _set_progress(db, run, 10 + ((idx + 1) / max(1, len(labels))) * 85, f"Processed label={label}")
            db.commit()

        run.result_json = {
            "dataset": dataset,
            "processed_path": str(target),
            "total_labels": len(labels),
            "total_selected": total_selected,
            "total_copied": total_copied,
        }
        run.status = "succeeded"
        run.progress = 100.0
        _add_event(db, job_id, "INFO", "Preprocess succeeded", run.result_json)
        db.commit()
    except Exception as exc:
        db.rollback()
        run = db.get(AdminJobRun, job_id)
        if run:
            run.status = "failed"
            run.error_message = str(exc)
            _add_event(db, job_id, "ERROR", "Preprocess failed", {"error": str(exc)})
            db.commit()
        raise
    finally:
        db.close()

