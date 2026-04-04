"""Admin-only dashboard APIs."""
from typing import Annotated, Any

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.core.deps import get_db, require_admin
from app.models.models import ClaimDB, PolicyDB, UserDB
from app.services.analytics_service import build_admin_analytics

router = APIRouter(prefix="/admin", tags=["admin"])


@router.get("/users")
def admin_users(
    _: Annotated[UserDB, Depends(require_admin)],
    db: Session = Depends(get_db),
):
    users = db.query(UserDB).order_by(UserDB.id).all()
    return {
        "users": [
            {
                "id": u.id,
                "name": u.name,
                "phone": u.phone,
                "role": u.role,
                "platform": u.platform,
                "zone": u.zone,
                "city": u.city,
                "avg_daily_income": u.avg_daily_income,
                "active_hours": u.active_hours,
                "created_at": u.created_at.isoformat() if u.created_at else None,
            }
            for u in users
        ],
        "total": len(users),
    }


@router.get("/claims")
def admin_claims(
    _: Annotated[UserDB, Depends(require_admin)],
    db: Session = Depends(get_db),
):
    claims = db.query(ClaimDB).order_by(ClaimDB.created_at.desc()).all()
    users = {u.id: u.name for u in db.query(UserDB).all()}
    rows: list[dict[str, Any]] = []
    for c in claims:
        rows.append(
            {
                "id": c.id,
                "worker": users.get(c.user_id, "Unknown"),
                "user_id": c.user_id,
                "trigger_type": c.trigger_type,
                "trigger_value": c.trigger_value,
                "trigger_zone": c.trigger_zone,
                "disruption_hours": c.disruption_hours,
                "fraud_score": c.fraud_score,
                "gps_mismatch_flag": c.gps_mismatch_flag,
                "repeated_claim_flag": c.repeated_claim_flag,
                "payout_amount": c.payout_amount,
                "status": c.status,
                "auto_initiated": c.auto_initiated,
                "created_at": c.created_at.strftime("%Y-%m-%d %H:%M") if c.created_at else None,
            }
        )
    return {"claims": rows, "total": len(rows)}


@router.get("/analytics")
def admin_analytics(
    _: Annotated[UserDB, Depends(require_admin)],
    db: Session = Depends(get_db),
):
    return build_admin_analytics(db)
