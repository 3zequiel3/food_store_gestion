"""
Integration tests for admin metrics endpoints.

Covers:
  GET /api/v1/admin/metricas/resumen            — US-056
  GET /api/v1/admin/metricas/ventas-por-periodo — US-057
  GET /api/v1/admin/metricas/top-productos      — US-058
  GET /api/v1/admin/metricas/pedidos-por-estado — US-059

Test strategy:
- Orders inserted directly into the `orders` table (no order_items — ARRAY(Integer) is PG-only).
- Top-productos test uses the orders table join with order_items, so it uses
  a pg_only marker. The resumen/ventas/estados endpoints work on orders alone.
- Auth: ADMIN role required; CLIENT gets 403.
"""

from __future__ import annotations

from datetime import date, datetime, timezone
from decimal import Decimal

import pytest
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from backend.shared.security import hash_password


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _make_user(session: Session, email: str, role_ids: list[int]):
    """Create a user with given roles."""
    from backend.features.users.models import Usuario, UsuarioRol

    user = Usuario(
        email=email,
        password_hash=hash_password("test_pass_123"),
        nombre="Test",
        apellido="User",
        is_active=True,
    )
    session.add(user)
    session.flush()
    for role_id in role_ids:
        session.add(UsuarioRol(user_id=user.id, role_id=role_id))
    session.commit()
    session.refresh(user)
    return user


def _make_pedido(
    session: Session,
    user_id: int,
    total: Decimal,
    estado_codigo: str = "PENDIENTE",
    creado_en: datetime | None = None,
) -> int:
    """
    Insert a Pedido directly (bypassing UoW/service).

    Does NOT insert DetallePedido (order_items) — that table requires ARRAY(Integer),
    which is PostgreSQL-only and unavailable in SQLite tests.
    """
    from backend.features.orders.models import Pedido

    pedido = Pedido(
        user_id=user_id,
        total=total,
        costo_envio=Decimal("0"),
        forma_pago_codigo="EFECTIVO",
        estado_codigo=estado_codigo,
    )
    session.add(pedido)
    session.flush()

    if creado_en is not None:
        # Override the server default with the explicit timestamp for date-filter tests.
        # Use UPDATE after flush so the instance is persistent.
        from sqlalchemy import update
        from backend.features.orders.models import Pedido as PedidoModel
        session.execute(
            update(PedidoModel)
            .where(PedidoModel.id == pedido.id)
            .values(creado_en=creado_en)
        )

    session.commit()
    session.refresh(pedido)
    return pedido.id


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


@pytest.fixture
def admin_user(test_db_session: Session, sample_roles):
    return _make_user(test_db_session, "admin_metrics@example.com", role_ids=[1])  # ADMIN


@pytest.fixture
def client_user(test_db_session: Session, sample_roles):
    return _make_user(test_db_session, "client_metrics@example.com", role_ids=[4])  # CLIENT


@pytest.fixture
def admin_headers(client: TestClient, admin_user):
    resp = client.post(
        "/api/v1/auth/login",
        json={"email": "admin_metrics@example.com", "password": "test_pass_123"},
    )
    assert resp.status_code == 200, f"Login failed: {resp.json()}"
    return {}


@pytest.fixture
def client_headers(client: TestClient, client_user):
    resp = client.post(
        "/api/v1/auth/login",
        json={"email": "client_metrics@example.com", "password": "test_pass_123"},
    )
    assert resp.status_code == 200, f"Login failed: {resp.json()}"
    return {}


# ---------------------------------------------------------------------------
# GET /resumen — US-056
# ---------------------------------------------------------------------------


