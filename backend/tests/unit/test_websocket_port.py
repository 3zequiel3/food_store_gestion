"""
Unit tests for the websocket module port contract (Task 1.2).

Tests:
- EventPublisher.publish is best-effort and NEVER raises to its caller.
- DomainEvent carries versioned contract: {v, type, topic, payload, ts}.
- InProcessEventPublisher enqueues onto the asyncio queue.
- Drain task broadcasts each event from the queue.
"""

from __future__ import annotations

import asyncio
from datetime import datetime, timezone
from unittest.mock import AsyncMock, MagicMock, patch

import pytest


# ---------------------------------------------------------------------------
# Task 1.2 — EventPublisher port: publish is best-effort, never raises
# ---------------------------------------------------------------------------


class TestEventPublisherContract:
    """EventPublisher protocol contract tests."""

    def test_domain_event_has_versioned_fields(self):
        """DomainEvent must carry v, type, topic, payload, ts."""
        from features.websocket.contracts import DomainEvent

        event = DomainEvent(
            v=1,
            type="order_state_changed",
            topic="kitchen:all",
            payload={"order_id": 1, "estado": "CONFIRMADO"},
            ts=datetime.now(timezone.utc),
        )
        assert event.v == 1
        assert event.type == "order_state_changed"
        assert event.topic == "kitchen:all"
        assert isinstance(event.payload, dict)
        assert isinstance(event.ts, datetime)

    def test_domain_event_serializes_to_dict(self):
        """DomainEvent.to_wire() produces a dict with all contract fields."""
        from features.websocket.contracts import DomainEvent

        event = DomainEvent(
            v=1,
            type="order_state_changed",
            topic="order:42",
            payload={"order_id": 42, "estado": "CONFIRMADO"},
            ts=datetime(2026, 5, 21, 12, 0, 0, tzinfo=timezone.utc),
        )
        wire = event.to_wire()
        assert wire["v"] == 1
        assert wire["type"] == "order_state_changed"
        assert wire["topic"] == "order:42"
        assert wire["payload"]["order_id"] == 42
        assert "ts" in wire

    def test_in_process_publisher_does_not_raise_when_no_loop(self):
        """InProcessEventPublisher.publish is best-effort — never raises."""
        from features.websocket.publisher import InProcessEventPublisher
        from features.websocket.contracts import DomainEvent

        queue: asyncio.Queue = asyncio.Queue()
        loop = asyncio.new_event_loop()
        publisher = InProcessEventPublisher(queue, loop)

        event = DomainEvent(
            v=1,
            type="order_state_changed",
            topic="kitchen:all",
            payload={},
            ts=datetime.now(timezone.utc),
        )

        # Must not raise even in a non-async context
        try:
            publisher.publish(event)
        except Exception as exc:
            pytest.fail(f"publish() raised unexpectedly: {exc}")
        finally:
            loop.close()

    @pytest.mark.asyncio
    async def test_in_process_publisher_enqueues_event(self):
        """InProcessEventPublisher.publish puts the event on the queue."""
        from features.websocket.publisher import InProcessEventPublisher
        from features.websocket.contracts import DomainEvent

        queue: asyncio.Queue = asyncio.Queue(maxsize=10)
        publisher = InProcessEventPublisher(queue, asyncio.get_running_loop())

        event = DomainEvent(
            v=1,
            type="order_state_changed",
            topic="kitchen:all",
            payload={"order_id": 7},
            ts=datetime.now(timezone.utc),
        )

        publisher.publish(event)

        # Give the event loop a chance to process the coroutine
        await asyncio.sleep(0)

        assert not queue.empty()
        queued = await queue.get()
        assert queued.type == "order_state_changed"

    def test_event_publisher_protocol_is_satisfied(self):
        """InProcessEventPublisher satisfies the EventPublisher Protocol."""
        from features.websocket.publisher import InProcessEventPublisher
        from features.websocket.contracts import EventPublisher

        # runtime_checkable Protocol check
        queue: asyncio.Queue = asyncio.Queue()
        loop = asyncio.new_event_loop()
        publisher = InProcessEventPublisher(queue, loop)
        try:
            assert isinstance(publisher, EventPublisher)
        finally:
            loop.close()
