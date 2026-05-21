"""
Integration tests for EN_CAMINO conditional branching (Slice 2).

Business rules:
- Delivery orders (direccion_entrega_id NOT NULL): must go TERMINADO→EN_CAMINO→ENTREGADO.
  Direct TERMINADO→ENTREGADO returns 422 BusinessRuleError.
- Pickup orders (direccion_entrega_id IS NULL): TERMINADO→ENTREGADO succeeds directly.
  TERMINADO→EN_CAMINO returns 422 BusinessRuleError.

Runner: cd backend && uv run pytest tests/integration/test_en_camino_branching.py -v
"""

from __future__ import annotations

from decimal import Decimal

import pytest
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from shared.security import hash_password

TRANSICIONAR_URL = "/api/v1/pedidos/{pedido_id}/transicionar"


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


@pytest.fixture
def auth_headers_pedidos(client: TestClient, test_db_session: Session, sample_roles):
    """Auth headers for a PEDIDOS user."""
    from features.users.models import Usuario, UsuarioRol

    user = Usuario(
        email="pedidos_camino@example.com",
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
        json={"email": "pedidos_camino@example.com", "password": "pedidos_pw_123"},
    )
    return {}


@pytest.fixture
def auth_headers_cocina(client: TestClient, test_db_session: Session, sample_roles):
    """Auth headers for a COCINA user."""
    from features.users.models import Usuario, UsuarioRol
    from features.catalog.models import Rol

    # Ensure COCINA role exists
    from sqlalchemy import select as sa_select
    cocina_role = test_db_session.execute(
        sa_select(Rol).where(Rol.codigo == "COCINA")
    ).scalar_one_or_none()
    if not cocina_role:
        cocina_role = Rol(id=5, codigo="COCINA", descripcion="Cocinero")
        test_db_session.add(cocina_role)
        test_db_session.commit()

    user = Usuario(
        email="cocina_camino@example.com",
        password_hash=hash_password("cocina_pw_123"),
        nombre="Cocina",
        apellido="Camino",
        is_active=True,
    )
    test_db_session.add(user)
    test_db_session.flush()
    test_db_session.add(UsuarioRol(user_id=user.id, role_id=5))  # COCINA
    test_db_session.commit()

    client.post(
        "/api/v1/auth/login",
        json={"email": "cocina_camino@example.com", "password": "cocina_pw_123"},
    )
    return {}


@pytest.fixture
def pedido_terminado_delivery(
    test_db_session: Session, sample_user, sample_formas_pago,
    sample_estados_pedido, sample_address
):
    """A Pedido in TERMINADO state WITH delivery address (direccion_entrega_id NOT NULL)."""
    from features.orders.models import Pedido

    pedido = Pedido(
        user_id=sample_user.id,
        total=Decimal("250.00"),
        costo_envio=Decimal("50.00"),
        forma_pago_codigo="MERCADOPAGO",
        estado_codigo="TERMINADO",
        direccion_entrega_id=sample_address.id,
        direccion_snapshot="Av Siempre Viva 742, Springfield",
    )
    test_db_session.add(pedido)
    test_db_session.commit()
    test_db_session.refresh(pedido)
    return pedido


@pytest.fixture
def pedido_terminado_pickup(
    test_db_session: Session, sample_user, sample_formas_pago, sample_estados_pedido
):
    """A Pedido in TERMINADO state WITHOUT delivery address (pickup, direccion_entrega_id IS NULL)."""
    from features.orders.models import Pedido

    pedido = Pedido(
        user_id=sample_user.id,
        total=Decimal("200.00"),
        costo_envio=Decimal("0.00"),
        forma_pago_codigo="MERCADOPAGO",
        estado_codigo="TERMINADO",
        direccion_entrega_id=None,
    )
    test_db_session.add(pedido)
    test_db_session.commit()
    test_db_session.refresh(pedido)
    return pedido


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------


class TestEnCaminoBranching:
    """EN_CAMINO conditional branching based on delivery mode."""

    def test_delivery_order_must_go_through_en_camino(
        self, client: TestClient, auth_headers_pedidos, pedido_terminado_delivery
    ):
        """Delivery order: TERMINADO→ENTREGADO directly returns 422 BusinessRuleError."""
        url = TRANSICIONAR_URL.format(pedido_id=pedido_terminado_delivery.id)
        response = client.post(
            url,
            json={"estado_codigo_destino": "ENTREGADO"},
            headers=auth_headers_pedidos,
        )
        assert response.status_code == 422
        data = response.json()
        assert "EN_CAMINO" in data.get("detail", "")

    def test_pickup_order_skips_en_camino(
        self, client: TestClient, auth_headers_pedidos, pedido_terminado_pickup
    ):
        """Pickup order: TERMINADO→ENTREGADO succeeds directly."""
        url = TRANSICIONAR_URL.format(pedido_id=pedido_terminado_pickup.id)
        response = client.post(
            url,
            json={"estado_codigo_destino": "ENTREGADO"},
            headers=auth_headers_pedidos,
        )
        assert response.status_code == 200
        assert response.json()["estado_nuevo"] == "ENTREGADO"

    def test_pickup_order_cannot_go_en_camino(
        self, client: TestClient, auth_headers_pedidos, pedido_terminado_pickup
    ):
        """Pickup order: TERMINADO→EN_CAMINO returns 422 BusinessRuleError."""
        url = TRANSICIONAR_URL.format(pedido_id=pedido_terminado_pickup.id)
        response = client.post(
            url,
            json={"estado_codigo_destino": "EN_CAMINO"},
            headers=auth_headers_pedidos,
        )
        assert response.status_code == 422
        data = response.json()
        assert "retiro" in data.get("detail", "").lower() or "local" in data.get("detail", "").lower()

    def test_en_camino_to_entregado(
        self, client: TestClient, auth_headers_pedidos, pedido_terminado_delivery
    ):
        """After TERMINADO→EN_CAMINO, EN_CAMINO→ENTREGADO succeeds."""
        url = TRANSICIONAR_URL.format(pedido_id=pedido_terminado_delivery.id)

        # First: TERMINADO→EN_CAMINO
        response = client.post(
            url,
            json={"estado_codigo_destino": "EN_CAMINO"},
            headers=auth_headers_pedidos,
        )
        assert response.status_code == 200
        assert response.json()["estado_nuevo"] == "EN_CAMINO"

        # Second: EN_CAMINO→ENTREGADO
        response = client.post(
            url,
            json={"estado_codigo_destino": "ENTREGADO"},
            headers=auth_headers_pedidos,
        )
        assert response.status_code == 200
        assert response.json()["estado_nuevo"] == "ENTREGADO"

    def test_cocina_cannot_transition_en_camino(
        self, client: TestClient, auth_headers_cocina, pedido_terminado_delivery
    ):
        """COCINA role REJECTED for TERMINADO→EN_CAMINO (only PEDIDOS/ADMIN can dispatch)."""
        url = TRANSICIONAR_URL.format(pedido_id=pedido_terminado_delivery.id)
        response = client.post(
            url,
            json={"estado_codigo_destino": "EN_CAMINO"},
            headers=auth_headers_cocina,
        )
        assert response.status_code == 403
