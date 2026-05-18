"""
FSM and RBAC constants for order state transitions (order-state-machine-fsm #16).

Rules:
- ALLOWED_TRANSITIONS: valid outgoing states per origin state (pure FSM).
- TRANSITION_ROLES: roles allowed per (origin, target) pair (RBAC).
- validate_transition(): raises on FSM violation (BusinessRuleError) or
  insufficient permissions (ForbiddenError).

Design refs: D3, D4, D10.
No imports from service, router, or FastAPI — pure domain logic.
"""

from __future__ import annotations

from shared.exceptions import BusinessRuleError, ForbiddenError

# ---------------------------------------------------------------------------
# FSM: valid outgoing states per origin
# ---------------------------------------------------------------------------

ALLOWED_TRANSITIONS: dict[str, set[str]] = {
    "PENDIENTE": {"CANCELADO", "CANCELADO_ADMIN", "CANCELADO_CLIENTE"},
    "CONFIRMADO": {"EN_PREPARACION", "CANCELADO_ADMIN"},
    "EN_PREPARACION": {"TERMINADO", "CANCELADO_ADMIN"},
    "TERMINADO": {"ENTREGADO"},
    "ENTREGADO": set(),
    "CANCELADO": set(),
    "CANCELADO_ADMIN": set(),
    "CANCELADO_CLIENTE": set(),
}

# ---------------------------------------------------------------------------
# RBAC: roles allowed per (origin, target) transition
#
# PENDIENTE → CONFIRMADO is NOT listed here — that transition is webhook-only
# (SISTEMA). avanzar_estado() blocks it via doble-defensa D5 before reaching
# validate_transition().
# ---------------------------------------------------------------------------

TRANSITION_ROLES: dict[tuple[str, str], set[str]] = {
    ("PENDIENTE", "CANCELADO"): {"CLIENT", "PEDIDOS", "ADMIN"},
    ("PENDIENTE", "CANCELADO_CLIENTE"): {"CLIENT"},
    ("PENDIENTE", "CANCELADO_ADMIN"): {"ADMIN", "PEDIDOS"},
    ("CONFIRMADO", "EN_PREPARACION"): {"PEDIDOS", "ADMIN"},
    ("CONFIRMADO", "CANCELADO_ADMIN"): {"PEDIDOS", "ADMIN"},
    ("EN_PREPARACION", "TERMINADO"): {"PEDIDOS", "ADMIN"},
    ("EN_PREPARACION", "CANCELADO_ADMIN"): {"ADMIN"},  # RN-RB08 — solo ADMIN
    ("TERMINADO", "ENTREGADO"): {"PEDIDOS", "ADMIN"},
}


# ---------------------------------------------------------------------------
# validate_transition
# ---------------------------------------------------------------------------


def validate_transition(desde: str, hacia: str, user_roles: set[str]) -> None:
    """
    Validate that the FSM transition is allowed AND that the user has a role
    authorized for that transition.

    Args:
        desde: Current state code (e.g. "CONFIRMADO").
        hacia: Target state code (e.g. "EN_PREPARACION").
        user_roles: Set of role codes for the acting user (e.g. {"PEDIDOS"}).

    Raises:
        BusinessRuleError: The transition is not defined in ALLOWED_TRANSITIONS
            (unknown origin state, terminal state, or invalid jump).
        ForbiddenError: The transition is valid in the FSM but the user does not
            have any of the required roles.
    """
    allowed = ALLOWED_TRANSITIONS.get(desde)

    # Unknown origin state or terminal state with no outgoing transitions
    if allowed is None or hacia not in allowed:
        raise BusinessRuleError(
            f"Transición '{desde}' → '{hacia}' no permitida por la FSM del pedido"
        )

    # Check RBAC
    required_roles = TRANSITION_ROLES.get((desde, hacia), set())
    if not user_roles.intersection(required_roles):
        raise ForbiddenError(
            f"No tenés permiso para ejecutar la transición '{desde}' → '{hacia}'. "
            f"Roles requeridos: {sorted(required_roles)}"
        )
