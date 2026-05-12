"""
Integration tests for GET /api/v1/pedidos/{id} — order detail endpoint.

Sections:
  - Role-based access (CLIENT own, CLIENT foreign, PEDIDOS, ADMIN, STOCK, no-auth)
  - Anti-leak 404: CLIENT seeing foreign pedido = identical response to non-existent
  - Response shape: historial order, pagos order, decimal serialization
  - Edge cases: no pagos, retiro en local, motivo in historial

Markers:
  pg_only — tests requiring order_items (PG-specific ARRAY type).
"""
from __future__ import annotations

from decimal import Decimal

import pytest
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

BASE_URL = "/api/v1/pedidos"


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

@pytest.fixture
def pedido_de_sample_user(
    test_db_session: Session,
    sample_user,
    sample_estados_pedido,
    sample_formas_pago,
):
    """A Pedido owned by sample_user (CLIENT)."""
    from backend.features.orders.models import Pedido

    pedido = Pedido(
        user_id=sample_user.id,
        total=Decimal("199.99"),
        costo_envio=Decimal("50.00"),
        forma_pago_codigo="MERCADOPAGO",
        estado_codigo="CONFIRMADO",
        notas="Dejar en la puerta",
        direccion_snapshot="Av Siempre Viva 742, Springfield 1000",
    )
    test_db_session.add(pedido)
    test_db_session.commit()
    test_db_session.refresh(pedido)
    return pedido


@pytest.fixture
def historial_para_pedido(test_db_session: Session, pedido_de_sample_user):
    """Add two historial entries to pedido_de_sample_user."""
    from backend.features.orders.models import HistorialEstadoPedido

    h1 = HistorialEstadoPedido(
        pedido_id=pedido_de_sample_user.id,
        estado_anterior_codigo=None,
        estado_nuevo_codigo="PENDIENTE",
        cambiado_por_id=pedido_de_sample_user.user_id,
    )
    h2 = HistorialEstadoPedido(
        pedido_id=pedido_de_sample_user.id,
        estado_anterior_codigo="PENDIENTE",
        estado_nuevo_codigo="CONFIRMADO",
        cambiado_por_id=None,
        motivo=None,
    )
    test_db_session.add_all([h1, h2])
    test_db_session.commit()
    test_db_session.refresh(h1)
    test_db_session.refresh(h2)
    return [h1, h2]


@pytest.fixture
def user_b(test_db_session: Session, sample_roles):
    """A second CLIENT user."""
    from backend.features.users.models import Usuario, UsuarioRol
    from backend.shared.security import hash_password

    user = Usuario(
        email="userb@example.com",
        password_hash=hash_password("password_b"),
        nombre="María",
        apellido="García",
        is_active=True,
    )
    test_db_session.add(user)
    test_db_session.flush()
    test_db_session.add(UsuarioRol(user_id=user.id, role_id=4))  # CLIENT
    test_db_session.commit()
    test_db_session.refresh(user)
    return user


@pytest.fixture
def pedido_de_user_b(
    test_db_session: Session,
    user_b,
    sample_estados_pedido,
    sample_formas_pago,
):
    """A Pedido owned by user_b (foreign to sample_user)."""
    from backend.features.orders.models import Pedido

    pedido = Pedido(
        user_id=user_b.id,
        total=Decimal("99.00"),
        costo_envio=Decimal("50.00"),
        forma_pago_codigo="EFECTIVO",
        estado_codigo="PENDIENTE",
    )
    test_db_session.add(pedido)
    test_db_session.commit()
    test_db_session.refresh(pedido)
    return pedido


@pytest.fixture
def pedidos_role_user(test_db_session: Session, sample_roles):
    from backend.features.users.models import Usuario, UsuarioRol
    from backend.shared.security import hash_password

    user = Usuario(
        email="pedidos@example.com",
        password_hash=hash_password("pedidos_pass"),
        nombre="Operador",
        apellido="Pedidos",
        is_active=True,
    )
    test_db_session.add(user)
    test_db_session.flush()
    test_db_session.add(UsuarioRol(user_id=user.id, role_id=3))  # PEDIDOS
    test_db_session.commit()
    test_db_session.refresh(user)
    return user


@pytest.fixture
def admin_user(test_db_session: Session, sample_roles):
    from backend.features.users.models import Usuario, UsuarioRol
    from backend.shared.security import hash_password

    user = Usuario(
        email="admin@example.com",
        password_hash=hash_password("admin_pass"),
        nombre="Admin",
        apellido="User",
        is_active=True,
    )
    test_db_session.add(user)
    test_db_session.flush()
    test_db_session.add(UsuarioRol(user_id=user.id, role_id=1))  # ADMIN
    test_db_session.commit()
    test_db_session.refresh(user)
    return user


