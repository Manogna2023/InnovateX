"""Pydantic schemas for policy management — GigShield AI Phase 2."""
from typing import Optional
from pydantic import BaseModel, Field


class PolicyCreateRequest(BaseModel):
    user_id: int
    tier: str = Field(..., description="basic | standard | pro")
    payment_method: str = Field("upi", description="upi | wallet")
    upi_id: Optional[str] = None
