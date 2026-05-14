"""
Integration tests for POST /api/v1/pedidos/{pedido_id}/transicionar
(payment-checkout-api-implementation).

Runner: cd backend && uv run pytest tests/integration/test_router_transicionar.py -v
"""

from __future__ import annotations

from decimal import Decimal

import pytest
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

TRANSICIONAR_URL = "/api/v1/pedidos/{pedido_id}/transicionar"


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
        email="pedidos_trans@example.com",
        password_hash=hash_password("pedidos_pw_123"),
        nombre="Gestor",
        apellido="Pedidos",
        is_active=True,
    )
    test_db_session.add(user)
    test_db_session.flush()
    test_db_session.add(UsuarioRol(user_id=user.id, role_id=3))  # PEDIDOS
    test_db_session.commit()

    client.post(
        "/api/v1/auth/login",
        json={"email": "pedidos_trans@example.com", "password": "pedidos_pw_123"},
    )
    return {}


@pytest.fixture
def auth_headers_admin(client, test_db_session: Session, sample_roles):
    """Auth headers for an ADMIN user."""
    from features.users.models import Usuario, UsuarioRol
    from shared.security import hash_password

    user = Usuario(
        email="admin_trans@example.com",
        password_hash=hash_password("admin_trans_pw"),
        nombre="Admin",
        apellido="Trans",
        is_active=True,
    )
    test_db_session.add(user)
    test_db_session.flush()
    test_db_session.add(UsuarioRol(user_id=user.id, role_id=1))  # ADMIN
    test_db_session.commit()

    client.post(
        "/api/v1/auth/login",
        json={"email": "admin_trans@example.com", "password": "admin_trans_pw"},
    )
    return {}


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------


