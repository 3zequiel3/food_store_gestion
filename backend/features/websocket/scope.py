"""
Topic/room scope model — server-side derivation from JWT roles.

Design: D4 — scope is DERIVED from the JWT at handshake time, NEVER trusted
from the client. A client-declared topic is validated against this scope before
a subscription is honored.

Scope types:
  ADMIN / PEDIDOS → {type: "staff_orders"} → can subscribe to orders:all
  COCINA / ADMIN  → {type: "kitchen"}       → can subscribe to kitchen:all
  CLIENT          → {type: "client_own"}    → can subscribe to order:N (any N)
                                               but ownership is re-checked at
                                               subscribe time against the DB.
  Other           → {} → no topics allowed.

The scope object is a plain dict passed around between handshake and the
inbound router. Its shape is intentionally simple.
"""

from __future__ import annotations

from typing import Any


# ---------------------------------------------------------------------------
# Scope derivation from JWT roles
# ---------------------------------------------------------------------------

_KITCHEN_ROLES = frozenset({"COCINA", "ADMIN"})
_ORDERS_ALL_ROLES = frozenset({"ADMIN", "PEDIDOS"})
_CLIENT_ROLE = "CLIENT"


def scope_from_jwt(user_id: int, roles: list[str]) -> dict[str, Any]:
    """
    Derive the subscription scope from JWT roles.

    Returns a dict describing which topics the connection is allowed to
    subscribe to. The shape encodes allowed fixed topics and/or a pattern.

    Shape:
      {
        "type": "client_own" | "staff" | "empty",
        "user_id": <int>,               # always present
        "kitchen": <bool>,              # can subscribe to kitchen:all
        "orders_all": <bool>,           # can subscribe to orders:all
        "client_own": <bool>,           # can subscribe to order:N (any N)
      }
    """
    role_set = set(roles)
    kitchen = bool(role_set & _KITCHEN_ROLES)
    orders_all = bool(role_set & _ORDERS_ALL_ROLES)
    client_own = _CLIENT_ROLE in role_set

    if kitchen or orders_all:
        scope_type = "staff"
    elif client_own:
        scope_type = "client_own"
    else:
        scope_type = "empty"

    return {
        "type": scope_type,
        "user_id": user_id,
        "kitchen": kitchen,
        "orders_all": orders_all,
        "client_own": client_own,
    }


# ---------------------------------------------------------------------------
# Topic validation
# ---------------------------------------------------------------------------


def is_topic_allowed(
    topic: str,
    scope: dict[str, Any],
    *,
    user_id: int,
    roles: list[str],
) -> bool:
    """
    Check whether subscribing to `topic` is allowed given the JWT scope.

    For CLIENT connections (scope["client_own"] = True): any "order:N" topic
    is provisionally allowed here; ownership against the DB is re-checked in
    the subscribe handler before the subscription is committed.

    For fixed topics (kitchen:all, orders:all): allowed only when the
    corresponding flag in scope is True.

    Unknown/unsupported topics → False.
    """
    if topic == "kitchen:all":
        return bool(scope.get("kitchen"))

    if topic == "orders:all":
        return bool(scope.get("orders_all"))

    if topic.startswith("order:"):
        # CLIENT can subscribe to order:N topics; ownership check is deferred
        # to the subscribe handler (requires DB lookup).
        return bool(scope.get("client_own")) or bool(scope.get("orders_all"))

    return False


# ---------------------------------------------------------------------------
# Default topic for a connection (auto-subscribed at handshake)
# ---------------------------------------------------------------------------


def default_topic(scope: dict[str, Any]) -> str | None:
    """
    Return the topic a connection is subscribed to automatically at handshake,
    based on its JWT-derived scope.

    COCINA / ADMIN → kitchen:all
    ADMIN / PEDIDOS → orders:all (ADMIN also gets kitchen:all above, so this
                      is the additional default)
    CLIENT → no default topic (they must explicitly subscribe to order:{id})
    """
    if scope.get("kitchen"):
        return "kitchen:all"
    if scope.get("orders_all"):
        return "orders:all"
    return None
