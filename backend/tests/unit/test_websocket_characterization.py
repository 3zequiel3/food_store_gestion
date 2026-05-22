"""
Characterization tests (Task 1.1) — capture current KDS behavior BEFORE the
websocket module extraction.

These tests prove the baseline before Phase 1 moves the code:
- publish_transition_event enqueues for CONFIRMADO/EN_PREPARACION/TERMINADO/CANCELADO*
- broadcast fan-out (best-effort, never raises)
- Silently discards events with no queue / unknown state

These will remain green AFTER the extraction because the module is relocated
(not rewritten) and the KDS consumer will wire back through the new transport.
"""

from __future__ import annotations

import asyncio
from unittest.mock import AsyncMock, MagicMock, patch

import pytest


# ---------------------------------------------------------------------------
# Task 1.1 — characterize current ws_manager.broadcast behavior
# ---------------------------------------------------------------------------


class TestKitchenWSManagerBroadcast:
    """Characterize KitchenWSManager.broadcast: best-effort, never raises."""

    @pytest.mark.asyncio
    async def test_broadcast_to_zero_connections_returns_without_error(self):
        """Broadcast with no connections silently discards — never raises."""
        from features.cocina.ws_manager import KitchenWSManager

        manager = KitchenWSManager()
        # Must not raise even with no connections
        await manager.broadcast({"type": "pedido_confirmado", "payload": {}})

    @pytest.mark.asyncio
    async def test_broadcast_sends_json_to_connected_clients(self):
        """Broadcast fans out the event to all registered connections."""
        import json
        from features.cocina.ws_manager import KitchenWSManager

        manager = KitchenWSManager()

        ws1 = AsyncMock()
        ws2 = AsyncMock()
        await manager.connect(ws1)
        await manager.connect(ws2)

        event = {"type": "pedido_confirmado", "payload": {"id": 1}}
        await manager.broadcast(event)

        expected = json.dumps(event, default=str)
        ws1.send_text.assert_called_once_with(expected)
        ws2.send_text.assert_called_once_with(expected)

    @pytest.mark.asyncio
    async def test_broadcast_disconnects_failed_client(self):
        """If a send raises, that connection is removed; others still receive."""
        import json
        from features.cocina.ws_manager import KitchenWSManager

        manager = KitchenWSManager()

        ws_bad = AsyncMock()
        ws_bad.send_text.side_effect = Exception("closed")
        ws_good = AsyncMock()

        await manager.connect(ws_bad)
        await manager.connect(ws_good)

        event = {"type": "pedido_terminado", "payload": {}}
        # Must not raise
        await manager.broadcast(event)

        # The failed connection should be removed
        async with manager._lock:
            assert ws_bad not in manager._connections

    @pytest.mark.asyncio
    async def test_connect_and_disconnect_track_connections(self):
        """connect adds; disconnect removes (idempotent)."""
        from features.cocina.ws_manager import KitchenWSManager

        manager = KitchenWSManager()
        ws = AsyncMock()

        await manager.connect(ws)
        async with manager._lock:
            assert ws in manager._connections

        await manager.disconnect(ws)
        async with manager._lock:
            assert ws not in manager._connections

        # Disconnect again — must not raise
        await manager.disconnect(ws)


# ---------------------------------------------------------------------------
# Task 1.1 — characterize publish_kitchen_event (enqueue, best-effort)
# ---------------------------------------------------------------------------


class TestPublishKitchenEvent:
    """Characterize the enqueue path — best-effort, never raises."""

    def test_publish_kitchen_event_does_not_raise_without_loop(self):
        """publish_kitchen_event is best-effort: if no queue, silently discard."""
        from features.cocina.service import publish_kitchen_event

        # Called in a context without a running event loop / queue
        # Must not raise
        try:
            publish_kitchen_event({"type": "pedido_cancelado", "payload": {}})
        except Exception as exc:
            pytest.fail(f"publish_kitchen_event raised unexpectedly: {exc}")


# ---------------------------------------------------------------------------
# Task 1.1 — characterize publish_transition_event: state-to-event mapping
# ---------------------------------------------------------------------------


class TestPublishTransitionEventMapping:
    """
    Characterize which states trigger a kitchen event.

    publish_transition_event only enqueues for:
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
    def test_kitchen_states_map_to_event_type(self, estado):
        """_state_to_event_type returns a non-None string for kitchen states."""
        from features.cocina.service import _state_to_event_type

        result = _state_to_event_type(estado)
        assert result is not None
        assert isinstance(result, str)

    @pytest.mark.parametrize("estado", NON_KITCHEN_STATES)
    def test_non_kitchen_states_return_none(self, estado):
        """_state_to_event_type returns None for non-kitchen states."""
        from features.cocina.service import _state_to_event_type

        result = _state_to_event_type(estado)
        assert result is None
