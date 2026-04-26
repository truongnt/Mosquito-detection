from fastapi import Cookie, Header, HTTPException, Request

from .config import settings
from .auth import verify_session_token


def require_admin(
    request: Request,
    admin_session: str | None = Cookie(default=None),
    authorization: str | None = Header(default=None),
) -> None:
    if admin_session:
        payload = verify_session_token(admin_session)
        if payload:
            request.state.admin_user = payload
            return

    if settings.allow_admin_token:
        if not authorization or not authorization.startswith("Bearer "):
            raise HTTPException(status_code=401, detail="Missing admin credentials")
        token = authorization.removeprefix("Bearer ").strip()
        if token != settings.admin_token:
            raise HTTPException(status_code=403, detail="Invalid admin token")
        request.state.admin_user = {"uid": 0, "u": "token"}
        return

    raise HTTPException(status_code=401, detail="Not authenticated")
