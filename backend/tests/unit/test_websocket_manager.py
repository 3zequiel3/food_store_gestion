"""
Unit tests for the websocket ConnectionManager (Task 1.4).

Tests:
- register/disconnect lifecycle
- broadcast only reaches topic subscribers
- broadcast with no subscribers silently discards
- failed send removes the connection (best-effort)
- multiple topics are independent
"""

from __future__ import annotations

import asyncio
import json
from unittest.mock import AsyncMock

import pytest


class TestConnectionManager:
    """ConnectionManager: topic-indexed registration + selective broadcast."""

    @pytest.mark.asyncio
    async def test_register_adds_connection_to_topic(self):
        """connect() adds the websocket to the given topic set."""
        from features.websocket.manager import ConnectionManager

        mgr = ConnectionManager()
        ws = AsyncMock()
        await mgr.connect(ws, topic="kitchen:all")

        assert mgr.connection_count() == 1

    @pytest.mark.asyncio
    async def test_disconnect_removes_connection(self):
        """disconnect() removes the websocket from its topic (idempotent)."""
        from features.websocket.manager import ConnectionManager

        mgr = ConnectionManager()
        ws = AsyncMock()
        await mgr.connect(ws, topic="kitchen:all")
        await mgr.disconnect(ws)

        assert mgr.connection_count() == 0

        # Idempotent — second disconnect must not raise
        await mgr.disconnect(ws)

    @pytest.mark.asyncio
    async def test_broadcast_reaches_only_topic_subscribers(self):
        """broadcast(topic) delivers only to connections on that topic."""
        from features.websocket.manager import ConnectionManager

        mgr = ConnectionManager()
        ws_kitchen = AsyncMock()
        ws_order = AsyncMock()

        await mgr.connect(ws_kitchen, topic="kitchen:all")
        await mgr.connect(ws_order, topic="order:99")

        payload = json.dumps({"v": 1, "type": "order_state_changed", "topic": "kitchen:all"})
        await mgr.broadcast_to_topic("kitchen:all", payload)

        ws_kitchen.send_text.assert_called_once_with(payload)
        ws_order.send_text.assert_not_called()

    @pytest.mark.asyncio
    async def test_broadcast_to_empty_topic_does_not_raise(self):
        """broadcast to a topic with no subscribers is a no-op, never raises."""
        from features.websocket.manager import ConnectionManager

        mgr = ConnectionManager()
        # No connections at all
        await mgr.broadcast_to_topic("kitchen:all", json.dumps({"v": 1}))

    @pytest.mark.asyncio
    async def test_broadcast_removes_failed_connection(self):
        """If a send raises, that connection is removed; broadcast still succeeds."""
        from features.websocket.manager import ConnectionManager

        mgr = ConnectionManager()
        ws_bad = AsyncMock()
        ws_bad.send_text.side_effect = Exception("connection closed")
        ws_good = AsyncMock()

        await mgr.connect(ws_bad, topic="kitchen:all")
        await mgr.connect(ws_good, topic="kitchen:all")

        payload = json.dumps({"v": 1, "type": "order_state_changed"})
        await mgr.broadcast_to_topic("kitchen:all", payload)

        # Good connection still received the message
        ws_good.send_text.assert_called_once_with(payload)
        # Bad connection is removed
        assert mgr.connection_count() == 1

    @pytest.mark.asyncio
    async def test_connection_count_spans_all_topics(self):
        """connection_count() returns total across all topics."""
        from features.websocket.manager import ConnectionManager

        mgr = ConnectionManager()
        ws1 = AsyncMock()
        ws2 = AsyncMock()
        ws3 = AsyncMock()

        await mgr.connect(ws1, topic="kitchen:all")
        await mgr.connect(ws2, topic="order:1")
        await mgr.connect(ws3, topic="order:2")

        assert mgr.connection_count() == 3

    @pytest.mark.asyncio
    async def test_same_connection_multiple_topics(self):
        """A single ws can subscribe to multiple topics independently."""
        from features.websocket.manager import ConnectionManager

        mgr = ConnectionManager()
        ws = AsyncMock()

        await mgr.connect(ws, topic="kitchen:all")
        await mgr.connect(ws, topic="orders:all")

        kitchen_payload = json.dumps({"topic": "kitchen:all"})
        orders_payload = json.dumps({"topic": "orders:all"})

        await mgr.broadcast_to_topic("kitchen:all", kitchen_payload)
        await mgr.broadcast_to_topic("orders:all", orders_payload)

        assert ws.send_text.call_count == 2
