"""
Analytics service — GigShield AI Phase 2
Builds admin KPI dashboard: loss ratios, fraud stats, payout summaries,
top disruption zones, and a 7-day claims sparkline.
"""
from __future__ import annotations

from collections import Counter
from datetime import datetime, timedelta, timezone
from typing import Any

from sqlalchemy.orm import Session

from app.models.models import ClaimDB, PayoutDB, PolicyDB, UserDB


def build_admin_analytics(db: Session) -> dict[str, Any]:
    workers = db.query(UserDB).filter(UserDB.role == "worker").count()
    active_policies = db.query(PolicyDB).filter(PolicyDB.status == "active").count()

    claims = db.query(ClaimDB).all()
    total_claims = len(claims)
    approved = [c for c in claims if c.status == "approved"]
    blocked  = [c for c in claims if c.status == "blocked"]
    review   = [c for c in claims if c.status == "review"]

    payouts = db.query(PayoutDB).filter(PayoutDB.status == "processed").all()
    total_payout_amount = sum(p.amount for p in payouts)

    # Premium collected (sum of ai_premium for active + expired policies)
    all_policies = db.query(PolicyDB).all()
    total_premiums = sum(p.ai_premium for p in all_policies)

    # Loss ratio = payouts / premiums
    loss_ratio = (total_payout_amount / total_premiums) if total_premiums > 0 else 0.0

    # Top zones by claim frequency
    zone_counts = Counter(c.trigger_zone for c in claims if c.trigger_zone)
    top_zones = [{"zone": z, "claims": n} for z, n in zone_counts.most_common(5)]

    # Top trigger types
    trigger_counts = Counter(c.trigger_type for c in claims if c.trigger_type)
    top_triggers = [{"trigger": t, "count": n} for t, n in trigger_counts.most_common(5)]

    # 7-day claims sparkline
    today = datetime.now(timezone.utc).date()
    sparkline = []
    for i in range(6, -1, -1):
        day = today - timedelta(days=i)
        day_claims = [
            c for c in claims
            if c.created_at and c.created_at.date() == day
        ]
        sparkline.append({
            "date": day.strftime("%b %d"),
            "claims": len(day_claims),
            "approved": len([x for x in day_claims if x.status == "approved"]),
            "payout": round(sum(x.payout_amount for x in day_claims if x.status == "approved"), 2),
        })

    # Avg fraud score
    fraud_scores = [c.fraud_score for c in claims if c.fraud_score is not None]
    avg_fraud = round(sum(fraud_scores) / len(fraud_scores), 3) if fraud_scores else 0.0

    return {
        "total_workers": workers,
        "active_policies": active_policies,
        "total_claims": total_claims,
        "approved_claims": len(approved),
        "blocked_claims": len(blocked),
        "review_claims": len(review),
        "fraud_blocked": len(blocked),
        "total_payouts_amount": round(total_payout_amount, 2),
        "total_premiums_collected": round(total_premiums, 2),
        "loss_ratio": round(loss_ratio, 4),
        "avg_fraud_score": avg_fraud,
        "top_zones": top_zones,
        "top_triggers": top_triggers,
        "sparkline_7d": sparkline,
        "generated_at": datetime.now(timezone.utc).isoformat(),
    }
