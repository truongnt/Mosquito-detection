from fastapi import APIRouter, Depends

from ..deps import require_admin

router = APIRouter(prefix="/api", tags=["reports"])


@router.get("/reports/health")
def health():
    return {"status": "ok"}


@router.get("/admin/health", dependencies=[Depends(require_admin)])
def admin_health():
    return {"status": "ok"}
