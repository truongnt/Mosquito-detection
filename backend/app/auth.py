from __future__ import annotations

from datetime import datetime, timezone

from itsdangerous import BadSignature, BadTimeSignature, URLSafeTimedSerializer
from passlib.context import CryptContext

from .config import settings


pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")


def hash_password(password: str) -> str:
    return pwd_context.hash(password)


def verify_password(password: str, password_hash: str) -> bool:
    return pwd_context.verify(password, password_hash)


def _serializer() -> URLSafeTimedSerializer:
    return URLSafeTimedSerializer(settings.session_secret, salt="admin-session")


def create_session_token(user_id: int, username: str) -> str:
    payload = {
        "uid": user_id,
        "u": username,
        "iat": int(datetime.now(timezone.utc).timestamp()),
    }
    return _serializer().dumps(payload)


def verify_session_token(token: str) -> dict | None:
    try:
        payload = _serializer().loads(token, max_age=settings.session_max_age_seconds)
        if not isinstance(payload, dict):
            return None
        if "uid" not in payload or "u" not in payload:
            return None
        return payload
    except (BadTimeSignature, BadSignature):
        return None

