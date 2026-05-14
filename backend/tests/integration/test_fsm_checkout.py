"""
Unit tests for FSM state machine updates (payment-checkout-api-implementation).

Tests new states: CANCELADO_ADMIN, CANCELADO_CLIENTE.
Tests new RBAC rules and transitions.

Runner: cd backend && uv run pytest tests/integration/test_fsm_checkout.py -v
"""

from __future__ import annotations

import pytest

from shared.exceptions import BusinessRuleError, ForbiddenError


# ---------------------------------------------------------------------------
# ALLOWED_TRANSITIONS — new states
# ---------------------------------------------------------------------------


class TestAllowedTransitionsNewStates:
    def test_pendiente_to_cancelado_admin(self):
        from features.orders.state_machine import ALLOWED_TRANSITIONS

        assert "CANCELADO_ADMIN" in ALLOWED_TRANSITIONS["PENDIENTE"]

    def test_pendiente_to_cancelado_cliente(self):
        from features.orders.state_machine import ALLOWED_TRANSITIONS

        assert "CANCELADO_CLIENTE" in ALLOWED_TRANSITIONS["PENDIENTE"]

    def test_confirmado_to_cancelado_admin(self):
        from features.orders.state_machine import ALLOWED_TRANSITIONS

        assert "CANCELADO_ADMIN" in ALLOWED_TRANSITIONS["CONFIRMADO"]

    def test_en_preparacion_to_cancelado_admin(self):
        from features.orders.state_machine import ALLOWED_TRANSITIONS

        assert "CANCELADO_ADMIN" in ALLOWED_TRANSITIONS["EN_PREPARACION"]

    def test_cancelado_admin_terminal(self):
        from features.orders.state_machine import ALLOWED_TRANSITIONS

        assert ALLOWED_TRANSITIONS["CANCELADO_ADMIN"] == set()

    def test_cancelado_cliente_terminal(self):
        from features.orders.state_machine import ALLOWED_TRANSITIONS

        assert ALLOWED_TRANSITIONS["CANCELADO_CLIENTE"] == set()

    def test_cancelado_legacy_still_terminal(self):
        """CANCELADO catalog entry preserved, still terminal."""
        from features.orders.state_machine import ALLOWED_TRANSITIONS

        assert ALLOWED_TRANSITIONS["CANCELADO"] == set()

    def test_total_edges_updated(self):
        """Total outgoing transitions: PENDIENTE(3) + CONFIRMADO(2) + EN_PREPARACION(2) + EN_CAMINO(1) = 8."""
        from features.orders.state_machine import ALLOWED_TRANSITIONS

        total = sum(len(v) for v in ALLOWED_TRANSITIONS.values())
        assert total == 8  # 3+2+2+1+0+0+0+0


# ---------------------------------------------------------------------------
# TRANSITION_ROLES — new RBAC
# ---------------------------------------------------------------------------


class TestTransitionRolesNewStates:
    def test_pendiente_cancelado_cliente_only_client(self):
        from features.orders.state_machine import TRANSITION_ROLES

        assert TRANSITION_ROLES[("PENDIENTE", "CANCELADO_CLIENTE")] == {"CLIENT"}

    def test_pendiente_cancelado_admin_admin_pedidos(self):
        from features.orders.state_machine import TRANSITION_ROLES

        assert TRANSITION_ROLES[("PENDIENTE", "CANCELADO_ADMIN")] == {
            "ADMIN",
            "PEDIDOS",
        }

    def test_confirmado_cancelado_admin_pedidos(self):
        from features.orders.state_machine import TRANSITION_ROLES

        assert TRANSITION_ROLES[("CONFIRMADO", "CANCELADO_ADMIN")] == {
            "PEDIDOS",
            "ADMIN",
        }

    def test_en_preparacion_cancelado_admin_only_admin(self):
        """RN-RB08: only ADMIN can cancel from EN_PREPARACION."""
        from features.orders.state_machine import TRANSITION_ROLES

        assert TRANSITION_ROLES[("EN_PREPARACION", "CANCELADO_ADMIN")] == {"ADMIN"}

    def test_legacy_pendiente_cancelado_still_exists(self):
        """Legacy CANCELADO transition preserved for backward compat."""
        from features.orders.state_machine import TRANSITION_ROLES

        assert TRANSITION_ROLES[("PENDIENTE", "CANCELADO")] == {
            "CLIENT",
            "PEDIDOS",
            "ADMIN",
        }

    def test_total_role_entries(self):
        """8 entries: legacy(1) + new(7)."""
        from features.orders.state_machine import TRANSITION_ROLES

        assert len(TRANSITION_ROLES) == 8


# ---------------------------------------------------------------------------
# validate_transition — new transitions
# ---------------------------------------------------------------------------


class TestValidateTransitionNewStates:
    def test_client_can_cancel_pendiente_as_cliente(self):
        from features.orders.state_machine import validate_transition

        validate_transition("PENDIENTE", "CANCELADO_CLIENTE", {"CLIENT"})

    def test_client_cannot_cancel_pendiente_as_admin(self):
        from features.orders.state_machine import validate_transition

        with pytest.raises(ForbiddenError):
            validate_transition("PENDIENTE", "CANCELADO_CLIENTE", {"ADMIN"})

    def test_admin_can_cancel_pendiente_as_admin(self):
        from features.orders.state_machine import validate_transition

        validate_transition("PENDIENTE", "CANCELADO_ADMIN", {"ADMIN"})

    def test_pedidos_can_cancel_pendiente_as_admin(self):
        from features.orders.state_machine import validate_transition

        validate_transition("PENDIENTE", "CANCELADO_ADMIN", {"PEDIDOS"})

    def test_client_cannot_cancel_pendiente_as_admin(self):
        from features.orders.state_machine import validate_transition

        with pytest.raises(ForbiddenError):
            validate_transition("PENDIENTE", "CANCELADO_ADMIN", {"CLIENT"})

    def test_admin_can_cancel_confirmado_as_admin(self):
        from features.orders.state_machine import validate_transition

        validate_transition("CONFIRMADO", "CANCELADO_ADMIN", {"ADMIN"})

    def test_pedidos_can_cancel_confirmado_as_admin(self):
        from features.orders.state_machine import validate_transition

        validate_transition("CONFIRMADO", "CANCELADO_ADMIN", {"PEDIDOS"})

    def test_admin_can_cancel_en_preparacion(self):
        from features.orders.state_machine import validate_transition

        validate_transition("EN_PREPARACION", "CANCELADO_ADMIN", {"ADMIN"})

    def test_pedidos_cannot_cancel_en_preparacion(self):
        """RN-RB08: PEDIDOS cannot cancel from EN_PREPARACION."""
        from features.orders.state_machine import validate_transition

        with pytest.raises(ForbiddenError):
            validate_transition("EN_PREPARACION", "CANCELADO_ADMIN", {"PEDIDOS"})

    def test_cancelado_admin_is_terminal(self):
        from features.orders.state_machine import validate_transition

        with pytest.raises(BusinessRuleError):
            validate_transition("CANCELADO_ADMIN", "PENDIENTE", {"ADMIN"})

    def test_cancelado_cliente_is_terminal(self):
        from features.orders.state_machine import validate_transition

        with pytest.raises(BusinessRuleError):
            validate_transition("CANCELADO_CLIENTE", "PENDIENTE", {"CLIENT"})
