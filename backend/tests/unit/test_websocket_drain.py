"""
Unit tests for InProcessEventPublisher + drain task (Tasks 1.6).

Tests:
- publisher.publish() enqueues a DomainEvent onto the queue
- drain task dequeues and calls connection_manager.broadcast_to_topic
- drain task continues after a broadcast error (best-effort)
- drain task stops cleanly on CancelledError
"""

from __future__ import annotations

import asyncio
from datetime import datetime, timezone
from unittest.mock import AsyncMock, patch

import pytest

from features.websocket.contracts import DomainEvent


def _make_event(topic: str = "kitchen:all") -> DomainEvent:
    return DomainEvent(
        v=1,
        type="order_state_changed",
        topic=topic,
        payload={"order_id": 1},
        ts=datetime.now(timezone.utc),
    )


class TestInProcessPublisherEnqueue:
    """InProcessEventPublisher enqueues DomainEvent onto the asyncio.Queue."""

    @pytest.mark.asyncio
    async def test_publish_puts_event_on_queue(self):
        """After publish(), the queue contains the DomainEvent."""
        from features.websocket.publisher import InProcessEventPublisher

        queue: asyncio.Queue = asyncio.Queue(maxsize=10)
        publisher = InProcessEventPublisher(queue)
        event = _make_event()

        publisher.publish(event)
        await asyncio.sleep(0)  # yield so call_soon_threadsafe fires

        assert not queue.empty()
        got = queue.get_nowait()
        assert got.type == event.type
        assert got.topic == event.topic

    @pytest.mark.asyncio
    async def test_publish_on_full_queue_does_not_raise(self):
        """When the queue is full, publish discards silently (best-effort)."""
        from features.websocket.publisher import InProcessEventPublisher

        queue: asyncio.Queue = asyncio.Queue(maxsize=1)
        await queue.put(_make_event())  # fill it

        publisher = InProcessEventPublisher(queue)
        try:
            publisher.publish(_make_event())
        except Exception as exc:
            pytest.fail(f"publish raised on full queue: {exc}")


class TestDrainTask:
    """Drain task dequeues events and broadcasts them via the connection manager."""

    @pytest.mark.asyncio
    async def test_drain_broadcasts_dequeued_event(self):
        """The drain task calls broadcast_to_topic for each dequeued DomainEvent."""
        from features.websocket.drain import run_drain_loop

        queue: asyncio.Queue = asyncio.Queue()
        mock_manager = AsyncMock()

        event = _make_event(topic="kitchen:all")
        await queue.put(event)

        task = asyncio.ensure_future(run_drain_loop(queue, mock_manager))
        # give the task one iteration
        await asyncio.sleep(0.05)
        task.cancel()
        try:
            await task
        except asyncio.CancelledError:
            pass

        import json
        mock_manager.broadcast_to_topic.assert_called_once_with(
            "kitchen:all", json.dumps(event.to_wire(), default=str)
        )

    @pytest.mark.asyncio
    async def test_drain_continues_after_broadcast_error(self):
        """If broadcast raises, the drain loop logs and continues (never crashes)."""
        from features.websocket.drain import run_drain_loop

        queue: asyncio.Queue = asyncio.Queue()
        mock_manager = AsyncMock()
        mock_manager.broadcast_to_topic.side_effect = [
            Exception("send failed"),  # first call raises
            None,  # second call succeeds
        ]

        event1 = _make_event(topic="kitchen:all")
        event2 = _make_event(topic="kitchen:all")
        await queue.put(event1)
        await queue.put(event2)

        task = asyncio.ensure_future(run_drain_loop(queue, mock_manager))
        await asyncio.sleep(0.1)
        task.cancel()
        try:
            await task
        except asyncio.CancelledError:
            pass

        # Both events were attempted
        assert mock_manager.broadcast_to_topic.call_count == 2

    @pytest.mark.asyncio
    async def test_drain_stops_on_cancelled_error(self):
        """Cancelling the drain task exits cleanly without raising."""
        from features.websocket.drain import run_drain_loop

        queue: asyncio.Queue = asyncio.Queue()
        mock_manager = AsyncMock()

        task = asyncio.ensure_future(run_drain_loop(queue, mock_manager))
        await asyncio.sleep(0.01)
        task.cancel()

        # Should complete without uncaught exceptions
        try:
            await task
        except asyncio.CancelledError:
            pass  # expected
