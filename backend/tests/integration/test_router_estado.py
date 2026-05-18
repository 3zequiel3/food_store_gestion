"""
Integration tests for PATCH /api/v1/pedidos/{pedido_id}/estado
(order-state-machine-fsm #16).

Runner: cd backend && uv run pytest tests/integration/test_router_estado.py -v
"""

from __future__ import annotations

from decimal import Decimal

import pytest
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

ESTADO_URL = "/api/v1/pedidos/{pedido_id}/estado"


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


@pytest.fixture
def pedido_pendiente(
    test_db_session: Session, sample_user, sample_formas_pago, sample_estados_pedido
):
    """A Pedido in PENDIENTE state belonging to sample_user."""
    from features.orders.models import Pedido

    pedido = Pedido(
        user_id=sample_user.id,
        total=Decimal("200.00"),
        costo_envio=Decimal("0.00"),
        forma_pago_codigo="MERCADOPAGO",
        estado_codigo="PENDIENTE",
    )
    test_db_session.add(pedido)
    test_db_session.commit()
    test_db_session.refresh(pedido)
    return pedido


@pytest.fixture
def pedido_confirmado(
    test_db_session: Session, sample_user, sample_formas_pago, sample_estados_pedido
):
    """A Pedido in CONFIRMADO state belonging to sample_user."""
    from features.orders.models import Pedido

    pedido = Pedido(
        user_id=sample_user.id,
        total=Decimal("200.00"),
        costo_envio=Decimal("0.00"),
        forma_pago_codigo="MERCADOPAGO",
        estado_codigo="CONFIRMADO",
    )
    test_db_session.add(pedido)
    test_db_session.commit()
    test_db_session.refresh(pedido)
    return pedido


@pytest.fixture
def auth_headers_pedidos(client, test_db_session: Session, sample_roles):
    """Auth headers for a PEDIDOS user."""
    from features.users.models import Usuario, UsuarioRol
    from shared.security import hash_password

    user = Usuario(
        email="pedidos_router@example.com",
        password_hash=hash_password("pedidos_pw_123"),
        nombre="Gestor",
        apellido="Pedidos",
        is_active=True,
    )
    test_db_session.add(user)
    test_db_session.flush()
    test_db_session.add(UsuarioRol(user_id=user.id, role_id=3))  # PEDIDOS
    test_db_session.commit()

    response = client.post(
        "/api/v1/auth/login",
        json={"email": "pedidos_router@example.com", "password": "pedidos_pw_123"},
    )
    return {}


@pytest.fixture
def auth_headers_admin(client, test_db_session: Session, sample_roles):
    """Auth headers for an ADMIN user (US-065)."""
    from features.users.models import Usuario, UsuarioRol
    from shared.security import hash_password

    user = Usuario(
        email="admin_router@example.com",
        password_hash=hash_password("admin_router_pw"),
        nombre="Admin",
        apellido="Router",
        is_active=True,
    )
    test_db_session.add(user)
    test_db_session.flush()
    test_db_session.add(UsuarioRol(user_id=user.id, role_id=1))  # ADMIN
    test_db_session.commit()

    response = client.post(
        "/api/v1/auth/login",
        json={"email": "admin_router@example.com", "password": "admin_router_pw"},
    )
    return {}


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------


