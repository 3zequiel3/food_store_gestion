"""
Integration tests for Kitchen Display System (KDS) REST endpoint (Slice 3).

Tests GET /api/v1/cocina/pedidos:
- Returns orders in CONFIRMADO and EN_PREPARACION states
- Sorted by kitchen entry time (oldest first)
- Excludes TERMINADO/ENTREGADO/CANCELADO states
- Authorization: COCINA and ADMIN roles allowed, CLIENT gets 403

NOTE: These tests require PostgreSQL because the KDS service uses
selectinload(Pedido.items) which queries the order_items table (PG ARRAY type).

Runner: cd backend && uv run pytest tests/integration/test_cocina_kds.py -v --pg
"""

from __future__ import annotations

from datetime import datetime, timedelta, timezone
from decimal import Decimal

import pytest
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from shared.security import hash_password

KDS_URL = "/api/v1/cocina/pedidos"


@pytest.fixture(scope="module")
def vcr_config():
    return {"filter_headers": ["authorization"]}


# Mark all tests in this module as requiring PostgreSQL
pytestmark = pytest.mark.pg_only


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


@pytest.fixture
def auth_headers_cocina(client: TestClient, test_db_session: Session, sample_roles):
    """Auth headers for a COCINA user."""
    from features.users.models import Usuario, UsuarioRol
    from features.catalog.models import Rol
    from sqlalchemy import select as sa_select

    cocina_role = test_db_session.execute(
        sa_select(Rol).where(Rol.codigo == "COCINA")
    ).scalar_one_or_none()
    if not cocina_role:
        cocina_role = Rol(id=5, codigo="COCINA", descripcion="Cocinero")
        test_db_session.add(cocina_role)
        test_db_session.commit()

    user = Usuario(
        email="cocina_kds@example.com",
        password_hash=hash_password("cocina_pw_123"),
        nombre="Cocina",
        apellido="KDS",
        is_active=True,
    )
    test_db_session.add(user)
    test_db_session.flush()
    test_db_session.add(UsuarioRol(user_id=user.id, role_id=5))
    test_db_session.commit()

    client.post(
        "/api/v1/auth/login",
        json={"email": "cocina_kds@example.com", "password": "cocina_pw_123"},
    )
    return {}


@pytest.fixture
def auth_headers_admin(client: TestClient, test_db_session: Session, sample_roles):
    """Auth headers for an ADMIN user."""
    from features.users.models import Usuario, UsuarioRol

    user = Usuario(
        email="admin_kds@example.com",
        password_hash=hash_password("admin_kds_pw"),
        nombre="Admin",
        apellido="KDS",
        is_active=True,
    )
    test_db_session.add(user)
    test_db_session.flush()
    test_db_session.add(UsuarioRol(user_id=user.id, role_id=1))
    test_db_session.commit()

    client.post(
        "/api/v1/auth/login",
        json={"email": "admin_kds@example.com", "password": "admin_kds_pw"},
    )
    return {}


@pytest.fixture
def auth_headers_client(client: TestClient, sample_user):
    """Auth headers for a CLIENT user (should be forbidden)."""
    client.post(
        "/api/v1/auth/login",
        json={"email": "test@example.com", "password": "test_password_123"},
    )
    return {}


@pytest.fixture
def pedido_confirmado_con_historial(
    test_db_session: Session, sample_user, sample_formas_pago, sample_estados_pedido
):
    """A Pedido in CONFIRMADO state with historial entry for kitchen entry time."""
    from features.orders.models import Pedido, HistorialEstadoPedido

    pedido = Pedido(
        user_id=sample_user.id,
        total=Decimal("200.00"),
        costo_envio=Decimal("0.00"),
        forma_pago_codigo="MERCADOPAGO",
        estado_codigo="CONFIRMADO",
    )
    test_db_session.add(pedido)
    test_db_session.flush()

    # Add historial entry for CONFIRMADO transition (kitchen entry time)
    historial = HistorialEstadoPedido(
        pedido_id=pedido.id,
        estado_anterior_codigo="PENDIENTE",
        estado_nuevo_codigo="CONFIRMADO",
        cambiado_por_id=sample_user.id,
    )
    test_db_session.add(historial)
    test_db_session.commit()
    test_db_session.refresh(pedido)
    return pedido


@pytest.fixture
def pedido_en_preparacion_con_historial(
    test_db_session: Session, sample_user, sample_formas_pago, sample_estados_pedido
):
    """A Pedido in EN_PREPARACION state with historial entry."""
    from features.orders.models import Pedido, HistorialEstadoPedido

    pedido = Pedido(
        user_id=sample_user.id,
        total=Decimal("150.00"),
        costo_envio=Decimal("0.00"),
        forma_pago_codigo="MERCADOPAGO",
        estado_codigo="EN_PREPARACION",
    )
    test_db_session.add(pedido)
    test_db_session.flush()

    historial = HistorialEstadoPedido(
        pedido_id=pedido.id,
        estado_anterior_codigo="CONFIRMADO",
        estado_nuevo_codigo="CONFIRMADO",
        cambiado_por_id=sample_user.id,
    )
    test_db_session.add(historial)
    test_db_session.commit()
    test_db_session.refresh(pedido)
    return pedido


