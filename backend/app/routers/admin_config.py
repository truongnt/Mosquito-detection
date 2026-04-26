from datetime import datetime, timezone

from fastapi import APIRouter, Depends
from sqlalchemy import select
from sqlalchemy.orm import Session

from ..database import get_db
from ..deps import require_admin
from ..models.config_kv import AppConfigKV

router = APIRouter(prefix="/api/admin/config", tags=["admin-config"], dependencies=[Depends(require_admin)])


@router.get("")
def get_config(db: Session = Depends(get_db)):
    rows = db.execute(select(AppConfigKV)).scalars().all()
    return {row.key: row.value_json for row in rows}


@router.put("")
def put_config(payload: dict, db: Session = Depends(get_db)):
    now = datetime.now(timezone.utc)
    for key, value in payload.items():
        if not isinstance(key, str) or not key:
            continue
        row = db.get(AppConfigKV, key)
        if row:
            row.value_json = value if isinstance(value, dict) else {"value": value}
            row.updated_at = now
        else:
            db.add(
                AppConfigKV(
                    key=key,
                    value_json=value if isinstance(value, dict) else {"value": value},
                    updated_at=now,
                )
            )
    db.commit()
    return {"status": "ok"}

