"""FastAPI dependencies: DB session, JWT auth, RBAC."""
from typing import Annotated, Generator, Optional

from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from sqlalchemy.orm import Session

from app.core.security import decode_token_safe
from app.models.database import SessionLocal
from app.models.models import UserDB

security = HTTPBearer(auto_error=False)


def get_db() -> Generator[Session, None, None]:
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


def _bearer_token(
    credentials: Optional[HTTPAuthorizationCredentials] = Depends(security),
) -> str:
    if credentials is None or not credentials.credentials:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Not authenticated",
            headers={"WWW-Authenticate": "Bearer"},
        )
    return credentials.credentials


def get_token_payload(token: Annotated[str, Depends(_bearer_token)]) -> dict:
    payload = decode_token_safe(token)
    if payload is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or expired token",
            headers={"WWW-Authenticate": "Bearer"},
        )
    if payload.get("type") != "access":
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid token type (access token required)",
        )
    return payload


def get_current_user(
    db: Annotated[Session, Depends(get_db)],
    payload: Annotated[dict, Depends(get_token_payload)],
) -> UserDB:
    user_id = payload.get("sub")
    if user_id is None:
        raise HTTPException(status_code=401, detail="Invalid token payload")
    try:
        uid = int(user_id)
    except (TypeError, ValueError):
        raise HTTPException(status_code=401, detail="Invalid subject")
    user = db.query(UserDB).filter(UserDB.id == uid).first()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    return user


def require_admin(current: Annotated[UserDB, Depends(get_current_user)]) -> UserDB:
    if current.role != "admin":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Admin role required",
        )
    return current


def require_worker_or_admin(current: Annotated[UserDB, Depends(get_current_user)]) -> UserDB:
    if current.role not in ("worker", "admin"):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Worker or admin role required",
        )
    return current


def require_worker(current: Annotated[UserDB, Depends(get_current_user)]) -> UserDB:
    if current.role != "worker":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Worker role required",
        )
    return current


def assert_self_or_admin(user_id: int, current: UserDB) -> None:
    """Raise 403 unless current user is admin or matches user_id."""
    if current.role != "admin" and current.id != user_id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Cannot access another user's resources",
        )
