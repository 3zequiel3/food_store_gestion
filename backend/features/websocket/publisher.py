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
    - Uses call_soon_threadsafe on the captured main loop.
    - Never raises: all exceptions are caught and logged at DEBUG level.
    """

    def __init__(self, queue: asyncio.Queue, main_loop: asyncio.AbstractEventLoop) -> None:
        self._queue = queue
        self._main_loop = main_loop

    def publish(self, event: DomainEvent) -> None:
        """
        Enqueue `event` for async broadcast on the captured main loop.

        Safe to call from both sync and async code on any thread:
        call_soon_threadsafe is the canonical way to schedule work on an
        event loop from any thread, including FastAPI threadpool workers.
        Best-effort: never raises.
        """
        self._main_loop.call_soon_threadsafe(self._queue.put_nowait, event)
