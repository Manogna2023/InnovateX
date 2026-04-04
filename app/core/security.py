"""Password hashing (bcrypt) and JWT access/refresh tokens."""
from datetime import datetime, timedelta, timezone
from typing import Any, Literal, Optional

from jose import JWTError, jwt
from passlib.context import CryptContext

from app.core.config import get_settings

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")


def verify_password(plain: str, hashed: str) -> bool:
    return pwd_context.verify(plain, hashed)


def hash_password(password: str) -> str:
    return pwd_context.hash(password)


def create_token(
    subject: str,
    role: str,
    token_type: Literal["access", "refresh"],
    expires_delta: Optional[timedelta] = None,
) -> str:
    settings = get_settings()
    now = datetime.now(timezone.utc)
    if expires_delta is None:
        if token_type == "access":
            expires_delta = timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES)
        else:
            expires_delta = timedelta(days=settings.REFRESH_TOKEN_EXPIRE_DAYS)
    expire = now + expires_delta
    to_encode: dict[str, Any] = {
        "sub": subject,
        "role": role,
        "type": token_type,
        "exp": expire,
        "iat": now,
    }
    return jwt.encode(to_encode, settings.SECRET_KEY, algorithm=settings.ALGORITHM)


def decode_token(token: str) -> dict[str, Any]:
    settings = get_settings()
    return jwt.decode(token, settings.SECRET_KEY, algorithms=[settings.ALGORITHM])


def decode_token_safe(token: str) -> Optional[dict[str, Any]]:
    try:
        return decode_token(token)
    except JWTError:
        return None
