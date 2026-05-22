"""
Unit tests — Task 5.7: kitchen.ingredient_unavailable inbound message.

Authorization: COCINA or ADMIN only. CLIENT is rejected with an error frame.
The handler validates the payload (order_id + ingredient_id), then hands off
to the Phase-6 service stub.

Design D5: inbound types performing privileged writes re-check JWT against roles.
"""

from __future__ import annotations

import json
from unittest.mock import AsyncMock, patch

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


def _sent_frame(ws) -> dict | None:
    if not ws.send_text.called:
        return None
    return json.loads(ws.send_text.call_args_list[0].args[0])


async def _send_ingredient_unavailable(
    order_id: int,
    ingredient_id: int,
    roles: list[str],
    user_id: int = 1,
):
    """Send a kitchen.ingredient_unavailable message through _handle_inbound."""
    from features.websocket.router import _handle_inbound

    scope = _make_scope(kitchen=("COCINA" in roles or "ADMIN" in roles))
    raw = json.dumps({
        "v": 1,
        "type": "kitchen.ingredient_unavailable",
        "payload": {"order_id": order_id, "ingredient_id": ingredient_id},
    })
    ws = AsyncMock()
    await _handle_inbound(ws, raw, scope, user_id=user_id, roles=roles)
    return ws


# ---------------------------------------------------------------------------
# Task 5.7 — authorization: COCINA/ADMIN only
# ---------------------------------------------------------------------------


class TestIngredientUnavailableAuthorization:
    """kitchen.ingredient_unavailable must be rejected for non-COCINA/ADMIN roles."""

    @pytest.mark.asyncio
    async def test_client_role_is_rejected_with_error_frame(self):
        """
        A CLIENT connection sending kitchen.ingredient_unavailable must receive
        an error frame with 'unauthorized' in the reason.
        """
        ws = await _send_ingredient_unavailable(
            order_id=10, ingredient_id=3, roles=["CLIENT"]
        )

        frame = _sent_frame(ws)
        assert frame is not None, "No error frame was sent to the rejected CLIENT"
        assert frame["type"] == "error"
        assert "unauthorized" in frame["payload"]["reason"]

    @pytest.mark.asyncio
    async def test_cocina_role_is_authorized(self):
        """
        A COCINA connection sending kitchen.ingredient_unavailable must NOT receive
        an 'unauthorized' error frame.
        """
        ws = await _send_ingredient_unavailable(
            order_id=10, ingredient_id=3, roles=["COCINA"]
        )

        frame = _sent_frame(ws)
        # No frame sent → authorized (stub logs and returns) OR an ack frame
        # Either way: must NOT be an 'unauthorized' error
        if frame is not None:
            assert "unauthorized" not in frame.get("payload", {}).get("reason", ""), (
                f"COCINA should not receive unauthorized error, got: {frame}"
            )

    @pytest.mark.asyncio
    async def test_admin_role_is_authorized(self):
        """ADMIN connection must also be authorized for kitchen.ingredient_unavailable."""
        ws = await _send_ingredient_unavailable(
            order_id=10, ingredient_id=3, roles=["ADMIN"]
        )

        frame = _sent_frame(ws)
        if frame is not None:
            assert "unauthorized" not in frame.get("payload", {}).get("reason", ""), (
                f"ADMIN should not receive unauthorized error, got: {frame}"
            )

    @pytest.mark.asyncio
    async def test_client_role_does_not_invoke_stub(self):
        """
        When a CLIENT is rejected, the Phase-6 stub handler must NOT be called.
        This ensures the authorization guard runs before any side-effects.
        """
        from features.websocket.router import _handle_inbound

        scope = _make_scope(client_own=True)
        raw = json.dumps({
            "v": 1,
            "type": "kitchen.ingredient_unavailable",
            "payload": {"order_id": 10, "ingredient_id": 3},
        })
        ws = AsyncMock()

        # Patch the stub to detect if it's called
        with patch(
            "features.websocket.router.kitchen_ingredient_unavailable_stub"
        ) as mock_stub:
            await _handle_inbound(ws, raw, scope, user_id=99, roles=["CLIENT"])

        mock_stub.assert_not_called()


