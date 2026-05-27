"""
Unit tests for the FSM state machine module (order-state-machine-fsm #16).

Tests are pure unit: no DB, no HTTP, no fixtures.
Runner: cd backend && uv run pytest tests/integration/test_state_machine.py -v
"""

from __future__ import annotations

import pytest

from shared.exceptions import BusinessRuleError, ForbiddenError


# ---------------------------------------------------------------------------
# ALLOWED_TRANSITIONS
# ---------------------------------------------------------------------------


class TestAllowedTransitions:
    def test_allowed_transitions_completas(self):
        """ALLOWED_TRANSITIONS must define valid outgoing transitions
        plus empty sets for terminal states."""
        from features.orders.state_machine import ALLOWED_TRANSITIONS

        # PENDIENTE outgoing (4)
        assert "CANCELADO" in ALLOWED_TRANSITIONS["PENDIENTE"]
        assert "CANCELADO_ADMIN" in ALLOWED_TRANSITIONS["PENDIENTE"]
        assert "CANCELADO_CLIENTE" in ALLOWED_TRANSITIONS["PENDIENTE"]
        assert "CONFIRMADO" in ALLOWED_TRANSITIONS["PENDIENTE"]

        # CONFIRMADO outgoing (3) — includes client-cancel post-payment
        assert "EN_PREPARACION" in ALLOWED_TRANSITIONS["CONFIRMADO"]
        assert "CANCELADO_ADMIN" in ALLOWED_TRANSITIONS["CONFIRMADO"]
        assert "CANCELADO_CLIENTE" in ALLOWED_TRANSITIONS["CONFIRMADO"]

        # EN_PREPARACION outgoing (2)
        assert "TERMINADO" in ALLOWED_TRANSITIONS["EN_PREPARACION"]
        assert "CANCELADO_ADMIN" in ALLOWED_TRANSITIONS["EN_PREPARACION"]

        # TERMINADO outgoing (3) — P3.9 added CANCELADO_ADMIN; delivery branching keeps EN_CAMINO/ENTREGADO
        assert "EN_CAMINO" in ALLOWED_TRANSITIONS["TERMINADO"]
        assert "ENTREGADO" in ALLOWED_TRANSITIONS["TERMINADO"]
        assert "CANCELADO_ADMIN" in ALLOWED_TRANSITIONS["TERMINADO"]

        # EN_CAMINO outgoing (1)
        assert "ENTREGADO" in ALLOWED_TRANSITIONS["EN_CAMINO"]

        # Terminal states
        assert ALLOWED_TRANSITIONS["ENTREGADO"] == set()
        assert ALLOWED_TRANSITIONS["CANCELADO"] == set()
        assert ALLOWED_TRANSITIONS["CANCELADO_ADMIN"] == set()
        assert ALLOWED_TRANSITIONS["CANCELADO_CLIENTE"] == set()

        # Total outgoing edges: 4 + 3 + 2 + 3 + 1 = 13
        total = sum(len(v) for v in ALLOWED_TRANSITIONS.values())
        assert total == 13


# ---------------------------------------------------------------------------
# TRANSITION_ROLES
# ---------------------------------------------------------------------------


class TestTransitionRoles:
    def test_transition_roles_matriz_completa(self):
        """TRANSITION_ROLES must define all manual transitions with correct role sets."""
        from features.orders.state_machine import TRANSITION_ROLES

        # From PENDIENTE (4 entries — includes ("PENDIENTE", "CONFIRMADO") used by webhook)
        assert TRANSITION_ROLES[("PENDIENTE", "CANCELADO")] == {
            "CLIENT", "PEDIDOS", "ADMIN",
        }
        assert TRANSITION_ROLES[("PENDIENTE", "CANCELADO_CLIENTE")] == {"CLIENT"}
        assert TRANSITION_ROLES[("PENDIENTE", "CANCELADO_ADMIN")] == {"ADMIN", "PEDIDOS"}
        assert TRANSITION_ROLES[("PENDIENTE", "CONFIRMADO")] == {"PEDIDOS", "ADMIN"}

        # From CONFIRMADO (3 entries — includes CLIENT-driven cancel)
        assert TRANSITION_ROLES[("CONFIRMADO", "EN_PREPARACION")] == {
            "PEDIDOS", "ADMIN", "COCINA",
        }
        assert TRANSITION_ROLES[("CONFIRMADO", "CANCELADO_ADMIN")] == {"PEDIDOS", "ADMIN"}
        assert TRANSITION_ROLES[("CONFIRMADO", "CANCELADO_CLIENTE")] == {"CLIENT"}

        # From EN_PREPARACION (2 entries)
        assert TRANSITION_ROLES[("EN_PREPARACION", "TERMINADO")] == {
            "PEDIDOS", "ADMIN", "COCINA",
        }
        assert TRANSITION_ROLES[("EN_PREPARACION", "CANCELADO_ADMIN")] == {"ADMIN"}

        # From TERMINADO (3 entries — P3.9 added CANCELADO_ADMIN)
        assert TRANSITION_ROLES[("TERMINADO", "EN_CAMINO")] == {"PEDIDOS", "ADMIN"}
        assert TRANSITION_ROLES[("TERMINADO", "ENTREGADO")] == {"PEDIDOS", "ADMIN"}
        assert TRANSITION_ROLES[("TERMINADO", "CANCELADO_ADMIN")] == {"ADMIN"}

        # From EN_CAMINO (1 entry)
        assert TRANSITION_ROLES[("EN_CAMINO", "ENTREGADO")] == {"PEDIDOS", "ADMIN"}

        # 4 + 3 + 2 + 3 + 1 = 13 entries total
        assert len(TRANSITION_ROLES) == 13


