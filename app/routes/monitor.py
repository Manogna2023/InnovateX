"""Zone monitoring (mock external APIs)."""
from typing import Annotated

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.core.deps import assert_self_or_admin, get_db, require_worker_or_admin
from app.models.models import UserDB
from app.schemas.claim import TriggerCheckRequest
from app.services.trigger_service import check_zone_for_user
from app.services.websocket_manager import ws_manager

router = APIRouter(tags=["monitor"])


@router.post("/monitor/check-zone")
def check_zone(
    req: TriggerCheckRequest,
    current: Annotated[UserDB, Depends(require_worker_or_admin)],
    db: Session = Depends(get_db),
):
    assert_self_or_admin(req.user_id, current)
    out = check_zone_for_user(db, req.user_id, req.zone, req.city)
    if out.get("disruption_detected"):
        ws_manager.schedule_broadcast_user(
            req.user_id,
            {
                "type": "disruption",
                "zone": req.zone,
                "triggers": out.get("triggers_active"),
                "checked_at": out.get("checked_at"),
            },
        )
        ws_manager.schedule_broadcast_admins(
            {
                "type": "zone_check",
                "user_id": req.user_id,
                "zone": req.zone,
                "disruption": True,
            }
        )
    return out
