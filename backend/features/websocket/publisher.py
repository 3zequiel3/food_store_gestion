"""
InProcessEventPublisher — concrete implementation of the EventPublisher port.

Design: D2, D3.
The publisher is a thin enqueue shim. The asyncio.Queue is drained by the
broadcast task (see drain.py). All persistence of the queue reference is done
in register_realtime (see registration.py).

Single-instance limitation: D1 — in-process only.
"""

from __future__ import annotations

import asyncio
import logging

from features.websocket.contracts import DomainEvent

logger = logging.getLogger(__name__)


class InProcessEventPublisher:
    """
    Concrete EventPublisher that enqueues DomainEvents onto an asyncio.Queue.

    The drain task (drain.py) reads from this queue and broadcasts each event
    to all ConnectionManager subscribers on the matching topic.

    publish() is sync-safe and best-effort:
    - Uses run_coroutine_threadsafe so it can be called from sync code.
    - Never raises: all exceptions are caught and logged at DEBUG level.
    """

    def __init__(self, queue: asyncio.Queue) -> None:
        self._queue = queue

    def publish(self, event: DomainEvent) -> None:
        """
        Enqueue `event` for async broadcast. Best-effort, never raises.

        Safe to call from both sync and async code:
        - When a running event loop exists (async context), uses
          call_soon_threadsafe to schedule the put coroutine.
        - When called from a sync worker thread (no running loop accessible),
          attempts run_coroutine_threadsafe on the loop.
        - On any failure, silently discards (best-effort).
        """
        try:
            loop = asyncio.get_running_loop()
            # We are inside an async context — schedule the put directly.
            loop.call_soon_threadsafe(self._queue.put_nowait, event)
        except RuntimeError:
            # No running loop — try the legacy threadpool path.
            try:
                loop = asyncio.get_event_loop()
                asyncio.run_coroutine_threadsafe(self._queue.put(event), loop)
            except Exception:
                logger.debug(
                    "InProcessEventPublisher.publish: discarded (best-effort, no loop)",
                )
        except asyncio.QueueFull:
            logger.debug(
                "InProcessEventPublisher.publish: queue full, event discarded",
            )
        except Exception:
            logger.debug(
                "InProcessEventPublisher.publish: discarded (best-effort)",
                exc_info=True,
            )