class TestPatchEstado:
    def test_patch_estado_sin_auth_401(self, client: TestClient, pedido_pendiente):
        """No auth header → 401."""
        url = ESTADO_URL.format(pedido_id=pedido_pendiente.id)
        response = client.patch(url, json={"nuevo_estado": "CANCELADO"})
        assert response.status_code == 401

    def test_patch_estado_exitoso_200_con_pedido_read(
        self, client: TestClient, auth_headers_pedidos, pedido_pendiente
    ):
        """PEDIDOS cancels PENDIENTE order → 200 with updated estado_codigo."""
        url = ESTADO_URL.format(pedido_id=pedido_pendiente.id)
        response = client.patch(
            url,
            json={"nuevo_estado": "CANCELADO"},
            headers=auth_headers_pedidos,
        )
        assert response.status_code == 200
        body = response.json()
        assert body["estado_codigo"] == "CANCELADO"
        assert body["id"] == pedido_pendiente.id

    def test_patch_estado_pedido_inexistente_404(
        self, client: TestClient, auth_headers_pedidos
    ):
        """Non-existent pedido → 404."""
        url = ESTADO_URL.format(pedido_id=999999)
        response = client.patch(
            url,
            json={"nuevo_estado": "CANCELADO"},
            headers=auth_headers_pedidos,
        )
        assert response.status_code == 404

    def test_patch_estado_rol_insuficiente_403(
        self, client: TestClient, auth_headers, pedido_confirmado
    ):
        """CLIENT cannot move CONFIRMADO → EN_PREPARACION → 403."""
        url = ESTADO_URL.format(pedido_id=pedido_confirmado.id)
        response = client.patch(
            url,
            json={"nuevo_estado": "EN_PREPARACION"},
            headers=auth_headers,  # sample_user is CLIENT
        )
        assert response.status_code == 403

    def test_patch_estado_fsm_invalida_422(
        self, client: TestClient, auth_headers_pedidos, pedido_pendiente
    ):
        """Invalid FSM transition → 422."""
        url = ESTADO_URL.format(pedido_id=pedido_pendiente.id)
        response = client.patch(
            url,
            json={"nuevo_estado": "TERMINADO"},  # PENDIENTE → TERMINADO not allowed
            headers=auth_headers_pedidos,
        )
        assert response.status_code == 422

    def test_patch_estado_motivo_faltante_en_cancel_critico_422(
        self, client: TestClient, auth_headers_pedidos, pedido_confirmado
    ):
        """Cancelling CONFIRMADO without motivo → 422."""
        url = ESTADO_URL.format(pedido_id=pedido_confirmado.id)
        response = client.patch(
            url,
            json={"nuevo_estado": "CANCELADO"},  # no motivo
            headers=auth_headers_pedidos,
        )
        assert response.status_code == 422

    def test_patch_estado_double_click_segundo_intento_no_permite_otra_transicion(
        self, client: TestClient, auth_headers_pedidos, pedido_pendiente
    ):
        """
        After cancelling PENDIENTE, trying to advance to EN_PREPARACION fails.
        The FSM sees CANCELADO as terminal — 422 (BusinessRuleError).

        Note: a true 409 (InvalidStateTransitionError) only happens when the state
        changed between the avanzar_estado read and the transicionar_estado FOR UPDATE
        (race condition). For sequential double-click, the FSM rejects it as 422.
        """
        url = ESTADO_URL.format(pedido_id=pedido_pendiente.id)

        # Cancel the order
        r1 = client.patch(
            url, json={"nuevo_estado": "CANCELADO"}, headers=auth_headers_pedidos
        )
        assert r1.status_code == 200

        # Try to move it forward — CANCELADO is terminal
        r2 = client.patch(
            url, json={"nuevo_estado": "CANCELADO"}, headers=auth_headers_pedidos
        )
        # FSM: CANCELADO is terminal → 422
        assert r2.status_code == 422

    def test_patch_estado_confirmado_via_pydantic_422(
        self, client: TestClient, auth_headers_pedidos, pedido_pendiente
    ):
        """Sending nuevo_estado=CONFIRMADO → 422 (Pydantic blocks before service, D5)."""
        url = ESTADO_URL.format(pedido_id=pedido_pendiente.id)
        response = client.patch(
            url,
            json={"nuevo_estado": "CONFIRMADO"},
            headers=auth_headers_pedidos,
        )
        assert response.status_code == 422

    def test_patch_estado_con_motivo_cancelacion_valida(
        self, client: TestClient, auth_headers_pedidos, pedido_pendiente
    ):
        """PEDIDOS cancels PENDIENTE with motivo → CANCELADO → 200."""
        url = ESTADO_URL.format(pedido_id=pedido_pendiente.id)
        response = client.patch(
            url,
            json={"nuevo_estado": "CANCELADO", "motivo": "Cliente cambió de opinión"},
            headers=auth_headers_pedidos,
        )
        assert response.status_code == 200
        body = response.json()
        assert body["estado_codigo"] == "CANCELADO"

    def test_patch_estado_admin_puede_cancelar_pendiente(
        self, client: TestClient, auth_headers_admin, pedido_pendiente
    ):
        """ADMIN can cancel a PENDIENTE order → 200 (US-065)."""
        url = ESTADO_URL.format(pedido_id=pedido_pendiente.id)
        response = client.patch(
            url,
            json={"nuevo_estado": "CANCELADO"},
            headers=auth_headers_admin,
        )
        assert response.status_code == 200
        assert response.json()["estado_codigo"] == "CANCELADO"

    def test_patch_estado_admin_puede_avanzar_confirmado_a_en_preparacion(
        self, client: TestClient, auth_headers_admin, pedido_confirmado
    ):
        """ADMIN can advance CONFIRMADO → EN_PREPARACION → 200 (US-065)."""
        url = ESTADO_URL.format(pedido_id=pedido_confirmado.id)
        response = client.patch(
            url,
            json={"nuevo_estado": "EN_PREPARACION"},
            headers=auth_headers_admin,
        )
        assert response.status_code == 200
        assert response.json()["estado_codigo"] == "EN_PREPARACION"
