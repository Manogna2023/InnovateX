"""JWT authentication routes."""
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Request, status
from sqlalchemy.orm import Session

from app.core.config import get_settings
from app.core.deps import assert_self_or_admin, get_db, get_current_user
from app.core.limiter import limiter
from app.core.security import create_token, decode_token_safe, verify_password
from app.models.models import UserDB
from app.schemas.auth import LoginRequest, RefreshRequest, RegisterRequest, TokenResponse, UserPublic
from app.services.auth_service import issue_token_pair, register_user

router = APIRouter(prefix="/auth", tags=["auth"])


@router.post("/register")
def register(req: RegisterRequest, db: Session = Depends(get_db)):
    if db.query(UserDB).filter(UserDB.phone == req.phone).first():
        raise HTTPException(status.HTTP_400_BAD_REQUEST, "Phone number already registered")
    user = register_user(
        db,
        name=req.name,
        phone=req.phone,
        password=req.password,
        platform=req.platform,
        city=req.city,
        zone=req.zone,
        avg_daily_income=req.avg_daily_income,
        active_hours=req.active_hours,
    )
    return {
        "message": "Registered successfully. Use POST /auth/login with your password.",
        "user_id": user.id,
    }


@router.post("/send-otp")
def send_otp_deprecated():
    raise HTTPException(
        status.HTTP_410_GONE,
        "OTP authentication removed. Use POST /auth/login with phone + password.",
    )


@router.post("/verify-otp")
def verify_otp_deprecated():
    raise HTTPException(
        status.HTTP_410_GONE,
        "OTP authentication removed. Use POST /auth/login and JWT Bearer tokens.",
    )


@router.post("/login")
@limiter.limit("30/minute")
def login(request: Request, req: LoginRequest, db: Session = Depends(get_db)):
    user = db.query(UserDB).filter(UserDB.phone == req.phone).first()
    if not user or not user.password_hash:
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "Invalid phone or password")
    if not verify_password(req.password, user.password_hash):
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "Invalid phone or password")
    tokens = issue_token_pair(user)
    settings = get_settings()
    return {
        **tokens,
        "expires_in": settings.ACCESS_TOKEN_EXPIRE_MINUTES * 60,
        "user": {
            "id": user.id,
            "name": user.name,
            "role": user.role,
            "zone": user.zone,
            "city": user.city,
            "platform": user.platform,
            "avg_daily_income": user.avg_daily_income,
        },
    }


@router.post("/refresh", response_model=TokenResponse)
def refresh_token(req: RefreshRequest, db: Session = Depends(get_db)):
    payload = decode_token_safe(req.refresh_token)
    if not payload or payload.get("type") != "refresh":
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "Invalid refresh token")
    try:
        uid = int(payload["sub"])
    except (KeyError, TypeError, ValueError):
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "Invalid refresh token")
    user = db.query(UserDB).filter(UserDB.id == uid).first()
    if not user:
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "User not found")
    tokens = issue_token_pair(user)
    settings = get_settings()
    return TokenResponse(
        access_token=tokens["access_token"],
        refresh_token=tokens["refresh_token"],
        token_type="bearer",
        expires_in=settings.ACCESS_TOKEN_EXPIRE_MINUTES * 60,
    )


@router.get("/user/{user_id}", response_model=UserPublic)
def get_user_profile(
    user_id: int,
    current: Annotated[UserDB, Depends(get_current_user)],
    db: Session = Depends(get_db),
):
    assert_self_or_admin(user_id, current)
    user = db.query(UserDB).filter(UserDB.id == user_id).first()
    if not user:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "User not found")
    return UserPublic(
        id=user.id,
        name=user.name,
        phone=user.phone,
        role=user.role,
        zone=user.zone,
        city=user.city,
        platform=user.platform,
        avg_daily_income=user.avg_daily_income,
        active_hours=user.active_hours,
    )


@router.get("/me", response_model=UserPublic)
def me(current: Annotated[UserDB, Depends(get_current_user)]):
    return UserPublic(
        id=current.id,
        name=current.name,
        phone=current.phone,
        role=current.role,
        zone=current.zone,
        city=current.city,
        platform=current.platform,
        avg_daily_income=current.avg_daily_income,
        active_hours=current.active_hours,
    )
