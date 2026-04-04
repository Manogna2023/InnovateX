"""
Seed service — GigShield AI Phase 2
Populates the database with a demo admin account and 3 sample workers
on first startup so the app is immediately usable for demo/judging.
"""
from __future__ import annotations

import logging

from sqlalchemy.orm import Session

from app.core.security import hash_password
from app.models.models import UserDB

logger = logging.getLogger("gigshield.seed")

# ─── SEED DATA ────────────────────────────────────────────────────────────────
_SEED_USERS = [
    # Admin (original)
    {
        "name":             "Admin GigShield",
        "phone":            "0000000000",
        "password":         "Admin@1234",
        "role":             "admin",
        "platform":         "GigShield",
        "city":             "Chennai",
        "zone":             "HQ",
        "avg_daily_income": 0.0,
        "active_hours":     8.0,
    },
    # Admin (shown on admin login page demo)
    {
        "name":             "Admin Portal",
        "phone":            "1111111111",
        "password":         "Admin@123",
        "role":             "admin",
        "platform":         "GigShield",
        "city":             "Mumbai",
        "zone":             "HQ",
        "avg_daily_income": 0.0,
        "active_hours":     8.0,
    },
    # Demo workers
    {
        "name":             "Arjun Kumar",
        "phone":            "9876543210",
        "password":         "Demo@1234",
        "role":             "worker",
        "platform":         "Zomato",
        "city":             "Chennai",
        "zone":             "Velachery",
        "avg_daily_income": 750.0,
        "active_hours":     10.0,
    },
    {
        "name":             "Priya Sharma",
        "phone":            "9876543211",
        "password":         "Demo@1234",
        "role":             "worker",
        "platform":         "Swiggy",
        "city":             "Mumbai",
        "zone":             "Bandra",
        "avg_daily_income": 820.0,
        "active_hours":     11.0,
    },
    {
        "name":             "Ravi Patel",
        "phone":            "9876543212",
        "password":         "Demo@1234",
        "role":             "worker",
        "platform":         "Zepto",
        "city":             "Bengaluru",
        "zone":             "Koramangala",
        "avg_daily_income": 680.0,
        "active_hours":     9.0,
    },
]


def seed_data(db: Session) -> None:
    """Insert seed users only if they don't already exist (idempotent)."""
    inserted = 0
    for u in _SEED_USERS:
        exists = db.query(UserDB).filter(UserDB.phone == u["phone"]).first()
        if exists:
            continue
        user = UserDB(
            name=u["name"],
            phone=u["phone"],
            password_hash=hash_password(u["password"]),
            role=u["role"],
            platform=u["platform"],
            city=u["city"],
            zone=u["zone"],
            avg_daily_income=u["avg_daily_income"],
            active_hours=u["active_hours"],
        )
        db.add(user)
        inserted += 1

    if inserted:
        db.commit()
        logger.info("Seeded %d users.", inserted)
    else:
        logger.info("Seed: all users already present, skipping.")
