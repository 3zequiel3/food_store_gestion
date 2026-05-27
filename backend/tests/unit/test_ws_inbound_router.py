"""
Unit tests — Task 5.5: inbound WebSocket message router (P0.3).

The router must:
  - Dispatch by "type" field in the parsed JSON frame.
  - Return an error frame (never crash the connection) for unknown or malformed types.
  - Honor a "subscribe" request only within the JWT-derived scope.
  - Route "kitchen.ingredient_unavailable" to COCINA/ADMIN only (CLIENT rejected).

Design D5: typed inbound router; unknown/invalid frames → error frame
{v:1, type:"error", payload:{reason:...}}; socket stays open.
"""

from __future__ import annotations

import json
from unittest.mock import AsyncMock, MagicMock, patch

import pytest


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _make_scope(
    *,
    kitchen: bool = False,
    orders_all: bool = False,
    client_own: bool = False,
    user_id: int = 1,
) -> dict:
    return {
        "type": "kitchen" if (kitchen or orders_all) else ("client_own" if client_own else "empty"),
        "user_id": user_id,
        "kitchen": kitchen,
        "orders_all": orders_all,
        "client_own": client_own,
    }


async def _call_handle_inbound(raw: str, scope: dict, roles: list[str], user_id: int = 1):
    """Invoke the inbound router with a fake WebSocket."""
    from features.websocket.router import _handle_inbound

    ws = AsyncMock()
    await _handle_inbound(ws, raw, scope, user_id, roles)
    return ws


def _sent_frame(ws) -> dict | None:
    """Return the first frame sent on the mock websocket, parsed as JSON."""
    if not ws.send_text.called:
        return None
    return json.loads(ws.send_text.call_args_list[0].args[0])


# ---------------------------------------------------------------------------
# Task 5.5 — malformed / unknown frames return an error frame without crashing
# ---------------------------------------------------------------------------


class TestInboundRouterErrorHandling:
    """Unknown or malformed inbound frames must be rejected with an error frame."""

    @pytest.mark.asyncio
    async def test_invalid_json_returns_error_frame(self):
        """Non-JSON text → error frame with reason='invalid_json'; socket stays open."""
        scope = _make_scope(kitchen=True)
        ws = await _call_handle_inbound("not json {{{", scope, ["COCINA"])

        frame = _sent_frame(ws)
        assert frame is not None, "No frame was sent"
        assert frame["type"] == "error"
        assert frame["v"] == 1
        assert "invalid_json" in frame["payload"]["reason"]

    @pytest.mark.asyncio
    async def test_unknown_type_returns_error_frame(self):
        """A valid JSON frame with an unknown type → error frame; socket not closed."""
        scope = _make_scope(kitchen=True)
        raw = json.dumps({"v": 1, "type": "definitely_not_a_real_type"})
        ws = await _call_handle_inbound(raw, scope, ["COCINA"])

        frame = _sent_frame(ws)
        assert frame is not None
        assert frame["type"] == "error"
        assert "unknown_type" in frame["payload"]["reason"]

        # Socket must NOT be closed
        ws.close.assert_not_called()

    @pytest.mark.asyncio
    async def test_none_type_returns_error_frame(self):
        """Frame with type=null → error frame (not a crash)."""
        scope = _make_scope(client_own=True)
        raw = json.dumps({"v": 1, "type": None})
        ws = await _call_handle_inbound(raw, scope, ["CLIENT"])

        frame = _sent_frame(ws)
        assert frame is not None
        assert frame["type"] == "error"

    @pytest.mark.asyncio
    async def test_missing_type_returns_error_frame(self):
        """Frame missing 'type' key → error frame (not a crash)."""
        scope = _make_scope(client_own=True)
        raw = json.dumps({"v": 1, "payload": {"order_id": 1}})
        ws = await _call_handle_inbound(raw, scope, ["CLIENT"])

        frame = _sent_frame(ws)
        assert frame is not None
        assert frame["type"] == "error"

    @pytest.mark.asyncio
    async def test_error_frame_shape(self):
        """Error frame must carry v=1, type='error', payload.reason (str)."""
        scope = _make_scope(kitchen=True)
        raw = json.dumps({"type": "totally_unknown"})
        ws = await _call_handle_inbound(raw, scope, ["COCINA"])

        frame = _sent_frame(ws)
        assert frame["v"] == 1
        assert frame["type"] == "error"
        assert isinstance(frame["payload"]["reason"], str)
        assert len(frame["payload"]["reason"]) > 0


# ---------------------------------------------------------------------------
# Task 5.5 — subscribe is honored only within JWT scope
# ---------------------------------------------------------------------------


