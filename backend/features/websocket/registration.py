"""
register_realtime(app) — the single realtime touchpoint for main.py.

Design: D3 — main.py calls register_realtime(app) exactly once in the lifespan.
It starts the drain task and binds the InProcessEventPublisher singleton.

The /ws router is included directly in main.py (module level) so that routes
survive lifespan overrides in tests. register_realtime() only handles the async
pieces (queue, drain task, publisher binding) that require a running event loop.

After this call:
  - The drain task is running and consuming from the event queue.
  - get_event_publisher() returns the bound InProcessEventPublisher.
"""

from __future__ import annotations

import asyncio
import json
import logging
from datetime import datetime, timezone

from fastapi import FastAPI

from features.websocket.drain import run_drain_loop
from features.websocket.manager import connection_manager
from features.websocket.publisher import InProcessEventPublisher
import features.websocket.router as _ws_router_module

logger = logging.getLogger(__name__)

# How often to broadcast a heartbeat frame to all connections (seconds).
# Keeps the TCP connection alive and lets the backend detect + clean up
# dead connections by catching send errors.
_HEARTBEAT_INTERVAL_S = 30

# Module-level singletons — set by register_realtime, read by get_event_publisher.
_event_queue: asyncio.Queue | None = None
_event_publisher: InProcessEventPublisher | None = None
_drain_task_handle: asyncio.Task | None = None
_heartbeat_task_handle: asyncio.Task | None = None


def get_event_publisher() -> InProcessEventPublisher | None:
    """
    Return the bound EventPublisher singleton.

    Returns None before register_realtime has been called (e.g. tests that
    override the lifespan). Callers MUST treat None as "no-op publish".
    """
    return _event_publisher


async def run_heartbeat_loop() -> None:
    """
    Periodically ping all connected WebSocket clients with a heartbeat frame.

    Every _HEARTBEAT_INTERVAL_S seconds, broadcast a lightweight frame to all
    unique connections. This serves two purposes:

      1. Keep the TCP connection alive through proxies / load balancers that
         would otherwise kill idle connections.
      2. Detect dead connections: if ws.send_text() raises, the ConnectionManager
         removes the connection (see broadcast_all).

    The heartbeat frame is a protocol-level signal — the client resets its
    last-message timer on *any* frame (including heartbeat), so there is no
    need for a separate pong/ack.
    """
    logger.info("WebSocket heartbeat task started (interval=%ds)", _HEARTBEAT_INTERVAL_S)
    while True:
        try:
            await asyncio.sleep(_HEARTBEAT_INTERVAL_S)
            frame = json.dumps({
                "v": 1,
                "type": "heartbeat",
                "ts": datetime.now(timezone.utc).isoformat(),
            })
            await connection_manager.broadcast_all(frame)
        except asyncio.CancelledError:
            logger.info("WebSocket heartbeat task stopped (cancelled)")
            break
        except Exception:
            logger.exception("WebSocket heartbeat: unexpected error — continuing")


def register_realtime(app: FastAPI) -> None:
    """
    Start the drain task and bind the EventPublisher singleton.

    Called ONCE from main.py lifespan startup.

    The /ws router is already included in main.py at module level. This
    function only initializes the async pieces that need a running event loop.

    Steps:
      1. Create the asyncio.Queue and InProcessEventPublisher singleton.
      2. Start the drain/broadcast task.
      3. Expose the drain task reference to the health endpoint.
    """
    global _event_queue, _event_publisher, _drain_task_handle, _heartbeat_task_handle

    if _event_publisher is not None:
        logger.debug("register_realtime: already registered, skipping")
        return

    # 1. Create the event queue + publisher.
    # Capture the current event loop so InProcessEventPublisher can safely
    # schedule work from any thread (including FastAPI sync endpoint workers).
    _main_loop = asyncio.get_running_loop()
    _event_queue = asyncio.Queue(maxsize=200)
    _event_publisher = InProcessEventPublisher(_event_queue, _main_loop)

    # 2. Start the drain task (Decision 3 — design.md).
    _drain_task_handle = _main_loop.create_task(run_drain_loop(_event_queue, connection_manager))
    logger.info("WebSocket realtime transport registered (drain task started)")

    # 3. Start the heartbeat task — broadcasts a ping frame every 30s to
    # keep connections alive through proxies and detect dead connections.
    _heartbeat_task_handle = _main_loop.create_task(run_heartbeat_loop())
    logger.info("WebSocket heartbeat task started")

    # Expose the drain task reference to the health endpoint
    _ws_router_module._drain_task = _drain_task_handle
