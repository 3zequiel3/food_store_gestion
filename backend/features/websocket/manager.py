"""
WebSocket ConnectionManager — topic-indexed, in-process connection registry.

Design: D4 — one transport, three consumer classes (CLIENT, ADMIN/PEDIDOS, COCINA),
zero data leaks. Connections are registered per topic; broadcast fans out only to
subscribers of the target topic.

Moved from features/cocina/ws_manager.py (KitchenWSManager) — extended to support
arbitrary topics instead of a single kitchen-wide set.

Thread-safety: asyncio.Lock per operation.
"""

from __future__ import annotations

import asyncio
import logging
from collections import defaultdict
from typing import DefaultDict

from fastapi import WebSocket

logger = logging.getLogger(__name__)


class ConnectionManager:
    """
    In-memory WebSocket connection registry, indexed by topic.

    A single WebSocket may appear in multiple topics (e.g. ADMIN can subscribe
    to both "orders:all" and "kitchen:all").

    Public interface:
      connect(ws, topic)          — register ws under topic
      disconnect(ws)              — remove ws from ALL topics
      broadcast_to_topic(topic, text) — fan-out to all subscribers of topic
      connection_count()          — total connections (across all topics)
    """

    def __init__(self) -> None:
        # topic → set of WebSocket connections
        self._topics: DefaultDict[str, set[WebSocket]] = defaultdict(set)
        self._lock = asyncio.Lock()

    async def connect(self, websocket: WebSocket, topic: str) -> None:
        """Register `websocket` as a subscriber of `topic`."""
        async with self._lock:
            self._topics[topic].add(websocket)
        logger.debug("WS connected on topic=%s total=%d", topic, self.connection_count())

    async def disconnect(self, websocket: WebSocket) -> None:
        """Remove `websocket` from ALL topics it is subscribed to (idempotent)."""
        async with self._lock:
            for topic_set in self._topics.values():
                topic_set.discard(websocket)
        logger.debug("WS disconnected, total=%d", self.connection_count())

    async def broadcast_to_topic(self, topic: str, text: str) -> None:
        """
        Fan out `text` to every connection subscribed to `topic`.

        Best-effort: if a send raises, that connection is removed and broadcast
        continues. Never raises to the caller.
        """
        async with self._lock:
            targets = list(self._topics.get(topic, set()))

        if not targets:
            return

        failed: list[WebSocket] = []
        for ws in targets:
            try:
                await ws.send_text(text)
            except Exception:
                logger.warning("WS send failed on topic=%s, removing connection", topic)
                failed.append(ws)

        if failed:
            async with self._lock:
                for ws in failed:
                    for topic_set in self._topics.values():
                        topic_set.discard(ws)

    def connection_count(self) -> int:
        """Return the total number of unique connections across all topics."""
        # A ws may appear in multiple topics — count distinct objects.
        all_ws: set[WebSocket] = set()
        for topic_set in self._topics.values():
            all_ws.update(topic_set)
        return len(all_ws)


# Module-level singleton — bound in register_realtime (registration.py)
connection_manager = ConnectionManager()
