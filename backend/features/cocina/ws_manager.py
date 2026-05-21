"""
WebSocket connection manager for the Kitchen Display System (KDS).

In-memory singleton that maintains active WebSocket connections for kitchen staff.
Used to broadcast real-time order state changes (pedido_confirmado, pedido_en_preparacion,
pedido_terminado, pedido_cancelado) to connected KDS screens.

Design: D5 — single-instance, best-effort broadcast, no external message bus.
"""

from __future__ import annotations

import asyncio
import json
import logging
from typing import Any

from fastapi import WebSocket

logger = logging.getLogger(__name__)


class KitchenWSManager:
    """
    Singleton in-memory WebSocket connection manager.

    Thread-safe via asyncio.Lock. All public methods are async.
    """

    def __init__(self) -> None:
        self._connections: set[WebSocket] = set()
        self._lock = asyncio.Lock()

    async def connect(self, websocket: WebSocket) -> None:
        """Register a new WebSocket connection."""
        async with self._lock:
            self._connections.add(websocket)
        logger.info(f"KDS WebSocket connected. Total: {len(self._connections)}")

    async def disconnect(self, websocket: WebSocket) -> None:
        """Remove a WebSocket connection (safe if not in set)."""
        async with self._lock:
            self._connections.discard(websocket)
        logger.info(f"KDS WebSocket disconnected. Total: {len(self._connections)}")

    async def broadcast(self, event: dict[str, Any]) -> None:
        """
        Send an event to all connected clients. Best-effort:
        - If no connections, silently discard.
        - If a send fails, remove that connection and continue.
        - Never raises to the caller.
        """
        payload = json.dumps(event, default=str)
        disconnected: list[WebSocket] = []

        async with self._lock:
            targets = list(self._connections)

        if not targets:
            return

        for ws in targets:
            try:
                await ws.send_text(payload)
            except Exception:
                logger.warning("KDS broadcast failed for a connection, disconnecting")
                disconnected.append(ws)

        if disconnected:
            async with self._lock:
                for ws in disconnected:
                    self._connections.discard(ws)


# Module-level singleton
ws_manager = KitchenWSManager()