class TestResumen:
    def test_resumen_empty_returns_zeros(self, client, admin_headers):
        """With no orders, all numeric fields should be zero."""
        resp = client.get("/api/v1/admin/metricas/resumen", headers=admin_headers)
        assert resp.status_code == 200
        data = resp.json()
        assert Decimal(data["total_ventas"]) == Decimal("0")
        assert data["total_pedidos"] == 0
        assert Decimal(data["ticket_promedio"]) == Decimal("0")
        # total_usuarios includes the admin itself
        assert data["total_usuarios"] >= 1

    def test_resumen_con_pedidos(
        self,
        client,
        admin_headers,
        admin_user,
        test_db_session,
        sample_estados_pedido,
        sample_formas_pago,
    ):
        """Resumen reflects the actual sum and count of orders."""
        _make_pedido(test_db_session, admin_user.id, Decimal("200.00"))
        _make_pedido(test_db_session, admin_user.id, Decimal("300.00"))

        resp = client.get("/api/v1/admin/metricas/resumen", headers=admin_headers)
        assert resp.status_code == 200
        data = resp.json()

        assert data["total_pedidos"] == 2
        assert Decimal(data["total_ventas"]) == Decimal("500.00")
        assert Decimal(data["ticket_promedio"]) == Decimal("250.00")

    def test_resumen_filtro_fecha(
        self,
        client,
        admin_headers,
        admin_user,
        test_db_session,
        sample_estados_pedido,
        sample_formas_pago,
    ):
        """Filtro de fecha excluye pedidos fuera del rango."""
        old_ts = datetime(2025, 1, 15, 12, 0, 0, tzinfo=timezone.utc)
        new_ts = datetime(2026, 5, 1, 12, 0, 0, tzinfo=timezone.utc)

        _make_pedido(test_db_session, admin_user.id, Decimal("100.00"), creado_en=old_ts)
        _make_pedido(test_db_session, admin_user.id, Decimal("400.00"), creado_en=new_ts)

        resp = client.get(
            "/api/v1/admin/metricas/resumen",
            params={"desde": "2026-01-01", "hasta": "2026-12-31"},
            headers=admin_headers,
        )
        assert resp.status_code == 200
        data = resp.json()

        assert data["total_pedidos"] == 1
        assert Decimal(data["total_ventas"]) == Decimal("400.00")

    def test_resumen_requires_admin(self, client, client_headers):
        """CLIENT cannot access resumen — expects 403."""
        resp = client.get("/api/v1/admin/metricas/resumen", headers=client_headers)
        assert resp.status_code == 403

    def test_resumen_requires_auth(self, client):
        """Unauthenticated request returns 401."""
        resp = client.get("/api/v1/admin/metricas/resumen")
        assert resp.status_code == 401


# ---------------------------------------------------------------------------
# GET /ventas-por-periodo — US-057
# ---------------------------------------------------------------------------


class TestVentasPorPeriodo:
    def test_ventas_por_periodo_empty(self, client, admin_headers):
        """No orders → empty puntos list."""
        resp = client.get(
            "/api/v1/admin/metricas/ventas-por-periodo", headers=admin_headers
        )
        assert resp.status_code == 200
        data = resp.json()
        assert data["puntos"] == []
        assert data["granularidad"] == "dia"

    def test_ventas_por_periodo_dia(
        self,
        client,
        admin_headers,
        admin_user,
        test_db_session,
        sample_estados_pedido,
        sample_formas_pago,
    ):
        """Two orders on the same day appear as one punto; different days → two puntos."""
        day1 = datetime(2026, 5, 1, 10, 0, 0, tzinfo=timezone.utc)
        day2 = datetime(2026, 5, 3, 10, 0, 0, tzinfo=timezone.utc)

        _make_pedido(test_db_session, admin_user.id, Decimal("100.00"), creado_en=day1)
        _make_pedido(test_db_session, admin_user.id, Decimal("50.00"), creado_en=day1)
        _make_pedido(test_db_session, admin_user.id, Decimal("200.00"), creado_en=day2)

        resp = client.get(
            "/api/v1/admin/metricas/ventas-por-periodo",
            params={"granularidad": "dia"},
            headers=admin_headers,
        )
        assert resp.status_code == 200
        data = resp.json()
        puntos = {p["periodo"]: p for p in data["puntos"]}

        assert "2026-05-01" in puntos
        assert "2026-05-03" in puntos
        assert Decimal(puntos["2026-05-01"]["total_ventas"]) == Decimal("150.00")
        assert puntos["2026-05-01"]["cantidad_pedidos"] == 2
        assert Decimal(puntos["2026-05-03"]["total_ventas"]) == Decimal("200.00")

    def test_ventas_por_periodo_mes(
        self,
        client,
        admin_headers,
        admin_user,
        test_db_session,
        sample_estados_pedido,
        sample_formas_pago,
    ):
        """Granularidad 'mes' groups orders by YYYY-MM."""
        may = datetime(2026, 5, 15, 10, 0, 0, tzinfo=timezone.utc)
        jun = datetime(2026, 6, 1, 10, 0, 0, tzinfo=timezone.utc)

        _make_pedido(test_db_session, admin_user.id, Decimal("300.00"), creado_en=may)
        _make_pedido(test_db_session, admin_user.id, Decimal("500.00"), creado_en=jun)

        resp = client.get(
            "/api/v1/admin/metricas/ventas-por-periodo",
            params={"granularidad": "mes"},
            headers=admin_headers,
        )
        assert resp.status_code == 200
        data = resp.json()
        assert data["granularidad"] == "mes"
        puntos = {p["periodo"]: p for p in data["puntos"]}
        assert "2026-05" in puntos
        assert "2026-06" in puntos

    def test_ventas_por_periodo_requires_admin(self, client, client_headers):
        resp = client.get(
            "/api/v1/admin/metricas/ventas-por-periodo", headers=client_headers
        )
        assert resp.status_code == 403