@pytest.fixture
def stock_user(test_db_session: Session, sample_roles):
    from backend.features.users.models import Usuario, UsuarioRol
    from backend.shared.security import hash_password

    user = Usuario(
        email="stock@example.com",
        password_hash=hash_password("stock_pass"),
        nombre="Stock",
        apellido="Manager",
        is_active=True,
    )
    test_db_session.add(user)
    test_db_session.flush()
    test_db_session.add(UsuarioRol(user_id=user.id, role_id=2))  # STOCK
    test_db_session.commit()
    test_db_session.refresh(user)
    return user


def _get_headers(client: TestClient, email: str, password: str) -> dict:
    resp = client.post("/api/v1/auth/login", json={"email": email, "password": password})
    return {"Authorization": f"Bearer {resp.json()['access_token']}"}


# ---------------------------------------------------------------------------
# Role-based access
# ---------------------------------------------------------------------------

class TestRoleAccess:
    def test_client_consulta_su_propio_pedido_200(
        self,
        client: TestClient,
        auth_headers: dict,
        pedido_de_sample_user,
    ):
        """CLIENT owner gets 200 with PedidoDetalle."""
        resp = client.get(f"{BASE_URL}/{pedido_de_sample_user.id}", headers=auth_headers)
        assert resp.status_code == 200
        body = resp.json()
        assert body["id"] == pedido_de_sample_user.id
        assert "items" in body
        assert "historial" in body
        assert "pagos" in body

    def test_client_pedido_ajeno_retorna_404_no_403(
        self,
        client: TestClient,
        auth_headers: dict,
        pedido_de_user_b,
    ):
        """CLIENT requesting foreign pedido → 404 (not 403, anti-leak D2)."""
        resp = client.get(f"{BASE_URL}/{pedido_de_user_b.id}", headers=auth_headers)
        assert resp.status_code == 404
        assert resp.status_code != 403

    def test_pedido_ajeno_y_inexistente_respuesta_identica(
        self,
        client: TestClient,
        auth_headers: dict,
        pedido_de_user_b,
    ):
        """Anti-leak: foreign pedido and non-existent pedido return structurally identical 404."""
        resp_ajeno = client.get(f"{BASE_URL}/{pedido_de_user_b.id}", headers=auth_headers)
        resp_inexistente = client.get(f"{BASE_URL}/99999", headers=auth_headers)
        assert resp_ajeno.status_code == 404
        assert resp_inexistente.status_code == 404
        body_ajeno = resp_ajeno.json()
        body_inexistente = resp_inexistente.json()
        # Same error code and message
        assert body_ajeno.get("code") == body_inexistente.get("code")
        assert body_ajeno.get("detail") == body_inexistente.get("detail")

    def test_pedidos_role_consulta_cualquier_pedido_200(
        self,
        client: TestClient,
        pedidos_role_user,
        pedido_de_sample_user,
    ):
        """PEDIDOS (not owner) can access any pedido → 200."""
        headers = _get_headers(client, "pedidos@example.com", "pedidos_pass")
        resp = client.get(f"{BASE_URL}/{pedido_de_sample_user.id}", headers=headers)
        assert resp.status_code == 200
        assert resp.json()["id"] == pedido_de_sample_user.id

    def test_admin_role_consulta_cualquier_pedido_200(
        self,
        client: TestClient,
        admin_user,
        pedido_de_sample_user,
    ):
        """ADMIN gets 200 on any pedido."""
        headers = _get_headers(client, "admin@example.com", "admin_pass")
        resp = client.get(f"{BASE_URL}/{pedido_de_sample_user.id}", headers=headers)
        assert resp.status_code == 200

    def test_pedido_inexistente_404(
        self,
        client: TestClient,
        auth_headers: dict,
        sample_estados_pedido,
        sample_formas_pago,
    ):
        """Any role, id=9999 (non-existent) → 404."""
        resp = client.get(f"{BASE_URL}/9999", headers=auth_headers)
        assert resp.status_code == 404

    def test_stock_role_rechazado_403(
        self,
        client: TestClient,
        stock_user,
        pedido_de_sample_user,
    ):
        """STOCK-only → 403."""
        headers = _get_headers(client, "stock@example.com", "stock_pass")
        resp = client.get(f"{BASE_URL}/{pedido_de_sample_user.id}", headers=headers)
        assert resp.status_code == 403

    def test_sin_auth_401(self, client: TestClient, pedido_de_sample_user):
        """No auth header → 401."""
        resp = client.get(f"{BASE_URL}/{pedido_de_sample_user.id}")
        assert resp.status_code == 401


