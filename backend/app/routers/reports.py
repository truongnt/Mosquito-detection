from fastapi import APIRouter

router = APIRouter(prefix="/api", tags=["reports"])


@router.get("/reports/health")
def health():
    return {"status": "ok"}
