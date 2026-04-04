"""
Scheduler service — GigShield AI Phase 2
Background thread that fires zone checks every N minutes for all workers
with active policies, auto-initiating claims when disruptions are detected.
"""
from __future__ import annotations

import logging
import threading
import time
from datetime import datetime, timezone

from app.models.database import SessionLocal
from app.models.models import PolicyDB, UserDB
from app.services.claim_service import create_claim_from_request
from app.services.trigger_service import check_zone_for_user
from app.services.websocket_manager import ws_manager

logger = logging.getLogger("gigshield.scheduler")

_scheduler_thread: threading.Thread | None = None
_stop_event = threading.Event()


def _run_zone_checks() -> None:
    """Check all workers with active policies for live disruptions."""
    db = SessionLocal()
    try:
        active = (
            db.query(PolicyDB)
            .filter(PolicyDB.status == "active")
            .all()
        )
        for policy in active:
            user = db.query(UserDB).filter(UserDB.id == policy.user_id).first()
            if not user:
                continue
            result = check_zone_for_user(db, user.id, user.zone or "", user.city or "")
            if result.get("disruption_detected"):
                for trig in result.get("triggers_active", []):
                    # Auto-file claim for this worker
                    claim_result = create_claim_from_request(
                        db, user, policy,
                        trigger_type=trig["type"],
                        trigger_value=trig["value"],
                        disruption_hours=4.0,  # default conservative estimate
                        zone=user.zone or "",
                        auto_initiated=True,
                    )
                    if claim_result.get("claim_status") == "approved":
                        ws_manager.schedule_broadcast_user(
                            user.id,
                            {
                                "type": "auto_claim",
                                "claim_id": claim_result["claim_id"],
                                "payout": claim_result["payout_amount"],
                                "trigger": trig["type"],
                                "zone": user.zone,
                            },
                        )
                        ws_manager.schedule_broadcast_admins(
                            {
                                "type": "auto_claim_admin",
                                "user_id": user.id,
                                "worker": user.name,
                                "claim_id": claim_result["claim_id"],
                                "trigger": trig["type"],
                                "payout": claim_result["payout_amount"],
                                "timestamp": datetime.now(timezone.utc).isoformat(),
                            }
                        )
                    break  # One auto-claim per cycle per worker
    except Exception as exc:
        logger.exception("Scheduler error: %s", exc)
    finally:
        db.close()


def _scheduler_loop(interval_seconds: int) -> None:
    logger.info("Scheduler started — interval %ds", interval_seconds)
    while not _stop_event.is_set():
        try:
            _run_zone_checks()
        except Exception as exc:
            logger.exception("Zone check cycle error: %s", exc)
        _stop_event.wait(timeout=interval_seconds)
    logger.info("Scheduler stopped.")


def start_scheduler(interval_minutes: int = 5) -> None:
    global _scheduler_thread
    _stop_event.clear()
    _scheduler_thread = threading.Thread(
        target=_scheduler_loop,
        args=(interval_minutes * 60,),
        daemon=True,
        name="gigshield-scheduler",
    )
    _scheduler_thread.start()


def shutdown_scheduler() -> None:
    _stop_event.set()
    if _scheduler_thread:
        _scheduler_thread.join(timeout=5)
