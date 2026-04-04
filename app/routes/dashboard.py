"""Worker and admin dashboards."""
from datetime import datetime, timedelta
from typing import Annotated, Any, Optional

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.core.deps import assert_self_or_admin, get_current_user, get_db, require_admin
from app.models.models import ClaimDB, LocationLogDB, PayoutDB, PolicyDB, RiskLogDB, UserDB
from app.services.analytics_service import build_admin_analytics
from app.services.ml_sim import prophet_risk_forecast

router = APIRouter(prefix="/dashboard", tags=["dashboard"])


def _last_disruption_for_zone(db: Session, zone: str) -> Optional[dict[str, Any]]:
    log = (
        db.query(RiskLogDB)
        .filter(RiskLogDB.zone == zone, RiskLogDB.breached.is_(True))
        .order_by(RiskLogDB.checked_at.desc())
        .first()
    )
    if not log:
        return None
    return {
        "trigger_type": log.trigger_type,
        "raw_value": log.raw_value,
        "checked_at": log.checked_at.isoformat() if log.checked_at else None,
        "zone": log.zone,
    }


@router.get("/worker/{user_id}")
def worker_dashboard(
    user_id: int,
    current: Annotated[UserDB, Depends(get_current_user)],
    db: Session = Depends(get_db),
):
    assert_self_or_admin(user_id, current)
    user = db.query(UserDB).filter(UserDB.id == user_id).first()
    if not user:
        raise HTTPException(404, "User not found")
    policy = (
        db.query(PolicyDB)
        .filter(PolicyDB.user_id == user_id, PolicyDB.status == "active")
        .first()
    )
    claims = db.query(ClaimDB).filter(ClaimDB.user_id == user_id).all()
    payouts = db.query(PayoutDB).filter(
        PayoutDB.user_id == user_id, PayoutDB.status == "processed"
    ).all()
    total_protected = sum(p.amount for p in payouts)
    this_week_claims = [
        c for c in claims if c.created_at and c.created_at > datetime.utcnow() - timedelta(days=7)
    ]
    risk = prophet_risk_forecast(user.zone, user.city)

    loc = (
        db.query(LocationLogDB)
        .filter(LocationLogDB.user_id == user_id)
        .order_by(LocationLogDB.timestamp.desc())
        .first()
    )
    latest_gps = None
    if loc:
        latest_gps = {
            "latitude": loc.latitude,
            "longitude": loc.longitude,
            "timestamp": loc.timestamp.isoformat() if loc.timestamp else None,
        }

    last_disruption = _last_disruption_for_zone(db, user.zone)

    return {
        "worker": {
            "id": user.id,
            "name": user.name,
            "zone": user.zone,
            "city": user.city,
            "platform": user.platform,
            "avg_daily_income": user.avg_daily_income,
        },
        "policy": {
            "id": policy.id if policy else None,
            "tier": policy.tier if policy else None,
            "ai_premium": policy.ai_premium if policy else None,
            "max_payout": policy.max_payout if policy else None,
            "week_end": policy.week_end.strftime("%b %d, %Y") if policy and policy.week_end else None,
            "active": policy is not None,
        },
        "stats": {
            "total_claims": len(claims),
            "approved_claims": len([c for c in claims if c.status == "approved"]),
            "this_week_claims": len(this_week_claims),
            "total_income_protected": round(total_protected, 2),
        },
        "risk_forecast": risk,
        "real_time_risk_score": risk.get("risk_score"),
        "latest_gps": latest_gps,
        "last_disruption": last_disruption,
    }


@router.get("/admin")
def admin_dashboard_legacy(
    _: Annotated[UserDB, Depends(require_admin)],
    db: Session = Depends(get_db),
):
    """Same metrics as GET /admin/analytics; kept for frontend compatibility."""
    return build_admin_analytics(db)