class TestTransicionarEndpoint:
    def test_sin_auth_401(self, client: TestClient, pedido_pendiente):
        """No auth → 401."""
        url = TRANSICIONAR_URL.format(pedido_id=pedido_pendiente.id)
        response = client.post(url, json={"estado_codigo_destino": "CANCELADO_ADMIN"})
        assert response.status_code == 401

    def test_cliente_cancela_pendiente_as_cliente_200(
        self, client: TestClient, auth_headers, pedido_pendiente
    ):
        """CLIENT cancels PENDIENTE → CANCELADO_CLIENTE → 200."""
        url = TRANSICIONAR_URL.format(pedido_id=pedido_pendiente.id)
        response = client.post(
            url,
            json={"estado_codigo_destino": "CANCELADO_CLIENTE"},
            headers=auth_headers,
        )
        assert response.status_code == 200
        body = response.json()
        assert body["estado_anterior"] == "PENDIENTE"
        assert body["estado_nuevo"] == "CANCELADO_CLIENTE"
        assert body["pedido_id"] == pedido_pendiente.id

    def test_admin_cancela_pendiente_as_admin_200(
        self, client: TestClient, auth_headers_admin, pedido_pendiente
    ):
        """ADMIN cancels PENDIENTE → CANCELADO_ADMIN → 200."""
        url = TRANSICIONAR_URL.format(pedido_id=pedido_pendiente.id)
        response = client.post(
            url,
            json={
                "estado_codigo_destino": "CANCELADO_ADMIN",
                "motivo": "Cancelado por admin",
            },
            headers=auth_headers_admin,
        )
        assert response.status_code == 200
        body = response.json()
        assert body["estado_nuevo"] == "CANCELADO_ADMIN"

    def test_admin_cancela_confirmado_con_motivo_200(
        self, client: TestClient, auth_headers_admin, pedido_confirmado
    ):
        """ADMIN cancels CONFIRMADO with motivo → 200."""
        url = TRANSICIONAR_URL.format(pedido_id=pedido_confirmado.id)
        response = client.post(
            url,
            json={
                "estado_codigo_destino": "CANCELADO_ADMIN",
                "motivo": "Fraude detectado",
            },
            headers=auth_headers_admin,
        )
        assert response.status_code == 200
        body = response.json()
        assert body["estado_nuevo"] == "CANCELADO_ADMIN"

    def test_admin_cancela_confirmado_sin_motivo_422(
        self, client: TestClient, auth_headers_admin, pedido_confirmado
    ):
        """ADMIN cancels CONFIRMADO without motivo → 422."""
        url = TRANSICIONAR_URL.format(pedido_id=pedido_confirmado.id)
        response = client.post(
            url,
            json={"estado_codigo_destino": "CANCELADO_ADMIN"},
            headers=auth_headers_admin,
        )
        assert response.status_code == 422

    def test_cliente_no_puede_cancelar_como_admin_403(
        self, client: TestClient, auth_headers, pedido_pendiente
    ):
        """CLIENT cannot use CANCELADO_ADMIN → 403."""
        url = TRANSICIONAR_URL.format(pedido_id=pedido_pendiente.id)
        response = client.post(
            url,
            json={"estado_codigo_destino": "CANCELADO_ADMIN"},
            headers=auth_headers,
        )
        assert response.status_code == 403

    def test_fsm_invalida_422(
        self, client: TestClient, auth_headers_admin, pedido_pendiente
    ):
        """Invalid FSM transition → 422."""
        url = TRANSICIONAR_URL.format(pedido_id=pedido_pendiente.id)
        response = client.post(
            url,
            json={"estado_codigo_destino": "ENTREGADO"},
            headers=auth_headers_admin,
        )
        assert response.status_code == 422

    def test_pedido_inexistente_404(self, client: TestClient, auth_headers_admin):
        """Non-existent pedido → 404."""
        url = TRANSICIONAR_URL.format(pedido_id=999999)
        response = client.post(
            url,
            json={"estado_codigo_destino": "CANCELADO_ADMIN"},
            headers=auth_headers_admin,
        )
        assert response.status_code == 404

    def test_response_includes_historial(
        self, client: TestClient, auth_headers_admin, pedido_pendiente
    ):
        """Response includes historial array with the new transition."""
        url = TRANSICIONAR_URL.format(pedido_id=pedido_pendiente.id)
        response = client.post(
            url,
            json={"estado_codigo_destino": "CANCELADO_ADMIN", "motivo": "Test"},
            headers=auth_headers_admin,
        )
        assert response.status_code == 200
        body = response.json()
        assert "historial" in body
        assert len(body["historial"]) >= 1
        assert body["historial"][0]["estado_nuevo_codigo"] == "CANCELADO_ADMIN"

    def test_pedidos_can_cancel_pendiente(
        self, client: TestClient, auth_headers_pedidos, pedido_pendiente
    ):
        """PEDIDOS can cancel PENDIENTE → CANCELADO_ADMIN → 200."""
        url = TRANSICIONAR_URL.format(pedido_id=pedido_pendiente.id)
        response = client.post(
            url,
            json={
                "estado_codigo_destino": "CANCELADO_ADMIN",
                "motivo": "Cancelado por pedidos",
            },
            headers=auth_headers_pedidos,
        )
        assert response.status_code == 200
        assert response.json()["estado_nuevo"] == "CANCELADO_ADMIN"

    def test_pedidos_cannot_cancel_en_preparacion_403(
        self,
        client: TestClient,
        auth_headers_pedidos,
        test_db_session: Session,
        sample_user,
        sample_formas_pago,
        sample_estados_pedido,
    ):
        """PEDIDOS cannot cancel EN_PREPARACION → 403 (RN-RB08)."""
        from features.orders.models import Pedido

        pedido = Pedido(
            user_id=sample_user.id,
            total=Decimal("200.00"),
            costo_envio=Decimal("0.00"),
            forma_pago_codigo="MERCADOPAGO",
            estado_codigo="EN_PREPARACION",
        )
        test_db_session.add(pedido)
        test_db_session.commit()
        test_db_session.refresh(pedido)

        url = TRANSICIONAR_URL.format(pedido_id=pedido.id)
        response = client.post(
            url,
            json={"estado_codigo_destino": "CANCELADO_ADMIN"},
            headers=auth_headers_pedidos,
        )
        assert response.status_code == 403
