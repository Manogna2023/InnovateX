"""ORM models — GigShield AI (users, policies, claims, payouts, risk, GPS)."""
from datetime import datetime

from sqlalchemy import (
    Boolean,
    Column,
    DateTime,
    Float,
    ForeignKey,
    Integer,
    String,
    Text,
)

from app.models.database import Base


class UserDB(Base):
    __tablename__ = "users"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(100))
    phone = Column(String(15), unique=True, index=True)
    role = Column(String(20), default="worker")  # worker | admin
    platform = Column(String(50))
    zone = Column(String(100))
    city = Column(String(50))
    avg_daily_income = Column(Float, default=700)
    active_hours = Column(Float, default=10)
    password_hash = Column(String(255), nullable=True)
    otp_hash = Column(String(64), nullable=True)  # legacy; unused with JWT
    created_at = Column(DateTime, default=datetime.utcnow)


class PolicyDB(Base):
    __tablename__ = "policies"

    id = Column(String(50), primary_key=True)
    user_id = Column(Integer, index=True)
    tier = Column(String(20))
    base_premium = Column(Float)
    ai_premium = Column(Float)
    max_payout = Column(Float)
    coverage_hours = Column(Float)
    payment_method = Column(String(20))
    upi_id = Column(String(100))
    status = Column(String(20), default="active")
    week_start = Column(DateTime)
    week_end = Column(DateTime)
    created_at = Column(DateTime, default=datetime.utcnow)


class ClaimDB(Base):
    __tablename__ = "claims"

    id = Column(String(50), primary_key=True)
    policy_id = Column(String(50), index=True)
    user_id = Column(Integer, index=True)
    trigger_type = Column(String(50))
    trigger_value = Column(Float)
    trigger_zone = Column(String(100))
    disruption_hours = Column(Float)
    fraud_score = Column(Float)
    payout_amount = Column(Float)
    status = Column(String(20), default="pending")
    auto_initiated = Column(Boolean, default=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    paid_at = Column(DateTime, nullable=True)
    # Fraud v2
    gps_mismatch_score = Column(Float, default=0.0)
    gps_mismatch_flag = Column(Boolean, default=False)
    repeated_claim_flag = Column(Boolean, default=False)
    time_anomaly_score = Column(Float, default=0.0)
    fraud_flags_json = Column(Text, nullable=True)  # JSON array of strings


class PayoutDB(Base):
    __tablename__ = "payouts"

    id = Column(String(50), primary_key=True)
    claim_id = Column(String(50), index=True)
    user_id = Column(Integer, index=True)
    amount = Column(Float)
    upi_id = Column(String(100))
    method = Column(String(20))
    razorpay_ref = Column(String(100), nullable=True)
    status = Column(String(20), default="initiated")
    created_at = Column(DateTime, default=datetime.utcnow)


class RiskLogDB(Base):
    __tablename__ = "risk_logs"

    id = Column(Integer, primary_key=True, autoincrement=True)
    zone = Column(String(100))
    trigger_type = Column(String(50))
    raw_value = Column(Float)
    threshold = Column(Float)
    breached = Column(Boolean)
    source_api = Column(String(100))
    checked_at = Column(DateTime, default=datetime.utcnow)
    user_id = Column(Integer, nullable=True, index=True)


class LocationLogDB(Base):
    __tablename__ = "location_logs"

    id = Column(Integer, primary_key=True, autoincrement=True)
    user_id = Column(Integer, ForeignKey("users.id"), index=True)
    latitude = Column(Float, nullable=False)
    longitude = Column(Float, nullable=False)
    timestamp = Column(DateTime, default=datetime.utcnow, index=True)
