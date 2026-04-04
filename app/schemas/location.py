"""Pydantic schema for GPS location logging — GigShield AI Phase 2."""
from pydantic import BaseModel, Field


class LocationUpdateRequest(BaseModel):
    latitude: float = Field(..., ge=-90, le=90)
    longitude: float = Field(..., ge=-180, le=180)
