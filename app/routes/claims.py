"""Parametric claims."""
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.core.deps import assert_self_or_admin, get_current_user, get_db, require_admin
from app.models.models import ClaimDB, PolicyDB, UserDB
from app.schemas.claim import ClaimInitRequest
from app.services.claim_service import create_claim_from_request

router = APIRouter(tags=["claims"])


@router.post("/claims/initiate")
def initiate_claim(
    req: ClaimInitRequest,
    current: Annotated[UserDB, Depends(get_current_user)],
    db: Session = Depends(get_db),
):
    assert_self_or_admin(req.user_id, current)
    user = db.query(UserDB).filter(UserDB.id == req.user_id).first()
    if not user:
        raise HTTPException(404, "User not found")
    policy = (
        db.query(PolicyDB)
        .filter(PolicyDB.id == req.policy_id, PolicyDB.status == "active")
        .first()
    )
    if not policy:
        raise HTTPException(404, "No active policy found")

    result = create_claim_from_request(
        db,
        user,
        policy,
        req.trigger_type,
        req.trigger_value,
        req.disruption_hours,
        req.zone,
        auto_initiated=False,
    )
    if result.get("status") == "blocked":
        return result

    fr = result["fraud_result"]
    return {
        "claim_id": result["claim_id"],
        "status": result["claim_status"],
        "payout_amount": result["payout_amount"],
        "fraud_score": fr["fraud_score"],
        "fraud_verdict": fr["verdict"],
        "gps_match": fr["gps_match"],
        "gps_mismatch_score": fr.get("gps_mismatch_score"),
        "gps_mismatch_flag": fr.get("gps_mismatch_flag"),
        "repeated_claim_flag": fr.get("repeated_claim_flag"),
        "time_anomaly_score": fr.get("time_anomaly_score"),
        "flags": fr["flags"],
        "payout_ref": result.get("payout_ref"),
        "message": f"Claim {result['claim_status']}. ₹{result['payout_amount']} being sent to {policy.upi_id}",
    }


@router.get("/claims/{user_id}")
def get_claims(
    user_id: int,
    current: Annotated[UserDB, Depends(get_current_user)],
    db: Session = Depends(get_db),
):
    assert_self_or_admin(user_id, current)
    claims = (
        db.query(ClaimDB)
        .filter(ClaimDB.user_id == user_id)
        .order_by(ClaimDB.created_at.desc())
        .all()
    )
    result = []
    for c in claims:
        result.append(
            {
                "id": c.id,
                "trigger_type": c.trigger_type,
                "trigger_value": c.trigger_value,
                "trigger_zone": c.trigger_zone,
                "disruption_hours": c.disruption_hours,
                "fraud_score": c.fraud_score,
                "payout_amount": c.payout_amount,
                "status": c.status,
                "auto_initiated": c.auto_initiated,
                "gps_mismatch_flag": c.gps_mismatch_flag,
                "repeated_claim_flag": c.repeated_claim_flag,
                "created_at": c.created_at.strftime("%Y-%m-%d %H:%M") if c.created_at else None,
                "paid_at": c.paid_at.strftime("%Y-%m-%d %H:%M") if c.paid_at else None,
            }
        )
    return {"claims": result, "total": len(result)}


@router.get("/claims/admin/all")
def get_all_claims_legacy(
    _: Annotated[UserDB, Depends(require_admin)],
    db: Session = Depends(get_db),
):
    """Backward-compatible path; prefer GET /admin/claims."""
    claims = db.query(ClaimDB).order_by(ClaimDB.created_at.desc()).all()
    users = {u.id: u.name for u in db.query(UserDB).all()}
    result = []
    for c in claims:
        result.append(
            {
                "id": c.id,
                "worker": users.get(c.user_id, "Unknown"),
                "trigger_type": c.trigger_type,
                "trigger_value": c.trigger_value,
                "trigger_zone": c.trigger_zone,
                "disruption_hours": c.disruption_hours,
                "fraud_score": c.fraud_score,
                "payout_amount": c.payout_amount,
                "status": c.status,
                "created_at": c.created_at.strftime("%Y-%m-%d %H:%M") if c.created_at else None,
            }
        )
    return {"claims": result, "total": len(result)}