# ---------------------------------------------------------------------------
# Response shape
# ---------------------------------------------------------------------------

class TestResponseShape:
    def test_detalle_incluye_historial_cronologico(
        self,
        client: TestClient,
        auth_headers: dict,
        pedido_de_sample_user,
        historial_para_pedido,
    ):
        """historial is ordered by creado_en ASC."""
        resp = client.get(f"{BASE_URL}/{pedido_de_sample_user.id}", headers=auth_headers)
        assert resp.status_code == 200
        historial = resp.json()["historial"]
        assert len(historial) == 2
        fechas = [h["creado_en"] for h in historial]
        assert fechas == sorted(fechas)  # ASC order

    def test_detalle_pedido_sin_pagos_devuelve_lista_vacia(
        self,
        client: TestClient,
        auth_headers: dict,
        pedido_de_sample_user,
    ):
        """PENDIENTE pedido with no payments → pagos == [] (not null)."""
        resp = client.get(f"{BASE_URL}/{pedido_de_sample_user.id}", headers=auth_headers)
        assert resp.status_code == 200
        body = resp.json()
        assert body["pagos"] == []
        assert body["pagos"] is not None

    def test_detalle_retiro_local_direccion_none(
        self,
        client: TestClient,
        test_db_session: Session,
        sample_user,
        sample_estados_pedido,
        sample_formas_pago,
        auth_headers: dict,
    ):
        """Pedido without direccion_snapshot (retiro en local) → direccion_snapshot is null, costo_envio='0.00'."""
        from backend.features.orders.models import Pedido

        pedido = Pedido(
            user_id=sample_user.id,
            total=Decimal("100.00"),
            costo_envio=Decimal("0.00"),
            forma_pago_codigo="EFECTIVO",
            estado_codigo="PENDIENTE",
            direccion_snapshot=None,
        )
        test_db_session.add(pedido)
        test_db_session.commit()
        test_db_session.refresh(pedido)

        resp = client.get(f"{BASE_URL}/{pedido.id}", headers=auth_headers)
        assert resp.status_code == 200
        body = resp.json()
        assert body["direccion_snapshot"] is None
        assert body["costo_envio"] == "0.00"

    def test_detalle_decimal_serializado_como_string(
        self,
        client: TestClient,
        auth_headers: dict,
        pedido_de_sample_user,
    ):
        """Decimal fields (total, costo_envio) are serialized as strings."""
        resp = client.get(f"{BASE_URL}/{pedido_de_sample_user.id}", headers=auth_headers)
        assert resp.status_code == 200
        body = resp.json()
        assert isinstance(body["total"], str)
        assert isinstance(body["costo_envio"], str)
        assert body["total"] == "199.99"

    def test_detalle_notas_y_snapshot(
        self,
        client: TestClient,
        auth_headers: dict,
        pedido_de_sample_user,
    ):
        """notas and direccion_snapshot are correctly returned."""
        resp = client.get(f"{BASE_URL}/{pedido_de_sample_user.id}", headers=auth_headers)
        assert resp.status_code == 200
        body = resp.json()
        assert body["notas"] == "Dejar en la puerta"
        assert body["direccion_snapshot"] == "Av Siempre Viva 742, Springfield 1000"

    def test_detalle_motivo_persistido_en_historial(
        self,
        client: TestClient,
        test_db_session: Session,
        sample_user,
        sample_estados_pedido,
        sample_formas_pago,
        auth_headers: dict,
    ):
        """Pedido cancelado con motivo → historial entry with that motivo."""
        from backend.features.orders.models import HistorialEstadoPedido, Pedido

        pedido = Pedido(
            user_id=sample_user.id,
            total=Decimal("150.00"),
            costo_envio=Decimal("0.00"),
            forma_pago_codigo="EFECTIVO",
            estado_codigo="CANCELADO",
        )
        test_db_session.add(pedido)
        test_db_session.flush()

        hist = HistorialEstadoPedido(
            pedido_id=pedido.id,
            estado_anterior_codigo="CONFIRMADO",
            estado_nuevo_codigo="CANCELADO",
            cambiado_por_id=None,
            motivo="Cliente pidió reembolso",
        )
        test_db_session.add(hist)
        test_db_session.commit()
        test_db_session.refresh(pedido)

        resp = client.get(f"{BASE_URL}/{pedido.id}", headers=auth_headers)
        assert resp.status_code == 200
        historial = resp.json()["historial"]
        cancelacion = next(h for h in historial if h["estado_nuevo_codigo"] == "CANCELADO")
        assert cancelacion["motivo"] == "Cliente pidió reembolso"
        assert cancelacion["estado_anterior_codigo"] == "CONFIRMADO"
