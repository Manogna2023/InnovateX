"""WebSocket endpoints for live disruption / trigger alerts (demo)."""
from typing import Optional

from fastapi import APIRouter, Query, WebSocket
from jose import JWTError

from app.core.security import decode_token
from app.services.websocket_manager import ws_manager

router = APIRouter(tags=["websocket"])


def _user_id_from_token(token: str) -> tuple[int, str]:
    payload = decode_token(token)
    if payload.get("type") != "access":
        raise ValueError("Access token required")
    uid = int(payload["sub"])
    role = str(payload.get("role", "worker"))
    return uid, role


@router.websocket("/ws/alerts/{user_id}")
async def websocket_worker_alerts(
    websocket: WebSocket,
    user_id: int,
    token: Optional[str] = Query(None),
):
    """Worker stream: JWT `sub` must match `user_id` (admin may observe any id for demo)."""
    await websocket.accept()
    if not token:
        await websocket.close(code=4001)
        return
    try:
        uid, role = _user_id_from_token(token)
    except (JWTError, ValueError, KeyError, TypeError):
        await websocket.close(code=4002)
        return
    if role != "admin" and uid != user_id:
        await websocket.close(code=4003)
        return
    ws_manager.register_user_socket(user_id, websocket)
    try:
        while True:
            await websocket.receive_text()
    except Exception:
        pass
    finally:
        ws_manager.disconnect_user(user_id, websocket)


@router.websocket("/ws/admin/alerts")
async def websocket_admin_alerts(
    websocket: WebSocket,
    token: Optional[str] = Query(None),
):
    await websocket.accept()
    if not token:
        await websocket.close(code=4001)
        return
    try:
        _, role = _user_id_from_token(token)
    except (JWTError, ValueError, KeyError, TypeError):
        await websocket.close(code=4002)
        return
    if role != "admin":
        await websocket.close(code=4003)
        return
    ws_manager.register_admin_socket(websocket)
    try:
        while True:
            await websocket.receive_text()
    except Exception:
        pass
    finally:
        ws_manager.disconnect_admin(websocket)
