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
import logging

from fastapi import FastAPI

from features.websocket.drain import run_drain_loop
from features.websocket.manager import connection_manager
from features.websocket.publisher import InProcessEventPublisher
import features.websocket.router as _ws_router_module

logger = logging.getLogger(__name__)

# Module-level singletons — set by register_realtime, read by get_event_publisher.
_event_queue: asyncio.Queue | None = None
_event_publisher: InProcessEventPublisher | None = None
_drain_task_handle: asyncio.Task | None = None


def get_event_publisher() -> InProcessEventPublisher | None:
    """
    Return the bound EventPublisher singleton.

    Returns None before register_realtime has been called (e.g. tests that
    override the lifespan). Callers MUST treat None as "no-op publish".
    """
    return _event_publisher


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
    global _event_queue, _event_publisher, _drain_task_handle

    if _event_publisher is not None:
        logger.debug("register_realtime: already registered, skipping")
        return

    # 1. Create the event queue + publisher
    _event_queue = asyncio.Queue(maxsize=200)
    _event_publisher = InProcessEventPublisher(_event_queue)

    # 2. Start the drain task using get_running_loop() (Decision 3 — design.md).
    # register_realtime() is called from the FastAPI lifespan async context,
    # which guarantees a running event loop. get_running_loop() is the modern
    # idiom (Python 3.10+) and raises RuntimeError if no loop is running,
    # making misconfiguration explicit rather than silently pinning to a dead loop.
    loop = asyncio.get_running_loop()
    _drain_task_handle = loop.create_task(run_drain_loop(_event_queue, connection_manager))
    logger.info("WebSocket realtime transport registered (drain task started)")

    # Expose the drain task reference to the health endpoint
    _ws_router_module._drain_task = _drain_task_handle
