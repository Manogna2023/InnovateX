"""Pydantic request/response schemas for auth endpoints — GigShield AI Phase 2."""
from typing import Optional
from pydantic import BaseModel, Field


class RegisterRequest(BaseModel):
    name: str = Field(..., min_length=2, max_length=100)
    phone: str = Field(..., min_length=10, max_length=15)
    password: str = Field(..., min_length=6)
    platform: str = Field(..., description="Zomato | Swiggy | Zepto | Blinkit | Amazon | Dunzo")
    city: str = Field(..., min_length=2)
    zone: Optional[str] = None
    avg_daily_income: float = Field(700, ge=100, le=10000)
    active_hours: float = Field(10, ge=4, le=16)


class LoginRequest(BaseModel):
    phone: str
    password: str


class RefreshRequest(BaseModel):
    refresh_token: str


class TokenResponse(BaseModel):
    access_token: str
    refresh_token: str
    token_type: str = "bearer"
    expires_in: int


class UserPublic(BaseModel):
    id: int
    name: str
    phone: str
    role: str
    zone: Optional[str]
    city: Optional[str]
    platform: Optional[str]
    avg_daily_income: float
    active_hours: float

    class Config:
        from_attributes = True
