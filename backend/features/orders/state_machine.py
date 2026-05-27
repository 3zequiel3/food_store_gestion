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
    "PENDIENTE": {"CANCELADO", "CANCELADO_ADMIN", "CANCELADO_CLIENTE", "CONFIRMADO"},
    # P3.10: ENTREGADO removed — CONFIRMADO can only go to EN_PREPARACION or be cancelled.
    # The direct CONFIRMADO→ENTREGADO shortcut was a design error (orders must be
    # prepared before delivery; there is no "instant delivery" path in v1).
    # CLIENT can cancel a CONFIRMADO pedido — payment is approved at that point,
    # so the UI surfaces a "support will contact you for refund" message.
    "CONFIRMADO": {"EN_PREPARACION", "CANCELADO_ADMIN", "CANCELADO_CLIENTE"},
    "EN_PREPARACION": {"TERMINADO", "CANCELADO_ADMIN"},
    # P3.9: TERMINADO can now be cancelled by ADMIN (e.g. post-completion dispute).
    "TERMINADO": {"EN_CAMINO", "ENTREGADO", "CANCELADO_ADMIN"},
    "EN_CAMINO": {"ENTREGADO"},
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
    ("PENDIENTE", "CONFIRMADO"): {"PEDIDOS", "ADMIN"},
    ("CONFIRMADO", "EN_PREPARACION"): {"PEDIDOS", "ADMIN", "COCINA"},
    # P3.10: ("CONFIRMADO", "ENTREGADO") removed — see ALLOWED_TRANSITIONS comment.
    ("CONFIRMADO", "CANCELADO_ADMIN"): {"PEDIDOS", "ADMIN"},
    # CLIENT-driven cancellation post-payment. The frontend warns the user that
    # support will reach out for the refund — the backend just restores stock.
    ("CONFIRMADO", "CANCELADO_CLIENTE"): {"CLIENT"},
    ("EN_PREPARACION", "TERMINADO"): {"PEDIDOS", "ADMIN", "COCINA"},
    ("EN_PREPARACION", "CANCELADO_ADMIN"): {"ADMIN"},  # RN-RB08 — solo ADMIN
    ("TERMINADO", "EN_CAMINO"): {"PEDIDOS", "ADMIN"},
    ("TERMINADO", "ENTREGADO"): {"PEDIDOS", "ADMIN"},
    # P3.9: ADMIN-only post-completion cancellation (e.g. dispute/refund scenario).
    ("TERMINADO", "CANCELADO_ADMIN"): {"ADMIN"},
    ("EN_CAMINO", "ENTREGADO"): {"PEDIDOS", "ADMIN"},
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
