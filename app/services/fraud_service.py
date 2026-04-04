"""
Fraud detection service — GigShield AI Phase 2
Multi-signal fraud scoring:
  1. GPS proximity check  (was worker actually in the affected zone?)
  2. Duplicate claim gate (same trigger type in same zone within 24h)
  3. Time anomaly score   (claims filed at 3 AM for a "noon rainstorm" are suspicious)
  4. Velocity check       (>3 claims in 7 days triggers review)
  5. Trigger value sanity (is the rainfall figure plausible?)
"""
from __future__ import annotations

import math
from datetime import datetime, timedelta, timezone
from typing import Any

from sqlalchemy.orm import Session

from app.models.models import ClaimDB, LocationLogDB


def _haversine_km(lat1: float, lng1: float, lat2: float, lng2: float) -> float:
    """Great-circle distance in kilometres."""
    R = 6371.0
    φ1, φ2 = math.radians(lat1), math.radians(lat2)
    Δφ = math.radians(lat2 - lat1)
    Δλ = math.radians(lng2 - lng1)
    a = math.sin(Δφ / 2) ** 2 + math.cos(φ1) * math.cos(φ2) * math.sin(Δλ / 2) ** 2
    return R * 2 * math.atan2(math.sqrt(a), math.sqrt(1 - a))


# Approximate zone centroids (lat, lng) for GPS proximity check
_ZONE_CENTROIDS: dict[str, tuple[float, float]] = {
    "velachery":          (12.9788, 80.2200),
    "t.nagar":            (13.0418, 80.2341),
    "t nagar":            (13.0418, 80.2341),
    "anna nagar":         (13.0850, 80.2101),
    "adyar":              (13.0050, 80.2570),
    "tambaram":           (12.9249, 80.1000),
    "perambur":           (13.1182, 80.2348),
    "kodambakkam":        (13.0530, 80.2310),
    "dharavi":            (19.0400, 72.8560),
    "bandra":             (19.0596, 72.8295),
    "andheri":            (19.1136, 72.8697),
    "kurla":              (19.0726, 72.8792),
    "koramangala":        (12.9352, 77.6245),
    "whitefield":         (12.9698, 77.7499),
    "connaught place":    (28.6315, 77.2167),
    "lajpat nagar":       (28.5677, 77.2432),
}


def _gps_check(
    db: Session,
    user_id: int,
    zone: str,
    tolerance_km: float = 8.0,
) -> dict[str, Any]:
    """Check if latest GPS log is within tolerance of the claimed zone."""
    loc = (
        db.query(LocationLogDB)
        .filter(LocationLogDB.user_id == user_id)
        .order_by(LocationLogDB.timestamp.desc())
        .first()
    )
    if not loc:
        return {"gps_match": None, "gps_mismatch_score": 0.0, "gps_mismatch_flag": False,
                "note": "No GPS history — cannot verify location"}

    centroid = _ZONE_CENTROIDS.get(zone.lower().strip())
    if not centroid:
        return {"gps_match": None, "gps_mismatch_score": 0.0, "gps_mismatch_flag": False,
                "note": "Zone centroid not in reference database"}

    dist_km = _haversine_km(loc.latitude, loc.longitude, centroid[0], centroid[1])
    match = dist_km <= tolerance_km
    mismatch_score = min(dist_km / (tolerance_km * 3), 1.0) if not match else 0.0

    return {
        "gps_match": match,
        "gps_mismatch_score": round(mismatch_score, 3),
        "gps_mismatch_flag": not match,
        "distance_km": round(dist_km, 2),
        "note": f"Worker {dist_km:.1f}km from zone centre (tolerance {tolerance_km}km)",
    }