# ---------------------------------------------------------------------------
# GET /top-productos — US-058
# ---------------------------------------------------------------------------


class TestTopProductos:
    @pytest.mark.pg_only
    def test_top_productos_empty(self, client, admin_headers):
        """No order items → empty productos list. Requires PG (order_items uses ARRAY)."""
        resp = client.get("/api/v1/admin/metricas/top-productos", headers=admin_headers)
        assert resp.status_code == 200
        data = resp.json()
        assert data["productos"] == []
        assert data["top"] == 10

    @pytest.mark.pg_only
    def test_top_productos_custom_top(self, client, admin_headers):
        """top param is echoed back in response. Requires PG (order_items uses ARRAY)."""
        resp = client.get(
            "/api/v1/admin/metricas/top-productos",
            params={"top": 5},
            headers=admin_headers,
        )
        assert resp.status_code == 200
        assert resp.json()["top"] == 5

    def test_top_productos_requires_admin(self, client, client_headers):
        resp = client.get(
            "/api/v1/admin/metricas/top-productos", headers=client_headers
        )
        assert resp.status_code == 403

    def test_top_productos_invalid_top(self, client, admin_headers):
        """top > 50 should be rejected with 422."""
        resp = client.get(
            "/api/v1/admin/metricas/top-productos",
            params={"top": 100},
            headers=admin_headers,
        )
        assert resp.status_code == 422


# ---------------------------------------------------------------------------
# GET /pedidos-por-estado — US-059
# ---------------------------------------------------------------------------


class TestPedidosPorEstado:
    def test_pedidos_por_estado_empty(self, client, admin_headers):
        """No orders → empty distribucion list."""
        resp = client.get(
            "/api/v1/admin/metricas/pedidos-por-estado", headers=admin_headers
        )
        assert resp.status_code == 200
        data = resp.json()
        assert data["distribucion"] == []

    def test_pedidos_por_estado_con_datos(
        self,
        client,
        admin_headers,
        admin_user,
        test_db_session,
        sample_estados_pedido,
        sample_formas_pago,
    ):
        """Distribution reflects state counts accurately."""
        _make_pedido(test_db_session, admin_user.id, Decimal("100.00"), estado_codigo="PENDIENTE")
        _make_pedido(test_db_session, admin_user.id, Decimal("200.00"), estado_codigo="PENDIENTE")
        _make_pedido(test_db_session, admin_user.id, Decimal("300.00"), estado_codigo="ENTREGADO")

        resp = client.get(
            "/api/v1/admin/metricas/pedidos-por-estado", headers=admin_headers
        )
        assert resp.status_code == 200
        data = resp.json()
        dist = {d["estado_codigo"]: d["cantidad"] for d in data["distribucion"]}

        assert dist["PENDIENTE"] == 2
        assert dist["ENTREGADO"] == 1

    def test_pedidos_por_estado_filtro_fecha(
        self,
        client,
        admin_headers,
        admin_user,
        test_db_session,
        sample_estados_pedido,
        sample_formas_pago,
    ):
        """Date filter restricts the distribution to the given range."""
        old = datetime(2024, 6, 1, tzinfo=timezone.utc)
        recent = datetime(2026, 5, 10, tzinfo=timezone.utc)

        _make_pedido(test_db_session, admin_user.id, Decimal("100.00"), estado_codigo="CANCELADO", creado_en=old)
        _make_pedido(test_db_session, admin_user.id, Decimal("200.00"), estado_codigo="ENTREGADO", creado_en=recent)

        resp = client.get(
            "/api/v1/admin/metricas/pedidos-por-estado",
            params={"desde": "2026-01-01"},
            headers=admin_headers,
        )
        assert resp.status_code == 200
        dist = {d["estado_codigo"]: d["cantidad"] for d in resp.json()["distribucion"]}

        assert "ENTREGADO" in dist
        assert "CANCELADO" not in dist

    def test_pedidos_por_estado_requires_admin(self, client, client_headers):
        resp = client.get(
            "/api/v1/admin/metricas/pedidos-por-estado", headers=client_headers
        )
        assert resp.status_code == 403
