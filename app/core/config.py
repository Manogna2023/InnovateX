"""Application settings loaded from environment (Guidewire DEVTrails — production-style)."""
from functools import lru_cache
from typing import Literal

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    PROJECT_NAME: str = "GigShield AI"
    VERSION: str = "2.0.0"
    EVENT_NAME: str = "Guidewire DEVTrails 2026"
    TEAM: str = "InnovateX"

    # Database: PostgreSQL in production; SQLite fallback for local demo
    DATABASE_URL: str = "sqlite:///./gigshield.db"

    # JWT — MUST override in production via .env
    SECRET_KEY: str = "change-me-in-production-use-openssl-rand-hex-32"
    ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 30
    REFRESH_TOKEN_EXPIRE_DAYS: int = 7

    # CORS
    CORS_ORIGINS: str = "*"

    # Rate limiting (slowapi)
    RATE_LIMIT_DEFAULT: str = "100/minute"

    # GPS fraud: max distance (km) from claim zone center to last known GPS
    GPS_ZONE_TOLERANCE_KM: float = 8.0

    # Scheduler: background zone monitoring
    MONITOR_INTERVAL_MINUTES: int = 5


@lru_cache
def get_settings() -> Settings:
    return Settings()


def is_sqlite(url: str) -> bool:
    return url.startswith("sqlite")


def get_db_engine_kwargs(url: str) -> dict:
    if is_sqlite(url):
        return {"connect_args": {"check_same_thread": False}}
    return {"pool_pre_ping": True}

