"""Health check."""
from fastapi import APIRouter

from app.core.config import get_settings, is_sqlite
from app.models.database import DATABASE_URL

router = APIRouter(tags=["health"])


@router.get("/health")
def health():
    settings = get_settings()
    return {
        "status": "ok",
        "version": settings.VERSION,
        "project": settings.PROJECT_NAME,
        "db": "sqlite" if is_sqlite(DATABASE_URL) else "postgresql",
        "phase": "Phase 2 - Automation & Protection (JWT, GPS, WebSockets, Scheduler)",
        "team": settings.TEAM,
        "event": settings.EVENT_NAME,
    }