# ---------------------------------------------------------------------------
# validate_transition
# ---------------------------------------------------------------------------


class TestValidateTransition:
    def test_validate_transition_valida_ok(self):
        """Valid FSM transition with authorized role returns None (no exception)."""
        from features.orders.state_machine import validate_transition

        result = validate_transition("CONFIRMADO", "EN_PREPARACION", {"PEDIDOS"})
        assert result is None

    def test_validate_transition_admin_puede_todo(self):
        """ADMIN can execute any authorized transition."""
        from features.orders.state_machine import validate_transition

        validate_transition("PENDIENTE", "CANCELADO", {"ADMIN"})
        validate_transition("PENDIENTE", "CANCELADO_ADMIN", {"ADMIN"})
        validate_transition("CONFIRMADO", "EN_PREPARACION", {"ADMIN"})
        validate_transition(
            "EN_PREPARACION", "CANCELADO_ADMIN", {"ADMIN"}
        )  # exclusive ADMIN

    def test_validate_transition_client_puede_cancelar_pendiente(self):
        """CLIENT can cancel PENDIENTE orders."""
        from features.orders.state_machine import validate_transition

        validate_transition("PENDIENTE", "CANCELADO", {"CLIENT"})

    def test_validate_transition_fsm_invalida_levanta_business_rule_error(self):
        """Transition not in ALLOWED_TRANSITIONS raises BusinessRuleError."""
        from features.orders.state_machine import validate_transition

        with pytest.raises(BusinessRuleError) as exc_info:
            validate_transition("PENDIENTE", "ENTREGADO", {"ADMIN"})

        assert "PENDIENTE" in str(exc_info.value.detail)
        assert "ENTREGADO" in str(exc_info.value.detail)

    def test_validate_transition_sin_rol_levanta_forbidden_error(self):
        """Transition exists in FSM but user lacks required role raises ForbiddenError."""
        from features.orders.state_machine import validate_transition

        # PEDIDOS is NOT in TRANSITION_ROLES[("EN_PREPARACION", "CANCELADO_ADMIN")] — only ADMIN
        with pytest.raises(ForbiddenError):
            validate_transition("EN_PREPARACION", "CANCELADO_ADMIN", {"PEDIDOS"})

    def test_validate_transition_client_no_puede_en_preparacion(self):
        """CLIENT cannot move CONFIRMADO → EN_PREPARACION (not in role set)."""
        from features.orders.state_machine import validate_transition

        with pytest.raises(ForbiddenError):
            validate_transition("CONFIRMADO", "EN_PREPARACION", {"CLIENT"})

    def test_validate_transition_estado_terminal_entregado(self):
        """ENTREGADO is terminal — no outgoing transitions allowed."""
        from features.orders.state_machine import validate_transition

        with pytest.raises(BusinessRuleError):
            validate_transition("ENTREGADO", "TERMINADO", {"ADMIN"})

    def test_validate_transition_estado_terminal_cancelado(self):
        """CANCELADO is terminal — no outgoing transitions allowed."""
        from features.orders.state_machine import validate_transition

        with pytest.raises(BusinessRuleError):
            validate_transition("CANCELADO", "PENDIENTE", {"ADMIN"})

    def test_validate_transition_estado_origen_desconocido(self):
        """Unknown origin state raises BusinessRuleError."""
        from features.orders.state_machine import validate_transition

        with pytest.raises(BusinessRuleError):
            validate_transition("INEXISTENTE", "CANCELADO", {"ADMIN"})
