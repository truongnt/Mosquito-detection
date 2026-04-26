import logging
from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException, Response, Request
from sqlalchemy import select
from sqlalchemy.orm import Session

from ..auth import create_session_token, hash_password, verify_password
from ..config import settings
from ..database import get_db
from ..deps import require_admin
from ..models.admin import AdminUser
from ..models.auth_schemas import LoginRequest, MeResponse

router = APIRouter(prefix="/api/auth", tags=["auth"])
log = logging.getLogger("auth")


COOKIE_NAME = "admin_session"


def _ensure_default_admin(db: Session) -> None:
    exists = db.execute(select(AdminUser).limit(1)).scalar_one_or_none()
    if exists:
        return
    if not settings.admin_password:
        log.warning("ADMIN_PASSWORD is not set; no admin user created (set ADMIN_PASSWORD and restart).")
        return

    now = datetime.now(timezone.utc)
    user = AdminUser(
        username=settings.admin_username,
        password_hash=hash_password(settings.admin_password),
        created_at=now,
        updated_at=now,
    )
    db.add(user)
    db.commit()
    log.warning("Default admin user created username=%s (please change password).", settings.admin_username)


@router.post("/login", response_model=MeResponse)
def login(payload: LoginRequest, response: Response, db: Session = Depends(get_db)):
    _ensure_default_admin(db)

    user = db.execute(select(AdminUser).where(AdminUser.username == payload.username)).scalar_one_or_none()
    if not user or not verify_password(payload.password, user.password_hash):
        raise HTTPException(status_code=401, detail="Invalid credentials")

    token = create_session_token(user.id, user.username)
    response.set_cookie(
        key=COOKIE_NAME,
        value=token,
        httponly=True,
        secure=bool(settings.cookie_secure),
        samesite="lax",
        max_age=int(settings.session_max_age_seconds),
        path="/",
    )
    return MeResponse(id=user.id, username=user.username)


@router.post("/logout")
def logout(response: Response):
    response.delete_cookie(key=COOKIE_NAME, path="/")
    return {"status": "ok"}


@router.get("/me", response_model=MeResponse, dependencies=[Depends(require_admin)])
def me(request: Request, db: Session = Depends(get_db)):
    admin = getattr(request.state, "admin_user", None)
    if not admin:
        raise HTTPException(status_code=401, detail="Not authenticated")
    if admin.get("uid") == 0:
        return MeResponse(id=0, username="token")
    user = db.get(AdminUser, int(admin["uid"]))
    if not user:
        raise HTTPException(status_code=401, detail="Not authenticated")
    return MeResponse(id=user.id, username=user.username)
