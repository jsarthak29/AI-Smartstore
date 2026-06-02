from datetime import datetime, timedelta, timezone
from typing import Any

from jose import JWTError, jwt
from passlib.context import CryptContext

from app.config import get_settings

settings = get_settings()

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")


def hash_password(password: str) -> str:
    return pwd_context.hash(password)


def verify_password(password: str, hashed: str) -> bool:
    return pwd_context.verify(password, hashed)


def _encode(payload: dict[str, Any], expires_delta: timedelta) -> str:
    to_encode = payload.copy()
    to_encode["exp"] = datetime.now(timezone.utc) + expires_delta
    return jwt.encode(to_encode, settings.JWT_SECRET, algorithm=settings.JWT_ALGORITHM)


def create_access_token(user_id: int, tenant_id: int, role: str) -> str:
    return _encode(
        {"sub": str(user_id), "tid": tenant_id, "role": role, "type": "access"},
        timedelta(minutes=settings.JWT_ACCESS_MINUTES),
    )


def create_refresh_token(user_id: int, tenant_id: int) -> str:
    return _encode(
        {"sub": str(user_id), "tid": tenant_id, "type": "refresh"},
        timedelta(days=settings.JWT_REFRESH_DAYS),
    )


def decode_token(token: str) -> dict[str, Any]:
    try:
        return jwt.decode(token, settings.JWT_SECRET, algorithms=[settings.JWT_ALGORITHM])
    except JWTError as exc:
        raise ValueError("invalid token") from exc
