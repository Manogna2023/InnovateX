"""
ML simulation service — GigShield AI Phase 2
Simulates a LightGBM premium pricing model and a Prophet-style risk forecast.
In production these would be real trained models; here we use deterministic
heuristics that are transparent and explainable for the hackathon demo.
"""
from __future__ import annotations

import math
import random
from datetime import datetime
from typing import Any

# ─── TIER CONFIGURATION ────────────────────────────────────────────────────────
TIER_CONFIG: dict[str, dict[str, Any]] = {
    "basic": {
        "base_premium": 49,
        "max_payout": 500,
        "coverage_hours": 4,
        "triggers_allowed": 2,
    },
    "standard": {
        "base_premium": 89,
        "max_payout": 1200,
        "coverage_hours": 8,
        "triggers_allowed": 4,
    },
    "pro": {
        "base_premium": 149,
        "max_payout": 2500,
        "coverage_hours": 12,
        "triggers_allowed": 6,
    },
}

# ─── ZONE RISK MULTIPLIERS (hyper-local factors) ───────────────────────────────
_ZONE_RISK: dict[str, float] = {
    # Chennai zones
    "velachery": 1.15,
    "t.nagar": 1.10,
    "t nagar": 1.10,
    "anna nagar": 0.92,
    "adyar": 1.05,
    "tambaram": 1.18,
    "perambur": 1.20,
    "kodambakkam": 1.08,
    # Mumbai
    "dharavi": 1.35,
    "bandra": 0.88,
    "andheri": 1.05,
    "kurla": 1.22,
    "thane": 1.12,
    # Delhi
    "connaught place": 0.85,
    "lajpat nagar": 1.10,
    "dwarka": 1.05,
    "rohini": 1.08,
    # Bengaluru
    "koramangala": 0.90,
    "whitefield": 0.95,
    "btm layout": 1.12,
    "hebbal": 1.08,
}

_PLATFORM_RISK: dict[str, float] = {
    "Zomato": 1.05,
    "Swiggy": 1.05,
    "Zepto": 1.10,   # Q-Commerce: faster, riskier rides
    "Blinkit": 1.10,
    "Amazon": 0.92,  # Scheduled, less weather-sensitive
    "Dunzo": 1.08,
}

_CITY_BASE: dict[str, float] = {
    "Chennai": 1.15,  # Monsoon, flooding risk
    "Mumbai": 1.20,   # Highest flood/rain risk
    "Delhi": 1.10,    # Extreme heat, AQI
    "Bengaluru": 0.95,
    "Hyderabad": 1.05,
    "Kolkata": 1.12,
    "Pune": 1.00,
    "Ahmedabad": 1.08,
}


def lightgbm_premium_model(user: Any, tier: str) -> dict[str, Any]:
    """
    Simulate a LightGBM gradient-boosted premium model.

    Features used (mirrors what a real trained model would consume):
      - zone_risk        : hyper-local flood / waterlogging history
      - city_base        : city-level climate multiplier
      - platform_risk    : delivery segment risk factor
      - income_factor    : higher income → higher coverage demand
      - hours_factor     : more active hours → more exposure
      - seasonality      : monsoon months get surcharge
    """
    cfg = TIER_CONFIG[tier]

    zone_key = (user.zone or "").lower().strip()
    zone_mult = _ZONE_RISK.get(zone_key, 1.00)
    city_mult = _CITY_BASE.get(user.city or "", 1.00)
    plat_mult = _PLATFORM_RISK.get(user.platform or "", 1.00)

    # Income ratio: payout scales with income so premium adjusts
    income_ratio = min((user.avg_daily_income or 700) / 700, 2.0)
    hours_ratio = min((user.active_hours or 10) / 10, 1.4)

    # Monsoon surcharge (June–September)
    month = datetime.utcnow().month
    season_mult = 1.18 if month in (6, 7, 8, 9) else 1.00

    # Composite risk score (0–1)
    risk_score = (zone_mult * city_mult * plat_mult * income_ratio * hours_ratio * season_mult - 1) / 2
    risk_score = max(0.0, min(risk_score, 1.0))

    base = cfg["base_premium"]
    # AI adjustment: can reduce by up to 20% (safe zone) or increase by up to 35% (risky)
    adjustment_pct = -0.20 + risk_score * 0.55
    ai_premium = round(base * (1 + adjustment_pct), 2)
    ai_premium = max(round(base * 0.70, 2), min(ai_premium, round(base * 1.40, 2)))

    # Max payout scales with income
    max_payout = round(cfg["max_payout"] * min(income_ratio, 1.5), 2)

    return {
        "tier": tier,
        "base_premium": base,
        "ai_adjusted_premium": ai_premium,
        "max_payout": max_payout,
        "coverage_hours": cfg["coverage_hours"],
        "triggers_allowed": cfg["triggers_allowed"],
        "risk_score": round(risk_score * 100, 1),
        "zone_multiplier": round(zone_mult, 3),
        "city_multiplier": round(city_mult, 3),
        "platform_multiplier": round(plat_mult, 3),
        "seasonality_multiplier": round(season_mult, 3),
        "model": "LightGBM-sim v2.0 (Phase 2)",
    }


def prophet_risk_forecast(zone: str | None, city: str | None) -> dict[str, Any]:
    """
    Simulate a Facebook Prophet time-series risk forecast.

    Returns a weekly disruption probability with confidence bands and alerts.
    In production this would consume historical rainfall, AQI, and claim data.
    """
    zone = (zone or "").lower().strip()
    city = (city or "").lower().strip()

    zone_mult  = _ZONE_RISK.get(zone, 1.00)
    city_label = city.capitalize() if city else "Unknown"
    city_multi = _CITY_BASE.get(city_label, 1.00)

    month = datetime.utcnow().month
    season_base = 55 if month in (6, 7, 8, 9) else 28 if month in (10, 11) else 20

    # Deterministic seed from zone string for reproducibility
    seed_val = sum(ord(c) for c in zone) % 20
    noise = seed_val - 10  # -10..+10

    raw_score = season_base * zone_mult * city_multi + noise
    risk_score = int(max(5, min(raw_score, 95)))

    weather_risk = (
        "VERY HIGH" if risk_score > 75 else
        "HIGH"      if risk_score > 55 else
        "MODERATE"  if risk_score > 35 else "LOW"
    )
    prob_str = f"{risk_score}%"
    conf = "0.82" if risk_score > 40 else "0.91"

    alerts = []
    if month in (6, 7, 8, 9):
        alerts.append("Monsoon season active — expect heavy rain triggers")
    if risk_score > 60:
        alerts.append(f"Historical data shows elevated disruption in {zone or city_label}")
    if city_label == "Mumbai" and month in (6, 7, 8):
        alerts.append("Mumbai flood season: coverage strongly recommended")
    if city_label == "Delhi" and month in (5, 6):
        alerts.append("Extreme heat advisory active for Delhi NCR")

    return {
        "zone": zone or city_label,
        "city": city_label,
        "risk_score": risk_score,
        "weather_risk": weather_risk,
        "disruption_probability": prob_str,
        "confidence": conf,
        "model": "Prophet-sim v2.0 (Phase 2)",
        "forecast_horizon": "7 days",
        "season": "Monsoon" if month in (6, 7, 8, 9) else "Post-Monsoon" if month in (10, 11) else "Dry",
        "alerts": alerts,
    }
