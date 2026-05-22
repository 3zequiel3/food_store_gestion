"""
Unit tests for WS handshake auth + topic/room scope binding (Task 1.8).

Tests the scope_from_jwt() helper that maps JWT roles to the set of topics
a connection is allowed to subscribe to.

Design: D4 — scope derived from JWT, never trusted from client.
  CLIENT → allowed: ["order:{owned_id}"] (prefix match)
  ADMIN / PEDIDOS → allowed: ["orders:all"]
  COCINA / ADMIN → allowed: ["kitchen:all"]
  Client-declared scope is IGNORED; server assigns from JWT.
"""

from __future__ import annotations

import pytest


class TestScopeFromJWT:
    """scope_from_jwt derives allowed topics from JWT roles."""

    def test_cocina_role_gets_kitchen_all(self):
        """COCINA role → kitchen:all is in allowed topics."""
        from features.websocket.scope import scope_from_jwt

        scope = scope_from_jwt(user_id=1, roles=["COCINA"])
        assert scope.get("kitchen") is True

    def test_admin_role_gets_both_scopes(self):
        """ADMIN → kitchen:all AND orders:all (admin sees everything)."""
        from features.websocket.scope import scope_from_jwt

        scope = scope_from_jwt(user_id=1, roles=["ADMIN"])
        assert scope.get("kitchen") is True
        assert scope.get("orders_all") is True

    def test_pedidos_role_gets_orders_all(self):
        """PEDIDOS → orders:all."""
        from features.websocket.scope import scope_from_jwt

        scope = scope_from_jwt(user_id=1, roles=["PEDIDOS"])
        assert scope.get("orders_all") is True
        assert not scope.get("kitchen")

    def test_client_role_gets_own_order_prefix(self):
        """CLIENT → only 'order:{id}' topics for their own orders."""
        from features.websocket.scope import scope_from_jwt

        scope = scope_from_jwt(user_id=42, roles=["CLIENT"])
        # CLIENT scope must indicate ownership pattern
        assert scope.get("type") == "client_own"
        assert scope.get("client_own") is True
        assert not scope.get("kitchen")
        assert not scope.get("orders_all")

    def test_topic_allowed_for_cocina(self):
        """is_topic_allowed: kitchen:all is allowed for COCINA scope."""
        from features.websocket.scope import is_topic_allowed, scope_from_jwt

        scope = scope_from_jwt(user_id=1, roles=["COCINA"])
        assert is_topic_allowed("kitchen:all", scope, user_id=1, roles=["COCINA"])

    def test_topic_denied_when_not_in_scope(self):
        """is_topic_allowed: orders:all denied for COCINA scope."""
        from features.websocket.scope import is_topic_allowed, scope_from_jwt

        scope = scope_from_jwt(user_id=1, roles=["COCINA"])
        assert not is_topic_allowed("orders:all", scope, user_id=1, roles=["COCINA"])

    def test_client_cannot_subscribe_to_kitchen(self):
        """is_topic_allowed: CLIENT denied kitchen:all."""
        from features.websocket.scope import is_topic_allowed, scope_from_jwt

        # CLIENT scope object
        scope = scope_from_jwt(user_id=5, roles=["CLIENT"])
        assert not is_topic_allowed("kitchen:all", scope, user_id=5, roles=["CLIENT"])

    def test_client_cannot_subscribe_to_orders_all(self):
        """is_topic_allowed: CLIENT denied orders:all."""
        from features.websocket.scope import is_topic_allowed, scope_from_jwt

        scope = scope_from_jwt(user_id=5, roles=["CLIENT"])
        assert not is_topic_allowed("orders:all", scope, user_id=5, roles=["CLIENT"])

    def test_client_allowed_own_order_topic(self):
        """is_topic_allowed: CLIENT allowed order:{their_id}."""
        from features.websocket.scope import is_topic_allowed, scope_from_jwt

        scope = scope_from_jwt(user_id=5, roles=["CLIENT"])
        # CLIENT can only subscribe to order:N topics that they own.
        # At scope-level (without DB lookup), "order:X" is conditionally allowed.
        assert is_topic_allowed("order:99", scope, user_id=5, roles=["CLIENT"])

    def test_unknown_role_gets_no_scope(self):
        """An unrecognized role grants no topics."""
        from features.websocket.scope import scope_from_jwt, is_topic_allowed

        scope = scope_from_jwt(user_id=99, roles=["STOCK"])
        assert not is_topic_allowed("kitchen:all", scope, user_id=99, roles=["STOCK"])
        assert not is_topic_allowed("orders:all", scope, user_id=99, roles=["STOCK"])
