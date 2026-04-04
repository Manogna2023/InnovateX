"""
WebSocket manager — GigShield AI Phase 2
Manages per-worker and admin socket connections.
Thread-safe with asyncio event loop scheduling.
"""
from __future__ import annotations

import asyncio
import json
import logging
from typing import Any

from fastapi import WebSocket

logger = logging.getLogger("gigshield.ws")


class WebSocketManager:
    def __init__(self):
        self._user_sockets: dict[int, list[WebSocket]] = {}
        self._admin_sockets: list[WebSocket] = []
        self._loop: asyncio.AbstractEventLoop | None = None

    def set_event_loop(self, loop: asyncio.AbstractEventLoop) -> None:
        self._loop = loop

    # ── Registration ────────────────────────────────────────────────────────
    def register_user_socket(self, user_id: int, ws: WebSocket) -> None:
        self._user_sockets.setdefault(user_id, []).append(ws)
        logger.info("WS connected: user %d (%d sockets)", user_id, len(self._user_sockets[user_id]))

    def register_admin_socket(self, ws: WebSocket) -> None:
        self._admin_sockets.append(ws)

    def disconnect_user(self, user_id: int, ws: WebSocket) -> None:
        sockets = self._user_sockets.get(user_id, [])
        if ws in sockets:
            sockets.remove(ws)

    def disconnect_admin(self, ws: WebSocket) -> None:
        if ws in self._admin_sockets:
            self._admin_sockets.remove(ws)

    # ── Broadcast helpers ────────────────────────────────────────────────────
    async def _send_safe(self, ws: WebSocket, payload: dict[str, Any]) -> None:
        try:
            await ws.send_text(json.dumps(payload))
        except Exception:
            pass

    async def _broadcast_user(self, user_id: int, payload: dict[str, Any]) -> None:
        for ws in list(self._user_sockets.get(user_id, [])):
            await self._send_safe(ws, payload)

    async def _broadcast_admins(self, payload: dict[str, Any]) -> None:
        for ws in list(self._admin_sockets):
            await self._send_safe(ws, payload)

    def schedule_broadcast_user(self, user_id: int, payload: dict[str, Any]) -> None:
        if self._loop and self._loop.is_running():
            asyncio.run_coroutine_threadsafe(self._broadcast_user(user_id, payload), self._loop)

    def schedule_broadcast_admins(self, payload: dict[str, Any]) -> None:
        if self._loop and self._loop.is_running():
            asyncio.run_coroutine_threadsafe(self._broadcast_admins(payload), self._loop)


ws_manager = WebSocketManager()
