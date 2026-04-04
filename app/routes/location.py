"""GPS location logging for workers."""
from datetime import datetime
from typing import Annotated, Any

from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from app.core.deps import assert_self_or_admin, get_current_user, get_db, require_worker
from app.models.models import LocationLogDB, UserDB
from app.schemas.location import LocationUpdateRequest

router = APIRouter(prefix="/location", tags=["location"])


@router.post("/update")
def location_update(
    body: LocationUpdateRequest,
    current: Annotated[UserDB, Depends(require_worker)],
    db: Session = Depends(get_db),
):
    uid = current.id
    row = LocationLogDB(
        user_id=uid,
        latitude=body.latitude,
        longitude=body.longitude,
        timestamp=datetime.utcnow(),
    )
    db.add(row)
    db.commit()
    db.refresh(row)
    return {"ok": True, "id": row.id, "timestamp": row.timestamp.isoformat()}


@router.get("/latest/{user_id}")
def location_latest(
    user_id: int,
    current: Annotated[UserDB, Depends(get_current_user)],
    db: Session = Depends(get_db),
):
    assert_self_or_admin(user_id, current)
    loc = (
        db.query(LocationLogDB)
        .filter(LocationLogDB.user_id == user_id)
        .order_by(LocationLogDB.timestamp.desc())
        .first()
    )
    if not loc:
        return {
            "user_id": user_id,
            "latitude": None,
            "longitude": None,
            "timestamp": None,
        }
    return {
        "user_id": user_id,
        "latitude": loc.latitude,
        "longitude": loc.longitude,
        "timestamp": loc.timestamp.isoformat() if loc.timestamp else None,
    }


@router.get("/history/{user_id}")
def location_history(
    user_id: int,
    current: Annotated[UserDB, Depends(get_current_user)],
    db: Session = Depends(get_db),
    limit: int = Query(120, ge=1, le=500),
):
    """Recent GPS points (oldest → newest) for map trail."""
    assert_self_or_admin(user_id, current)
    rows = (
        db.query(LocationLogDB)
        .filter(LocationLogDB.user_id == user_id)
        .order_by(LocationLogDB.timestamp.desc())
        .limit(limit)
        .all()
    )
    rows = list(reversed(rows))
    points: list[dict[str, Any]] = []
    for r in rows:
        points.append(
            {
                "lat": r.latitude,
                "lng": r.longitude,
                "t": r.timestamp.isoformat() if r.timestamp else None,
            }
        )
    return {"user_id": user_id, "points": points, "count": len(points)}
