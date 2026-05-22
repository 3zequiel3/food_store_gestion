"""
Drain/broadcast service — async task that dequeues DomainEvents and fans them out.

Design: D3 — the drain loop is started by register_realtime(app) in the lifespan.
It bridges the sync publish path (InProcessEventPublisher.publish → queue.put_nowait)
to the async send path (ConnectionManager.broadcast_to_topic).

Best-effort: broadcast errors are logged and swallowed; the loop continues.
The task stops cleanly on CancelledError (lifespan shutdown).
"""

from __future__ import annotations

import asyncio
import json
import logging

logger = logging.getLogger(__name__)


async def run_drain_loop(
    queue: asyncio.Queue,
    manager,  # ConnectionManager — typed loosely to avoid circular import
) -> None:
    """
    Continuously drain `queue` and broadcast each DomainEvent via `manager`.

    Exits cleanly on CancelledError (lifespan shutdown).
    Errors during broadcast are caught and logged; the loop continues.
    """
    logger.info("WebSocket drain task started")
    while True:
        try:
            event = await queue.get()
            wire_text = json.dumps(event.to_wire(), default=str)
            try:
                await manager.broadcast_to_topic(event.topic, wire_text)
            except Exception:
                logger.exception(
                    "WebSocket drain: broadcast error for topic=%s — continuing",
                    event.topic,
                )
            finally:
                queue.task_done()
        except asyncio.CancelledError:
            logger.info("WebSocket drain task stopped (cancelled)")
            break
        except Exception:
            logger.exception("WebSocket drain: unexpected error — continuing")