class TestSubscribeHandlerScope:
    """A 'subscribe' request must be validated against the JWT-derived scope."""

    @pytest.mark.asyncio
    async def test_kitchen_scope_can_subscribe_to_kitchen_all(self):
        """COCINA/ADMIN scope: subscribe to kitchen:all → subscribed ack."""
        scope = _make_scope(kitchen=True)
        raw = json.dumps({"v": 1, "type": "subscribe", "topic": "kitchen:all"})

        with patch("features.websocket.router.connection_manager") as mock_mgr:
            mock_mgr.connect = AsyncMock()
            ws = AsyncMock()
            from features.websocket.router import _handle_inbound
            await _handle_inbound(ws, raw, scope, user_id=1, roles=["COCINA"])

        frame = _sent_frame(ws)
        assert frame is not None
        assert frame["type"] == "subscribed"
        assert frame["payload"]["topic"] == "kitchen:all"

    @pytest.mark.asyncio
    async def test_client_scope_cannot_subscribe_to_kitchen_all(self):
        """CLIENT scope: subscribe to kitchen:all → error frame (scope violation)."""
        scope = _make_scope(client_own=True)
        raw = json.dumps({"v": 1, "type": "subscribe", "topic": "kitchen:all"})
        ws = await _call_handle_inbound(raw, scope, roles=["CLIENT"], user_id=5)

        frame = _sent_frame(ws)
        assert frame is not None
        assert frame["type"] == "error"
        assert "subscribe_denied" in frame["payload"]["reason"]

    @pytest.mark.asyncio
    async def test_subscribe_missing_topic_returns_error(self):
        """Subscribe without a topic → error frame."""
        scope = _make_scope(kitchen=True)
        raw = json.dumps({"v": 1, "type": "subscribe"})
        ws = await _call_handle_inbound(raw, scope, roles=["COCINA"], user_id=1)

        frame = _sent_frame(ws)
        assert frame is not None
        assert frame["type"] == "error"
        assert "subscribe_missing_topic" in frame["payload"]["reason"]


# ---------------------------------------------------------------------------
# D4 hardening — order:{N} ownership re-check for CLIENT subscriptions
# ---------------------------------------------------------------------------


class TestSubscribeOrderOwnership:
    """
    CLIENT subscriptions to `order:{N}` must verify pedido ownership against
    the DB. Staff with `orders_all` (ADMIN/PEDIDOS) skip the check.
    """

    @pytest.mark.asyncio
    async def test_client_can_subscribe_to_owned_order(self):
        """CLIENT subscribing to an order they own → subscribed ack."""
        scope = _make_scope(client_own=True, user_id=42)
        raw = json.dumps({"v": 1, "type": "subscribe", "topic": "order:7"})

        with patch("features.websocket.router._client_owns_order", return_value=True) as mock_owns, \
             patch("features.websocket.router.connection_manager") as mock_mgr:
            mock_mgr.connect = AsyncMock()
            ws = await _call_handle_inbound(raw, scope, roles=["CLIENT"], user_id=42)

        mock_owns.assert_called_once_with("order:7", 42)
        frame = _sent_frame(ws)
        assert frame is not None
        assert frame["type"] == "subscribed"
        assert frame["payload"]["topic"] == "order:7"

    @pytest.mark.asyncio
    async def test_client_cannot_subscribe_to_other_clients_order(self):
        """CLIENT subscribing to an order they DON'T own → subscribe_denied."""
        scope = _make_scope(client_own=True, user_id=42)
        raw = json.dumps({"v": 1, "type": "subscribe", "topic": "order:999"})

        with patch("features.websocket.router._client_owns_order", return_value=False) as mock_owns, \
             patch("features.websocket.router.connection_manager") as mock_mgr:
            mock_mgr.connect = AsyncMock()
            ws = await _call_handle_inbound(raw, scope, roles=["CLIENT"], user_id=42)

        mock_owns.assert_called_once_with("order:999", 42)
        mock_mgr.connect.assert_not_called()
        frame = _sent_frame(ws)
        assert frame is not None
        assert frame["type"] == "error"
        assert "subscribe_denied:order:999" in frame["payload"]["reason"]

    @pytest.mark.asyncio
    async def test_admin_skips_ownership_check_on_order_topic(self):
        """ADMIN/PEDIDOS (orders_all=True) subscribes to any order:N without DB check."""
        scope = _make_scope(orders_all=True, user_id=1)
        raw = json.dumps({"v": 1, "type": "subscribe", "topic": "order:999"})

        with patch("features.websocket.router._client_owns_order") as mock_owns, \
             patch("features.websocket.router.connection_manager") as mock_mgr:
            mock_mgr.connect = AsyncMock()
            ws = await _call_handle_inbound(raw, scope, roles=["ADMIN"], user_id=1)

        mock_owns.assert_not_called()
        frame = _sent_frame(ws)
        assert frame is not None
        assert frame["type"] == "subscribed"
        assert frame["payload"]["topic"] == "order:999"


class TestClientOwnsOrderHelper:
    """Direct tests for the _client_owns_order helper."""

    def test_invalid_topic_format_returns_false(self):
        """Topic without a numeric suffix → False (fail closed)."""
        from features.websocket.router import _client_owns_order
        assert _client_owns_order("order:abc", 1) is False
        assert _client_owns_order("order:", 1) is False
        assert _client_owns_order("order", 1) is False

    def test_db_exception_returns_false(self):
        """Any DB exception inside the UoW path → False (fail closed)."""
        from features.websocket.router import _client_owns_order

        with patch("shared.unit_of_work.UnitOfWork") as mock_uow:
            mock_uow.side_effect = RuntimeError("db is on fire")
            assert _client_owns_order("order:7", 42) is False

    def test_ownership_match_delegates_to_repository(self):
        """Happy path: returns whatever pedido_belongs_to_user returns."""
        from features.websocket.router import _client_owns_order

        mock_repo = MagicMock()
        mock_repo.pedido_belongs_to_user.return_value = True

        mock_uow_ctx = MagicMock()
        mock_uow_ctx.session = MagicMock()

        with patch("shared.unit_of_work.UnitOfWork") as mock_uow, \
             patch("features.orders.repository.OrderRepository") as mock_repo_cls:
            mock_uow.return_value.__enter__.return_value = mock_uow_ctx
            mock_uow.return_value.__exit__.return_value = False
            mock_repo_cls.return_value = mock_repo

            assert _client_owns_order("order:7", 42) is True

        mock_repo.pedido_belongs_to_user.assert_called_once_with(pedido_id=7, user_id=42)
