"""
Trigger service — GigShield AI Phase 2
Real-time disruption detection using live APIs (Open-Meteo free tier)
with mock fallbacks for social disruptions (curfew, platform outage).
"""
from __future__ import annotations

import math
from datetime import datetime, timezone
from typing import Any

import httpx
from sqlalchemy.orm import Session

from app.models.models import RiskLogDB

# ─── TRIGGER THRESHOLDS ────────────────────────────────────────────────────────
THRESHOLDS: dict[str, dict[str, Any]] = {
    "heavy_rain":    {"threshold": 10.0,  "unit": "mm/hr",  "source": "open-meteo"},
    "extreme_heat":  {"threshold": 40.0,  "unit": "°C",     "source": "open-meteo"},
    "flood":         {"threshold": 1.0,   "unit": "level",  "source": "mock"},
    "severe_aqi":    {"threshold": 300.0, "unit": "AQI",    "source": "mock"},
    "curfew":        {"threshold": 1.0,   "unit": "bool",   "source": "mock"},
    "app_outage":    {"threshold": 50.0,  "unit": "%down",  "source": "mock"},
    "high_wind":     {"threshold": 60.0,  "unit": "km/h",   "source": "open-meteo"},
    "thunderstorm":  {"threshold": 80.0,  "unit": "WMO",    "source": "open-meteo"},
}

# City → approximate lat/lng for weather lookup
_CITY_COORDS: dict[str, tuple[float, float]] = {
    "chennai":    (13.0827, 80.2707),
    "mumbai":     (19.0760, 72.8777),
    "delhi":      (28.6139, 77.2090),
    "bengaluru":  (12.9716, 77.5946),
    "hyderabad":  (17.3850, 78.4867),
    "kolkata":    (22.5726, 88.3639),
    "pune":       (18.5204, 73.8567),
    "ahmedabad":  (23.0225, 72.5714),
}


def _get_city_coords(city: str) -> tuple[float, float] | None:
    return _CITY_COORDS.get(city.lower().strip())


def _fetch_open_meteo(lat: float, lng: float) -> dict[str, Any] | None:
    """Fetch current weather from Open-Meteo (free, no key required)."""
    try:
        url = (
            f"https://api.open-meteo.com/v1/forecast"
            f"?latitude={lat}&longitude={lng}"
            f"&current_weather=true"
            f"&hourly=precipitation,apparent_temperature,weathercode,windspeed_10m"
            f"&timezone=Asia%2FKolkata&forecast_days=1"
        )
        resp = httpx.get(url, timeout=8.0)
        resp.raise_for_status()
        return resp.json()
    except Exception:
        return None


def _mock_social_triggers(zone: str, city: str) -> list[dict[str, Any]]:
    """
    Simulate social disruption triggers (curfew, platform outage, strikes).
    In production these would come from government APIs, platform webhooks,
    and social media NLP classifiers.
    """
    # Deterministic based on zone hash — gives repeatable demo behavior
    seed = sum(ord(c) for c in (zone + city).lower()) % 100
    triggers = []
    if seed > 90:
        triggers.append({"type": "curfew", "value": 1.0, "unit": "bool",
                         "description": "Local authority curfew detected via govt API"})
    if 80 < seed <= 90:
        triggers.append({"type": "app_outage", "value": 65.0, "unit": "%",
                         "description": "Platform API health check: >50% orders failing"})
    return triggers


def check_zone_for_user(
    db: Session, user_id: int, zone: str, city: str = ""
) -> dict[str, Any]:
    """
    Check a zone for active disruption triggers.
    Returns structured result with triggered conditions and auto-claim flag.
    """
    triggers_active: list[dict[str, Any]] = []
    now = datetime.now(timezone.utc)

    coords = _get_city_coords(city)
    weather_data = _fetch_open_meteo(*coords) if coords else None

    if weather_data:
        cw = weather_data.get("current_weather", {})
        hourly = weather_data.get("hourly", {})
        # Current hour index
        hr = datetime.now().hour
        precip = (hourly.get("precipitation") or [0])[min(hr, len(hourly.get("precipitation", [0])) - 1)]
        temp = cw.get("temperature", 25)
        wind = cw.get("windspeed", 0)
        wcode = cw.get("weathercode", 0)

        checks = [
            ("heavy_rain",   precip, THRESHOLDS["heavy_rain"]),
            ("extreme_heat", temp,   THRESHOLDS["extreme_heat"]),
            ("high_wind",    wind,   THRESHOLDS["high_wind"]),
            ("thunderstorm", wcode,  THRESHOLDS["thunderstorm"]),
        ]
        for ttype, value, cfg in checks:
            breached = float(value) >= cfg["threshold"]
            # Log every check to risk_logs
            log = RiskLogDB(
                zone=zone,
                trigger_type=ttype,
                raw_value=float(value),
                threshold=cfg["threshold"],
                breached=breached,
                source_api="open-meteo",
                checked_at=now,
                user_id=user_id,
            )
            db.add(log)
            if breached:
                triggers_active.append({
                    "type": ttype,
                    "value": round(float(value), 2),
                    "unit": cfg["unit"],
                    "threshold": cfg["threshold"],
                    "source": "open-meteo",
                })

    # Social / mock triggers
    for st in _mock_social_triggers(zone, city):
        log = RiskLogDB(
            zone=zone,
            trigger_type=st["type"],
            raw_value=st["value"],
            threshold=THRESHOLDS.get(st["type"], {}).get("threshold", 1.0),
            breached=True,
            source_api="mock",
            checked_at=now,
            user_id=user_id,
        )
        db.add(log)
        triggers_active.append(st)

    db.commit()

    return {
        "zone": zone,
        "city": city,
        "disruption_detected": len(triggers_active) > 0,
        "triggers_active": triggers_active,
        "trigger_count": len(triggers_active),
        "checked_at": now.isoformat(),
        "weather_source": "open-meteo" if weather_data else "unavailable",
    }
