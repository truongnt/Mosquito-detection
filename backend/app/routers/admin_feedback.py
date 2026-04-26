from fastapi import APIRouter, Depends
from sqlalchemy import select
from sqlalchemy.orm import Session

from ..database import get_db
from ..deps import require_admin
from ..models.feedback_event import FeedbackEvent

router = APIRouter(prefix="/api/admin/feedback", tags=["admin-feedback"], dependencies=[Depends(require_admin)])


@router.get("")
def list_feedback(db: Session = Depends(get_db), limit: int = 200):
    limit = max(1, min(1000, limit))
    rows = db.execute(select(FeedbackEvent).order_by(FeedbackEvent.id.desc()).limit(limit)).scalars().all()
    rows = list(reversed(rows))
    return [
        {
            "id": r.id,
            "created_at": r.created_at,
            "request_id": r.request_id,
            "predicted_label": r.predicted_label,
            "confirmed_label": r.confirmed_label,
            "payload_json": r.payload_json,
        }
        for r in rows
    ]

