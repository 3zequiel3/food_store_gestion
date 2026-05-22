"""
Phase 2 FSM tests — P3.9 and P3.10 (tasks 2.1 and 2.3).

Pure unit tests: no DB, no HTTP.
Runner: cd backend && uv run pytest tests/unit/test_fsm_phase2.py -v

P3.9: TERMINADO → CANCELADO_ADMIN must be allowed; restricted to ADMIN only.
P3.10: CONFIRMADO → ENTREGADO must be removed from the FSM entirely.
"""

from __future__ import annotations

import pytest

from shared.exceptions import BusinessRuleError, ForbiddenError


# ---------------------------------------------------------------------------
# Task 2.1 — P3.9: TERMINADO → CANCELADO_ADMIN (ADMIN-only)
# ---------------------------------------------------------------------------


class TestTerminadoCanceladoAdmin:
    """P3.9 — ADMIN can cancel a TERMINADO order; other roles cannot."""

    def test_terminado_cancelado_admin_with_admin_passes(self):
        """ADMIN role can execute TERMINADO → CANCELADO_ADMIN without exception."""
        from features.orders.state_machine import validate_transition

        # Must not raise
        result = validate_transition("TERMINADO", "CANCELADO_ADMIN", {"ADMIN"})
        assert result is None

    def test_terminado_cancelado_admin_with_pedidos_raises_403(self):
        """PEDIDOS role cannot execute TERMINADO → CANCELADO_ADMIN → ForbiddenError."""
        from features.orders.state_machine import validate_transition

        with pytest.raises(ForbiddenError):
            validate_transition("TERMINADO", "CANCELADO_ADMIN", {"PEDIDOS"})

    def test_terminado_cancelado_admin_with_client_raises_403(self):
        """CLIENT role cannot execute TERMINADO → CANCELADO_ADMIN → ForbiddenError."""
        from features.orders.state_machine import validate_transition

        with pytest.raises(ForbiddenError):
            validate_transition("TERMINADO", "CANCELADO_ADMIN", {"CLIENT"})

    def test_terminado_cancelado_admin_in_allowed_transitions(self):
        """CANCELADO_ADMIN is present in ALLOWED_TRANSITIONS['TERMINADO']."""
        from features.orders.state_machine import ALLOWED_TRANSITIONS

        assert "CANCELADO_ADMIN" in ALLOWED_TRANSITIONS["TERMINADO"]

    def test_terminado_cancelado_admin_in_transition_roles_admin_only(self):
        """TRANSITION_ROLES[('TERMINADO','CANCELADO_ADMIN')] == {'ADMIN'}."""
        from features.orders.state_machine import TRANSITION_ROLES

        assert TRANSITION_ROLES[("TERMINADO", "CANCELADO_ADMIN")] == {"ADMIN"}


# ---------------------------------------------------------------------------
# Task 2.3 — P3.10: CONFIRMADO → ENTREGADO must NOT exist in the FSM
# ---------------------------------------------------------------------------


class TestConfirmadoEntregadoRemoved:
    """P3.10 — CONFIRMADO → ENTREGADO removed: FSM rejects it as BusinessRuleError."""

    def test_confirmado_entregado_raises_business_rule_error_for_admin(self):
        """CONFIRMADO → ENTREGADO is not a valid FSM transition, even for ADMIN."""
        from features.orders.state_machine import validate_transition

        with pytest.raises(BusinessRuleError):
            validate_transition("CONFIRMADO", "ENTREGADO", {"ADMIN"})

    def test_confirmado_entregado_absent_from_allowed_transitions(self):
        """ENTREGADO must not appear in ALLOWED_TRANSITIONS['CONFIRMADO']."""
        from features.orders.state_machine import ALLOWED_TRANSITIONS

        assert "ENTREGADO" not in ALLOWED_TRANSITIONS["CONFIRMADO"]

    def test_confirmado_entregado_absent_from_transition_roles(self):
        """('CONFIRMADO','ENTREGADO') must not appear in TRANSITION_ROLES."""
        from features.orders.state_machine import TRANSITION_ROLES

        assert ("CONFIRMADO", "ENTREGADO") not in TRANSITION_ROLES

    def test_confirmado_en_preparacion_still_valid(self):
        """Sanity: removing ENTREGADO does not break CONFIRMADO → EN_PREPARACION."""
        from features.orders.state_machine import validate_transition

        result = validate_transition("CONFIRMADO", "EN_PREPARACION", {"COCINA"})
        assert result is None

    def test_confirmado_cancelado_admin_still_valid(self):
        """Sanity: CONFIRMADO → CANCELADO_ADMIN still works for PEDIDOS."""
        from features.orders.state_machine import validate_transition

        result = validate_transition("CONFIRMADO", "CANCELADO_ADMIN", {"PEDIDOS"})
        assert result is None