def _duplicate_check(
    db: Session,
    user_id: int,
    trigger_type: str,
    zone: str,
    window_hours: int = 24,
) -> dict[str, Any]:
    cutoff = datetime.now(timezone.utc) - timedelta(hours=window_hours)
    existing = (
        db.query(ClaimDB)
        .filter(
            ClaimDB.user_id == user_id,
            ClaimDB.trigger_type == trigger_type,
            ClaimDB.trigger_zone == zone,
            ClaimDB.created_at >= cutoff,
        )
        .first()
    )
    return {
        "repeated_claim_flag": existing is not None,
        "duplicate_claim_id": existing.id if existing else None,
    }


def _velocity_check(db: Session, user_id: int) -> dict[str, Any]:
    """More than 3 claims in 7 days raises a soft flag."""
    cutoff = datetime.now(timezone.utc) - timedelta(days=7)
    count = (
        db.query(ClaimDB)
        .filter(ClaimDB.user_id == user_id, ClaimDB.created_at >= cutoff)
        .count()
    )
    return {"weekly_claim_count": count, "velocity_flag": count >= 3}


def _time_anomaly(trigger_type: str) -> float:
    """
    Weather disruptions should align with daytime delivery hours.
    Filing a rain claim at 3 AM gets a minor anomaly flag.
    """
    hour = datetime.now().hour
    weather_types = {"heavy_rain", "extreme_heat", "flood", "severe_aqi", "thunderstorm"}
    if trigger_type in weather_types and (hour < 5 or hour > 23):
        return 0.25  # Minor flag
    return 0.0


def _value_sanity(trigger_type: str, trigger_value: float) -> float:
    """Penalize implausible sensor readings."""
    caps = {
        "heavy_rain":   500,   # mm/hr — anything >500 is physically impossible
        "extreme_heat": 55,    # °C
        "severe_aqi":   1000,
        "high_wind":    250,
    }
    cap = caps.get(trigger_type)
    if cap and trigger_value > cap:
        return 0.4  # Strong suspicion
    return 0.0


def run_fraud_check(
    db: Session,
    user_id: int,
    trigger_type: str,
    trigger_value: float,
    zone: str,
    gps_tolerance_km: float = 8.0,
) -> dict[str, Any]:
    """
    Composite fraud scorer.
    Returns a score in [0, 1] and a verdict:
      < 0.35 → clean
      0.35–0.65 → review
      > 0.65 → reject
    """
    gps   = _gps_check(db, user_id, zone, gps_tolerance_km)
    dupl  = _duplicate_check(db, user_id, trigger_type, zone)
    vel   = _velocity_check(db, user_id)
    t_anom = _time_anomaly(trigger_type)
    v_san  = _value_sanity(trigger_type, trigger_value)

    # Weighted composite
    score = 0.0
    flags = []

    if gps["gps_mismatch_flag"]:
        score += 0.35
        flags.append(f"GPS mismatch (+{gps['distance_km']}km from zone)")

    if dupl["repeated_claim_flag"]:
        score += 0.30
        flags.append(f"Duplicate claim (prior: {dupl['duplicate_claim_id']})")

    if vel["velocity_flag"]:
        score += 0.15
        flags.append(f"High velocity ({vel['weekly_claim_count']} claims/week)")

    if t_anom:
        score += t_anom
        flags.append("Time anomaly (off-hours claim)")

    if v_san:
        score += v_san
        flags.append("Implausible trigger value")

    score = round(min(score, 1.0), 3)

    verdict = (
        "reject" if score > 0.65 else
        "review" if score > 0.35 else
        "clean"
    )

    return {
        "fraud_score": score,
        "verdict": verdict,
        "flags": flags,
        "gps_match": gps.get("gps_match"),
        "gps_mismatch_score": gps.get("gps_mismatch_score", 0.0),
        "gps_mismatch_flag": gps.get("gps_mismatch_flag", False),
        "repeated_claim_flag": dupl["repeated_claim_flag"],
        "time_anomaly_score": t_anom,
        "velocity_flag": vel["velocity_flag"],
        "weekly_claim_count": vel["weekly_claim_count"],
    }
