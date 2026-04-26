import os
from pathlib import Path

from fastapi import APIRouter, Depends, HTTPException, Query

from ..config import settings
from ..deps import require_admin

router = APIRouter(prefix="/api/admin", tags=["admin-logs"], dependencies=[Depends(require_admin)])


def _tail_lines(path: Path, max_lines: int) -> list[str]:
    if max_lines <= 0:
        return []
    if not path.exists():
        return []
    data = path.read_text(encoding="utf-8", errors="replace").splitlines()
    return data[-max_lines:]


@router.get("/logs")
def get_logs(
    service: str = Query(default="backend", pattern="^(backend|worker)$"),
    tail: int = Query(default=200, ge=1, le=5000),
):
    os.makedirs(settings.log_dir, exist_ok=True)
    log_file = Path(settings.log_dir) / f"{service}.log"
    if not log_file.exists():
        raise HTTPException(status_code=404, detail=f"Log file not found: {log_file.name}")
    return {"service": service, "lines": _tail_lines(log_file, tail)}
