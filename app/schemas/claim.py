"""Pydantic schemas for claims and zone trigger check — GigShield AI Phase 2."""
from pydantic import BaseModel, Field


class ClaimInitRequest(BaseModel):
    user_id: int
    policy_id: str
    trigger_type: str = Field(
        ...,
        description="heavy_rain | extreme_heat | flood | severe_aqi | curfew | app_outage",
    )
    trigger_value: float = Field(..., description="Raw sensor/API reading (mm, °C, AQI…)")
    disruption_hours: float = Field(4.0, ge=0.5, le=12)
    zone: str = Field("unknown", description="Delivery zone where disruption occurred")


class TriggerCheckRequest(BaseModel):
    user_id: int
    zone: str
    city: str = ""
