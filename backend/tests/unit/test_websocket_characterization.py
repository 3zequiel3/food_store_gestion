"""
Characterization tests (Task 1.1) — KDS baseline behavior through the NEW transport.

After Phase 1 cutover, these tests verify the same behavior (broadcast fan-out,
best-effort swallow, topic-scoped delivery) but through the shared websocket module
instead of the kitchen-owned manager.

Originally these captured the behavior of features/cocina/ws_manager.py before the
extraction. After the cutover (task 1.17), they document the equivalent behavior in
features/websocket/manager.py and features/cocina/service.py (cleaned up service).
"""

from __future__ import annotations

import asyncio
from unittest.mock import AsyncMock, MagicMock, patch

import pytest


# ---------------------------------------------------------------------------
# Task 1.1 — characterize ConnectionManager.broadcast_to_topic: best-effort
# ---------------------------------------------------------------------------


class TestConnectionManagerBroadcast:
    """ConnectionManager.broadcast_to_topic: best-effort, never raises."""

    @pytest.mark.asyncio
    async def test_broadcast_to_zero_connections_returns_without_error(self):
        """Broadcast with no connections silently discards — never raises."""
        from features.websocket.manager import ConnectionManager

        manager = ConnectionManager()
        # Must not raise even with no connections
        await manager.broadcast_to_topic("kitchen:all", '{"type": "pedido_confirmado"}')

    @pytest.mark.asyncio
    async def test_broadcast_sends_json_to_connected_clients(self):
        """Broadcast fans out the event to all registered connections on a topic."""
        import json
        from features.websocket.manager import ConnectionManager

        manager = ConnectionManager()

        ws1 = AsyncMock()
        ws2 = AsyncMock()
        await manager.connect(ws1, topic="kitchen:all")
        await manager.connect(ws2, topic="kitchen:all")

        payload = json.dumps({"type": "pedido_confirmado", "payload": {"id": 1}})
        await manager.broadcast_to_topic("kitchen:all", payload)

        ws1.send_text.assert_called_once_with(payload)
        ws2.send_text.assert_called_once_with(payload)

    @pytest.mark.asyncio
    async def test_broadcast_disconnects_failed_client(self):
        """If a send raises, that connection is removed; others still receive."""
        import json
        from features.websocket.manager import ConnectionManager

        manager = ConnectionManager()

        ws_bad = AsyncMock()
        ws_bad.send_text.side_effect = Exception("closed")
        ws_good = AsyncMock()

        await manager.connect(ws_bad, topic="kitchen:all")
        await manager.connect(ws_good, topic="kitchen:all")

        payload = json.dumps({"type": "pedido_terminado", "payload": {}})
        # Must not raise
        await manager.broadcast_to_topic("kitchen:all", payload)

        # Good connection still received the message
        ws_good.send_text.assert_called_once_with(payload)
        # After failed send, bad ws is removed
        assert manager.connection_count() == 1

    @pytest.mark.asyncio
    async def test_connect_and_disconnect_track_connections(self):
        """connect adds; disconnect removes (idempotent)."""
        from features.websocket.manager import ConnectionManager

        manager = ConnectionManager()
        ws = AsyncMock()

        await manager.connect(ws, topic="kitchen:all")
        assert manager.connection_count() == 1

        await manager.disconnect(ws)
        assert manager.connection_count() == 0

        # Disconnect again — must not raise
        await manager.disconnect(ws)


# ---------------------------------------------------------------------------
# Task 1.1 — characterize publish via EventPublisher port (enqueue, best-effort)
# ---------------------------------------------------------------------------


class TestPublishViaPort:
    """EventPublisher port: publish is best-effort, never raises."""

    def test_publish_does_not_raise_without_loop(self):
        """InProcessEventPublisher.publish is best-effort: if no loop, silently discard."""
        import asyncio
        from features.websocket.publisher import InProcessEventPublisher
        from features.websocket.contracts import DomainEvent

        queue = asyncio.Queue()
        publisher = InProcessEventPublisher(queue)

        try:
            publisher.publish(DomainEvent(
                v=1,
                type="order_state_changed",
                topic="kitchen:all",
                payload={"order_id": 1, "estado": "CANCELADO"},
            ))
        except Exception as exc:
            pytest.fail(f"publish raised unexpectedly: {exc}")


# ---------------------------------------------------------------------------
# Task 1.1 — characterize _publish_order_state_event: state-to-event mapping
# ---------------------------------------------------------------------------


class TestPublishTransitionEventMapping:
    """
    Characterize which states trigger a kitchen event via the new port path.

    _publish_order_state_event only enqueues for:
      CONFIRMADO, EN_PREPARACION, TERMINADO, CANCELADO, CANCELADO_ADMIN,
      CANCELADO_CLIENTE
    Any other estado_nuevo is silently dropped.
    """

    KITCHEN_STATES = [
        "CONFIRMADO",
        "EN_PREPARACION",
        "TERMINADO",
        "CANCELADO",
        "CANCELADO_ADMIN",
        "CANCELADO_CLIENTE",
    ]
    NON_KITCHEN_STATES = ["PENDIENTE", "ENTREGADO", "UNKNOWN"]

    @pytest.mark.parametrize("estado", KITCHEN_STATES)
    def test_kitchen_states_publish_event(self, estado):
        """
        _publish_order_state_event enqueues an event for kitchen-relevant states.
        We verify this by checking the function doesn't return early for these states.
        """
        from features.orders.service import _KITCHEN_STATES

        assert estado in _KITCHEN_STATES, (
            f"Estado {estado!r} must be in _KITCHEN_STATES "
            f"but _KITCHEN_STATES = {_KITCHEN_STATES}"
        )

    @pytest.mark.parametrize("estado", NON_KITCHEN_STATES)
    def test_non_kitchen_states_are_excluded(self, estado):
        """Non-kitchen states are not in _KITCHEN_STATES — they are filtered out."""
        from features.orders.service import _KITCHEN_STATES

        assert estado not in _KITCHEN_STATES, (
            f"Estado {estado!r} should NOT be in _KITCHEN_STATES but it is."
        )
