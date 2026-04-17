"""
GigShield AI — FastAPI application entry.
Team InnovateX · Guidewire DEVTrails 2026
"""
from contextlib import asynccontextmanager

import asyncio

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from slowapi import _rate_limit_exceeded_handler
from slowapi.errors import RateLimitExceeded
from slowapi.middleware import SlowAPIMiddleware

from app.core.config import get_settings
from app.core.limiter import limiter
from app.models import models  # noqa: F401 — register ORM mappers
from app.models.database import Base, SessionLocal, engine
from app.routes import (
    admin,
    auth,
    claims,
    dashboard,
    frontend,
    health,
    location,
    monitor,
    policy,
    websocket_routes,
)
from app.services.scheduler_service import shutdown_scheduler, start_scheduler
from app.services.seed import seed_data
from app.services.websocket_manager import ws_manager


@asynccontextmanager
async def lifespan(app: FastAPI):
    loop = asyncio.get_running_loop()
    ws_manager.set_event_loop(loop)
    Base.metadata.create_all(bind=engine)
    db = SessionLocal()
    try:
        seed_data(db)
    finally:
        db.close()
    settings = get_settings()
    start_scheduler(interval_minutes=settings.MONITOR_INTERVAL_MINUTES)
    yield
    shutdown_scheduler()


def create_app() -> FastAPI:
    settings = get_settings()
    application = FastAPI(
        title=settings.PROJECT_NAME,
        description="Parametric Income Insurance for Food Delivery Partners — Phase 2 (Automation & Protection)",
        version=settings.VERSION,
        lifespan=lifespan,
    )
    application.state.limiter = limiter
    application.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)
    application.add_middleware(SlowAPIMiddleware)

    origins = settings.CORS_ORIGINS
    cors_list = ["*"] if origins == "*" else [o.strip() for o in origins.split(",") if o.strip()]
    application.add_middleware(
        CORSMiddleware,
        allow_origins=cors_list,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    application.include_router(health.router)
    application.include_router(frontend.router)
    application.include_router(auth.router)
    application.include_router(policy.router)
    application.include_router(monitor.router)
    application.include_router(claims.router)
    application.include_router(location.router)
    application.include_router(admin.router)
    application.include_router(dashboard.router)
    application.include_router(websocket_routes.router)
    return application


app = create_app()
