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
