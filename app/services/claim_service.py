"""
Claim service — GigShield AI Phase 2
Orchestrates: fraud check → payout calculation → DB persistence → mock UPI payout.
"""
from __future__ import annotations

import uuid
from datetime import datetime, timezone
from typing import Any

from sqlalchemy.orm import Session

from app.core.config import get_settings
from app.models.models import ClaimDB, PayoutDB, PolicyDB, UserDB
from app.services.fraud_service import run_fraud_check


def _calculate_payout(
    policy: PolicyDB,
    disruption_hours: float,
    fraud_score: float,
    user: UserDB,
) -> float:
    """
    Parametric payout formula:
      payout = min(hourly_income * disruption_hours, max_payout) * (1 - fraud_penalty)
    Fraud penalty reduces payout proportionally when score is in the review band.
    """
    hourly_income = (user.avg_daily_income or 700) / (user.active_hours or 10)
    raw_payout = min(hourly_income * disruption_hours, policy.max_payout)
    # Partial fraud penalty for review band (0.35–0.65)
    fraud_penalty = max(0.0, (fraud_score - 0.35) / 0.30) * 0.5 if 0.35 < fraud_score <= 0.65 else 0.0
    return round(raw_payout * (1 - fraud_penalty), 2)


def _mock_razorpay_payout(upi_id: str, amount: float) -> str:
    """Simulate Razorpay sandbox payout and return a reference ID."""
    return f"pout_{uuid.uuid4().hex[:16]}"


def create_claim_from_request(
    db: Session,
    user: UserDB,
    policy: PolicyDB,
    trigger_type: str,
    trigger_value: float,
    disruption_hours: float,
    zone: str,
    auto_initiated: bool = True,
) -> dict[str, Any]:
    """
    Full claim lifecycle:
    1. Fraud check
    2. Hard block if verdict == 'reject'
    3. Payout calculation
    4. Persist ClaimDB
    5. Persist PayoutDB + mock Razorpay call
    6. Return structured result
    """
    settings = get_settings()

    fraud = run_fraud_check(
        db,
        user_id=user.id,
        trigger_type=trigger_type,
        trigger_value=trigger_value,
        zone=zone,
        gps_tolerance_km=settings.GPS_ZONE_TOLERANCE_KM,
    )

    if fraud["verdict"] == "reject":
        claim_id = f"GS-CLM-{datetime.utcnow().strftime('%Y%m%d')}-{uuid.uuid4().hex[:8].upper()}"
        claim = ClaimDB(
            id=claim_id,
            policy_id=policy.id,
            user_id=user.id,
            trigger_type=trigger_type,
            trigger_value=trigger_value,
            trigger_zone=zone,
            disruption_hours=disruption_hours,
            fraud_score=fraud["fraud_score"],
            payout_amount=0.0,
            status="blocked",
            auto_initiated=auto_initiated,
            gps_mismatch_score=fraud.get("gps_mismatch_score", 0.0),
            gps_mismatch_flag=fraud.get("gps_mismatch_flag", False),
            repeated_claim_flag=fraud.get("repeated_claim_flag", False),
            time_anomaly_score=fraud.get("time_anomaly_score", 0.0),
            fraud_flags_json=str(fraud.get("flags", [])),
        )
        db.add(claim)
        db.commit()
        return {"status": "blocked", "reason": ", ".join(fraud["flags"]), **fraud,
                "claim_id": claim_id, "fraud_result": fraud}

    payout_amount = _calculate_payout(policy, disruption_hours, fraud["fraud_score"], user)
    claim_status = "approved" if fraud["verdict"] == "clean" else "review"

    claim_id = f"GS-CLM-{datetime.utcnow().strftime('%Y%m%d')}-{uuid.uuid4().hex[:8].upper()}"
    now = datetime.now(timezone.utc)

    claim = ClaimDB(
        id=claim_id,
        policy_id=policy.id,
        user_id=user.id,
        trigger_type=trigger_type,
        trigger_value=trigger_value,
        trigger_zone=zone,
        disruption_hours=disruption_hours,
        fraud_score=fraud["fraud_score"],
        payout_amount=payout_amount,
        status=claim_status,
        auto_initiated=auto_initiated,
        created_at=now,
        paid_at=now if claim_status == "approved" else None,
        gps_mismatch_score=fraud.get("gps_mismatch_score", 0.0),
        gps_mismatch_flag=fraud.get("gps_mismatch_flag", False),
        repeated_claim_flag=fraud.get("repeated_claim_flag", False),
        time_anomaly_score=fraud.get("time_anomaly_score", 0.0),
        fraud_flags_json=str(fraud.get("flags", [])),
    )
    db.add(claim)

    payout_ref = None
    if claim_status == "approved":
        payout_ref = _mock_razorpay_payout(policy.upi_id, payout_amount)
        payout = PayoutDB(
            id=f"GS-PAY-{uuid.uuid4().hex[:12].upper()}",
            claim_id=claim_id,
            user_id=user.id,
            amount=payout_amount,
            upi_id=policy.upi_id,
            method=policy.payment_method,
            razorpay_ref=payout_ref,
            status="processed",
            created_at=now,
        )
        db.add(payout)

    db.commit()

    return {
        "claim_id": claim_id,
        "claim_status": claim_status,
        "payout_amount": payout_amount,
        "payout_ref": payout_ref,
        "fraud_result": fraud,
    }