# ---------------------------------------------------------------------------
# Task 5.7 — payload validation
# ---------------------------------------------------------------------------


class TestIngredientUnavailablePayload:
    """kitchen.ingredient_unavailable with missing/invalid payload fields → error frame."""

    @pytest.mark.asyncio
    async def test_missing_order_id_returns_error(self):
        """Payload without order_id → error frame."""
        from features.websocket.router import _handle_inbound

        scope = _make_scope(kitchen=True)
        raw = json.dumps({
            "v": 1,
            "type": "kitchen.ingredient_unavailable",
            "payload": {"ingredient_id": 5},  # missing order_id
        })
        ws = AsyncMock()
        await _handle_inbound(ws, raw, scope, user_id=1, roles=["COCINA"])

        frame = _sent_frame(ws)
        assert frame is not None
        assert frame["type"] == "error"
        assert "invalid_payload" in frame["payload"]["reason"]

    @pytest.mark.asyncio
    async def test_missing_ingredient_id_returns_error(self):
        """Payload without ingredient_id → error frame."""
        from features.websocket.router import _handle_inbound

        scope = _make_scope(kitchen=True)
        raw = json.dumps({
            "v": 1,
            "type": "kitchen.ingredient_unavailable",
            "payload": {"order_id": 10},  # missing ingredient_id
        })
        ws = AsyncMock()
        await _handle_inbound(ws, raw, scope, user_id=1, roles=["COCINA"])

        frame = _sent_frame(ws)
        assert frame is not None
        assert frame["type"] == "error"
        assert "invalid_payload" in frame["payload"]["reason"]


# ---------------------------------------------------------------------------
# Task 5.8 — stub behavior: authorized call is handed off to the Phase-6 stub
# ---------------------------------------------------------------------------


class TestIngredientUnavailableStub:
    """
    When COCINA/ADMIN sends a valid kitchen.ingredient_unavailable message,
    the router hands off to kitchen_ingredient_unavailable_stub — the Phase-6
    placeholder that will be wired to the real service in task 6.17.
    """

    @pytest.mark.asyncio
    async def test_valid_cocina_message_calls_stub(self):
        """
        COCINA + valid payload → stub is invoked with order_id and ingredient_id.
        """
        from features.websocket.router import _handle_inbound

        scope = _make_scope(kitchen=True)
        raw = json.dumps({
            "v": 1,
            "type": "kitchen.ingredient_unavailable",
            "payload": {"order_id": 42, "ingredient_id": 7},
        })
        ws = AsyncMock()

        with patch(
            "features.websocket.router.kitchen_ingredient_unavailable_stub"
        ) as mock_stub:
            await _handle_inbound(ws, raw, scope, user_id=1, roles=["COCINA"])

        mock_stub.assert_called_once_with(order_id=42, ingredient_id=7)

    @pytest.mark.asyncio
    async def test_stub_is_a_named_placeholder(self):
        """
        kitchen_ingredient_unavailable_stub must exist as a named callable in
        features.websocket.router and carry a docstring marking it as a Phase-6 stub.
        """
        from features.websocket import router as ws_router

        assert hasattr(ws_router, "kitchen_ingredient_unavailable_stub"), (
            "kitchen_ingredient_unavailable_stub must be a top-level callable in router.py"
        )
        stub = ws_router.kitchen_ingredient_unavailable_stub
        assert callable(stub), "kitchen_ingredient_unavailable_stub must be callable"
        doc = (stub.__doc__ or "").lower()
        assert "phase 6" in doc or "stub" in doc, (
            "kitchen_ingredient_unavailable_stub must have a docstring mentioning "
            "Phase 6 or stub to mark it clearly as a placeholder."
        )

    @pytest.mark.asyncio
    async def test_stub_does_not_raise(self):
        """The Phase-6 stub must not raise (it is a no-op placeholder)."""
        from features.websocket.router import kitchen_ingredient_unavailable_stub

        try:
            kitchen_ingredient_unavailable_stub(order_id=1, ingredient_id=2)
        except Exception as exc:
            pytest.fail(f"stub raised unexpectedly: {exc}")
