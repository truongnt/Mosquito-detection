from datetime import datetime, timezone

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from ..database import get_db
from ..models.feedback_event import FeedbackEvent

router = APIRouter(prefix="/api", tags=["feedback"])


@router.post("/feedback")
def feedback(payload: dict, db: Session = Depends(get_db)):
    now = datetime.now(timezone.utc)
    req_id = payload.get("request_id") if isinstance(payload, dict) else None
    predicted = payload.get("predicted_label") if isinstance(payload, dict) else None
    confirmed = payload.get("confirmed_label") if isinstance(payload, dict) else None
    row = FeedbackEvent(
        created_at=now,
        request_id=req_id if isinstance(req_id, str) else None,
        predicted_label=predicted if isinstance(predicted, str) else None,
        confirmed_label=confirmed if isinstance(confirmed, str) else None,
        payload_json=payload if isinstance(payload, dict) else {"value": payload},
    )
    db.add(row)
    db.commit()
    return {"status": "received", "id": row.id}
