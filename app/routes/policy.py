"""Policy pricing and lifecycle."""
import uuid
from datetime import datetime, timedelta
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session

from app.core.deps import assert_self_or_admin, get_db, get_current_user
from app.models.models import PolicyDB, UserDB
from app.schemas.policy import PolicyCreateRequest
from app.services.ml_sim import TIER_CONFIG, lightgbm_premium_model, prophet_risk_forecast

router = APIRouter(prefix="/policy", tags=["policy"])


@router.post("/calculate-premium")
def calculate_premium(
    current: Annotated[UserDB, Depends(get_current_user)],
    db: Session = Depends(get_db),
    user_id: int = Query(..., ge=1),
    tier: str = Query(...),
):
    assert_self_or_admin(user_id, current)
    if tier not in TIER_CONFIG:
        raise HTTPException(400, "Invalid tier. Choose: basic, standard, pro")
    user = db.query(UserDB).filter(UserDB.id == user_id).first()
    if not user:
        raise HTTPException(404, "User not found")
    pricing = lightgbm_premium_model(user, tier)
    forecast = prophet_risk_forecast(user.zone, user.city)
    return {"pricing": pricing, "risk_forecast": forecast, "tier": tier}


@router.post("/create")
def create_policy(
    req: PolicyCreateRequest,
    current: Annotated[UserDB, Depends(get_current_user)],
    db: Session = Depends(get_db),
):
    assert_self_or_admin(req.user_id, current)
    user = db.query(UserDB).filter(UserDB.id == req.user_id).first()
    if not user:
        raise HTTPException(404, "User not found")
    existing = (
        db.query(PolicyDB)
        .filter(PolicyDB.user_id == req.user_id, PolicyDB.status == "active")
        .first()
    )
    if existing:
        raise HTTPException(400, "Worker already has an active policy this week")
    pricing = lightgbm_premium_model(user, req.tier)
    week_start = datetime.utcnow().replace(hour=0, minute=0, second=0, microsecond=0)
    policy = PolicyDB(
        id=f"GS-POL-{datetime.utcnow().strftime('%Y%m%d')}-{uuid.uuid4().hex[:8].upper()}",
        user_id=req.user_id,
        tier=req.tier,
        base_premium=pricing["base_premium"],
        ai_premium=pricing["ai_adjusted_premium"],
        max_payout=pricing["max_payout"],
        coverage_hours=pricing["coverage_hours"],
        payment_method=req.payment_method,
        upi_id=req.upi_id or f"{user.name.lower().replace(' ', '')}{user.phone[-4:]}@upi",
        week_start=week_start,
        week_end=week_start + timedelta(days=7),
    )
    db.add(policy)
    db.commit()
    db.refresh(policy)
    return {
        "policy_id": policy.id,
        "message": f"Policy activated. ₹{policy.ai_premium} paid via {req.payment_method}.",
        "premium_paid": policy.ai_premium,
        "max_payout": policy.max_payout,
        "valid_from": policy.week_start.strftime("%Y-%m-%d"),
        "valid_until": policy.week_end.strftime("%Y-%m-%d"),
        "razorpay_sandbox_ref": f"pay_{uuid.uuid4().hex[:16]}",
        "tier": policy.tier,
    }


@router.get("/{user_id}")
def get_policy(
    user_id: int,
    current: Annotated[UserDB, Depends(get_current_user)],
    db: Session = Depends(get_db),
):
    assert_self_or_admin(user_id, current)
    policy = (
        db.query(PolicyDB)
        .filter(PolicyDB.user_id == user_id, PolicyDB.status == "active")
        .first()
    )
    if not policy:
        raise HTTPException(404, "No active policy found")
    return {
        "id": policy.id,
        "tier": policy.tier,
        "ai_premium": policy.ai_premium,
        "max_payout": policy.max_payout,
        "coverage_hours": policy.coverage_hours,
        "status": policy.status,
        "week_start": policy.week_start.strftime("%Y-%m-%d") if policy.week_start else None,
        "week_end": policy.week_end.strftime("%Y-%m-%d") if policy.week_end else None,
        "upi_id": policy.upi_id,
        "payment_method": policy.payment_method,
    }