@pytest.fixture
def pedido_terminado_con_historial(
    test_db_session: Session, sample_user, sample_formas_pago, sample_estados_pedido
):
    """A Pedido in TERMINADO state (should NOT appear in KDS)."""
    from features.orders.models import Pedido, HistorialEstadoPedido

    pedido = Pedido(
        user_id=sample_user.id,
        total=Decimal("300.00"),
        costo_envio=Decimal("0.00"),
        forma_pago_codigo="MERCADOPAGO",
        estado_codigo="TERMINADO",
    )
    test_db_session.add(pedido)
    test_db_session.flush()

    historial = HistorialEstadoPedido(
        pedido_id=pedido.id,
        estado_anterior_codigo="CONFIRMADO",
        estado_nuevo_codigo="CONFIRMADO",
        cambiado_por_id=sample_user.id,
    )
    test_db_session.add(historial)
    test_db_session.commit()
    test_db_session.refresh(pedido)
    return pedido


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------


class TestKdsRestEndpoint:
    """GET /api/v1/cocina/pedidos — REST endpoint for KDS."""

    def test_get_kitchen_orders_cocina_role(
        self, client: TestClient, auth_headers_cocina,
        pedido_confirmado_con_historial, pedido_en_preparacion_con_historial
    ):
        """GET /cocina/pedidos with COCINA role returns 200 with CONFIRMADO and EN_PREPARACION orders."""
        response = client.get(KDS_URL, headers=auth_headers_cocina)
        assert response.status_code == 200
        data = response.json()
        assert isinstance(data, list)
        assert len(data) >= 2
        states = {order["estado"] for order in data}
        assert "CONFIRMADO" in states
        assert "EN_PREPARACION" in states

    def test_get_kitchen_orders_admin_role(
        self, client: TestClient, auth_headers_admin,
        pedido_confirmado_con_historial
    ):
        """GET /cocina/pedidos with ADMIN role returns 200."""
        response = client.get(KDS_URL, headers=auth_headers_admin)
        assert response.status_code == 200
        data = response.json()
        assert isinstance(data, list)

    def test_get_kitchen_orders_client_forbidden(
        self, client: TestClient, auth_headers_client
    ):
        """GET /cocina/pedidos with CLIENT role returns 403."""
        response = client.get(KDS_URL, headers=auth_headers_client)
        assert response.status_code == 403

    def test_get_kitchen_orders_sorted_by_entry_time(
        self, client: TestClient, auth_headers_cocina,
        test_db_session: Session, sample_user, sample_formas_pago, sample_estados_pedido
    ):
        """Orders are sorted by kitchen entry time (oldest first)."""
        from features.orders.models import Pedido, HistorialEstadoPedido
        from datetime import timedelta

        # Create two orders with different CONFIRMADO timestamps
        older_pedido = Pedido(
            user_id=sample_user.id,
            total=Decimal("100.00"),
            costo_envio=Decimal("0.00"),
            forma_pago_codigo="MERCADOPAGO",
            estado_codigo="CONFIRMADO",
        )
        test_db_session.add(older_pedido)
        test_db_session.flush()

        older_hist = HistorialEstadoPedido(
            pedido_id=older_pedido.id,
            estado_anterior_codigo="PENDIENTE",
            estado_nuevo_codigo="CONFIRMADO",
            cambiado_por_id=sample_user.id,
        )
        test_db_session.add(older_hist)
        test_db_session.commit()

        newer_pedido = Pedido(
            user_id=sample_user.id,
            total=Decimal("200.00"),
            costo_envio=Decimal("0.00"),
            forma_pago_codigo="MERCADOPAGO",
            estado_codigo="CONFIRMADO",
        )
        test_db_session.add(newer_pedido)
        test_db_session.flush()

        newer_hist = HistorialEstadoPedido(
            pedido_id=newer_pedido.id,
            estado_anterior_codigo="PENDIENTE",
            estado_nuevo_codigo="CONFIRMADO",
            cambiado_por_id=sample_user.id,
        )
        test_db_session.add(newer_hist)
        test_db_session.commit()

        response = client.get(KDS_URL, headers=auth_headers_cocina)
        assert response.status_code == 200
        data = response.json()
        assert len(data) >= 2

        # First order should be the older one (lower id, earlier entry)
        ids = [order["id"] for order in data]
        assert ids.index(older_pedido.id) < ids.index(newer_pedido.id)

    def test_get_kitchen_orders_excludes_terminated(
        self, client: TestClient, auth_headers_cocina,
        pedido_confirmado_con_historial, pedido_terminado_con_historial
    ):
        """Orders in TERMINADO/ENTREGADO/CANCELADO states are NOT in the response."""
        response = client.get(KDS_URL, headers=auth_headers_cocina)
        assert response.status_code == 200
        data = response.json()

        states = {order["estado"] for order in data}
        assert "TERMINADO" not in states
        assert "ENTREGADO" not in states
        assert "CANCELADO" not in states
        assert "CANCELADO_ADMIN" not in states
        assert "CANCELADO_CLIENTE" not in states

        # But CONFIRMADO should be present
        assert "CONFIRMADO" in states
