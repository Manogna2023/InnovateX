"""Auth service — GigShield AI Phase 2."""
from __future__ import annotations

from sqlalchemy.orm import Session

from app.core.security import create_token, hash_password
from app.models.models import UserDB


def register_user(
    db: Session,
    name: str,
    phone: str,
    password: str,
    platform: str,
    city: str,
    zone: str | None = None,
    avg_daily_income: float = 700,
    active_hours: float = 10,
) -> UserDB:
    user = UserDB(
        name=name,
        phone=phone,
        password_hash=hash_password(password),
        platform=platform,
        city=city,
        zone=zone or city,
        avg_daily_income=avg_daily_income,
        active_hours=active_hours,
        role="worker",
    )
    db.add(user)
    db.commit()
    db.refresh(user)
    return user


def issue_token_pair(user: UserDB) -> dict[str, str]:
    access  = create_token(str(user.id), user.role, "access")
    refresh = create_token(str(user.id), user.role, "refresh")
    return {"access_token": access, "refresh_token": refresh, "token_type": "bearer"}
