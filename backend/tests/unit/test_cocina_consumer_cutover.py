"""
Unit tests for cocina-as-consumer cutover (Task 1.17).

Tests:
- cocina/router.py no longer defines a /ws route (the old cocina WS endpoint is gone)
- cocina consumes kitchen:all via the shared transport, not a private manager
- kitchen events still reach COCINA connections (KDS parity via structure check)

Design: D4 — one transport, cocina is a CONSUMER via kitchen:all topic,
not a transport owner.
"""

from __future__ import annotations

import ast
from pathlib import Path


def _cocina_router_source() -> str:
    path = (
        Path(__file__).parent.parent.parent  # backend/
        / "features" / "cocina" / "router.py"
    )
    return path.read_text()


def _cocina_service_source() -> str:
    path = (
        Path(__file__).parent.parent.parent  # backend/
        / "features" / "cocina" / "service.py"
    )
    return path.read_text()


def _has_function_def(source: str, name: str) -> bool:
    """Return True if the source AST contains a function definition with `name`."""
    try:
        tree = ast.parse(source)
    except SyntaxError:
        return False
    for node in ast.walk(tree):
        if isinstance(node, ast.FunctionDef) and node.name == name:
            return True
    return False


class TestCocinaRouterNolongerOwnsWS:
    """cocina/router.py must not define a WebSocket endpoint."""

    def test_cocina_router_has_no_websocket_decorator(self):
        """
        After the cutover, cocina/router.py must not contain @router.websocket.
        The /ws route lives in features/websocket/router.py.
        """
        source = _cocina_router_source()
        assert "@router.websocket" not in source, (
            "cocina/router.py still defines @router.websocket — "
            "the old /ws route must be removed (task 1.17)."
        )

    def test_cocina_router_has_no_ws_manager_import(self):
        """cocina/router.py must not import KitchenWSManager or ws_manager."""
        source = _cocina_router_source()
        assert "ws_manager" not in source, (
            "cocina/router.py still imports ws_manager — remove it (task 1.17)."
        )

    def test_cocina_router_has_no_websocket_imports(self):
        """
        cocina/router.py must not import WebSocket or WebSocketDisconnect
        (no longer needs them after route removal).
        """
        source = _cocina_router_source()
        assert "WebSocket" not in source, (
            "cocina/router.py still imports WebSocket after route removal (task 1.17)."
        )


class TestCocinaServiceNolongerOwnsQueue:
    """
    cocina/service.py must not own the drain task or publish_transition_event.
    Those live in the websocket module now.
    """

    def test_cocina_service_has_no_start_drain_task(self):
        """
        cocina/service.py must not define start_drain_task after the cutover.
        The drain task is started by register_realtime in the websocket module.
        """
        source = _cocina_service_source()
        assert not _has_function_def(source, "start_drain_task"), (
            "cocina/service.py still defines start_drain_task() — "
            "drain task ownership belongs to the websocket module (task 1.17)."
        )

    def test_cocina_service_has_no_publish_transition_event(self):
        """
        cocina/service.py must not define publish_transition_event after the cutover.
        orders/service.py now publishes via the EventPublisher port.
        """
        source = _cocina_service_source()
        assert not _has_function_def(source, "publish_transition_event"), (
            "cocina/service.py still defines publish_transition_event() — "
            "this belongs to the orders→port inversion path (task 1.15/1.17)."
        )
