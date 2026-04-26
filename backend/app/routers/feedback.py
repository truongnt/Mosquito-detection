from fastapi import APIRouter

router = APIRouter(prefix="/api", tags=["feedback"])


@router.post("/feedback")
def feedback(payload: dict):
    return {"status": "received", "payload": payload}
