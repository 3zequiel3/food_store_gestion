"""
Integration tests for GET /api/v1/pedidos — order list endpoint.

Sections:
  - Role-based access (CLIENT, PEDIDOS, ADMIN, STOCK, no-auth)
  - Filters: estado, desde/hasta, q (numeric/string)
  - Pagination and ordering
  - Response shape validation

Markers:
  pg_only — tests that need order_items table (items_count, no-N+1 assertions).
"""
from __future__ import annotations

from datetime import date, datetime, timezone
from decimal import Decimal

import pytest
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

BASE_URL = "/api/v1/pedidos"


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

@pytest.fixture
def sample_pedidos_user_a(test_db_session: Session, sample_user, sample_estados_pedido, sample_formas_pago):
    """Create 3 Pedidos belonging to sample_user (CLIENT)."""
    from features.orders.models import Pedido

    pedidos = [
        Pedido(
            user_id=sample_user.id,
            total=Decimal("100.00"),
            costo_envio=Decimal("50.00"),
            forma_pago_codigo="MERCADOPAGO",
            estado_codigo="PENDIENTE",
        ),
        Pedido(
            user_id=sample_user.id,
            total=Decimal("200.00"),
            costo_envio=Decimal("0.00"),
            forma_pago_codigo="EFECTIVO",
            estado_codigo="CONFIRMADO",
        ),
        Pedido(
            user_id=sample_user.id,
            total=Decimal("300.00"),
            costo_envio=Decimal("50.00"),
            forma_pago_codigo="TRANSFERENCIA",
            estado_codigo="ENTREGADO",
        ),
    ]
    for p in pedidos:
        test_db_session.add(p)
    test_db_session.commit()
    for p in pedidos:
        test_db_session.refresh(p)
    return pedidos


@pytest.fixture
def user_b(test_db_session: Session, sample_roles):
    """A second CLIENT user."""
    from features.users.models import Usuario, UsuarioRol
    from shared.security import hash_password

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
def pedidos_user_b(test_db_session: Session, user_b, sample_estados_pedido, sample_formas_pago):
    """Create 2 Pedidos belonging to user_b."""
    from features.orders.models import Pedido

    pedidos = [
        Pedido(
            user_id=user_b.id,
            total=Decimal("500.00"),
            costo_envio=Decimal("50.00"),
            forma_pago_codigo="MERCADOPAGO",
            estado_codigo="CONFIRMADO",
        ),
        Pedido(
            user_id=user_b.id,
            total=Decimal("600.00"),
            costo_envio=Decimal("0.00"),
            forma_pago_codigo="EFECTIVO",
            estado_codigo="CANCELADO",
        ),
    ]
    for p in pedidos:
        test_db_session.add(p)
    test_db_session.commit()
    for p in pedidos:
        test_db_session.refresh(p)
    return pedidos


@pytest.fixture
def pedidos_role(test_db_session: Session, sample_roles):
    """Create a PEDIDOS user and return JWT headers."""
    from features.users.models import Usuario, UsuarioRol
    from shared.security import hash_password

    user = Usuario(
        email="pedidos@example.com",
        password_hash=hash_password("pedidos_pass"),
        nombre="Juan",
        apellido="Pérez",
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
    """Create an ADMIN user."""
    from features.users.models import Usuario, UsuarioRol
    from shared.security import hash_password

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
    """Create a STOCK-only user."""
    from features.users.models import Usuario, UsuarioRol
    from shared.security import hash_password

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
    return {}


# ---------------------------------------------------------------------------
# Role-based access
# ---------------------------------------------------------------------------

class TestRoleAccess:
    def test_client_solo_ve_sus_propios_pedidos(
        self,
        client: TestClient,
        auth_headers: dict,
        sample_pedidos_user_a,
        pedidos_user_b,
    ):
        """CLIENT with 3 own pedidos + 2 of user_b → total=3."""
        resp = client.get(BASE_URL, headers=auth_headers)
        assert resp.status_code == 200
        body = resp.json()
        assert body["total"] == 3
        assert len(body["items"]) == 3

    def test_pedidos_role_ve_todos(
        self,
        client: TestClient,
        pedidos_role,
        sample_pedidos_user_a,
        pedidos_user_b,
    ):
        """PEDIDOS sees all 5 pedidos."""
        headers = _get_headers(client, "pedidos@example.com", "pedidos_pass")
        resp = client.get(BASE_URL, headers=headers)
        assert resp.status_code == 200
        body = resp.json()
        assert body["total"] == 5

    def test_admin_role_ve_todos(
        self,
        client: TestClient,
        admin_user,
        sample_pedidos_user_a,
        pedidos_user_b,
    ):
        """ADMIN sees all 5 pedidos."""
        headers = _get_headers(client, "admin@example.com", "admin_pass")
        resp = client.get(BASE_URL, headers=headers)
        assert resp.status_code == 200
        body = resp.json()
        assert body["total"] == 5

    def test_stock_role_rechazado_403(self, client: TestClient, stock_user):
        """STOCK-only user gets 403."""
        headers = _get_headers(client, "stock@example.com", "stock_pass")
        resp = client.get(BASE_URL, headers=headers)
        assert resp.status_code == 403

    def test_sin_auth_retorna_401(self, client: TestClient):
        """No auth header → 401."""
        resp = client.get(BASE_URL)
        assert resp.status_code == 401


# ---------------------------------------------------------------------------
# Filters
# ---------------------------------------------------------------------------

class TestFilters:
    def test_filtro_por_estado(
        self,
        client: TestClient,
        pedidos_role,
        sample_pedidos_user_a,
        pedidos_user_b,
    ):
        """PEDIDOS filters ?estado=CONFIRMADO → only CONFIRMADO pedidos."""
        headers = _get_headers(client, "pedidos@example.com", "pedidos_pass")
        resp = client.get(BASE_URL + "?estado=CONFIRMADO", headers=headers)
        assert resp.status_code == 200
        body = resp.json()
        assert body["total"] == 2  # one from user_a, one from user_b
        assert all(item["estado_codigo"] == "CONFIRMADO" for item in body["items"])

    def test_filtro_estado_invalido_422(self, client: TestClient, auth_headers: dict):
        """Invalid estado value → 422."""
        resp = client.get(BASE_URL + "?estado=PAGADO", headers=auth_headers)
        assert resp.status_code == 422

    def test_desde_mayor_que_hasta_retorna_422(self, client: TestClient, auth_headers: dict):
        """desde > hasta → 422 with clear message."""
        resp = client.get(BASE_URL + "?desde=2026-12-31&hasta=2026-01-01", headers=auth_headers)
        assert resp.status_code == 422
        body_text = str(resp.json())
        assert "desde" in body_text.lower() or "posterior" in body_text.lower()

    def test_filtro_q_numerico_busca_por_id(
        self,
        client: TestClient,
        pedidos_role,
        sample_pedidos_user_a,
    ):
        """q=<id> → returns only the pedido with that id."""
        target_id = sample_pedidos_user_a[0].id
        headers = _get_headers(client, "pedidos@example.com", "pedidos_pass")
        resp = client.get(BASE_URL + f"?q={target_id}", headers=headers)
        assert resp.status_code == 200
        body = resp.json()
        assert body["total"] == 1
        assert body["items"][0]["id"] == target_id

    def test_filtro_q_string_busca_por_nombre_ilike(
        self,
        client: TestClient,
        pedidos_role,
        sample_pedidos_user_a,
        pedidos_user_b,
        user_b,
    ):
        """q=garcía (lowercase) → returns pedidos of user_b (García)."""
        headers = _get_headers(client, "pedidos@example.com", "pedidos_pass")
        resp = client.get(BASE_URL + "?q=garc%C3%ADa", headers=headers)
        assert resp.status_code == 200
        body = resp.json()
        ids_returned = {item["id"] for item in body["items"]}
        ids_user_b = {p.id for p in pedidos_user_b}
        assert ids_returned == ids_user_b

    def test_limit_fuera_de_rango_422(self, client: TestClient, auth_headers: dict):
        """limit > 100 or limit < 1 → 422."""
        resp_high = client.get(BASE_URL + "?limit=500", headers=auth_headers)
        assert resp_high.status_code == 422
        resp_zero = client.get(BASE_URL + "?limit=0", headers=auth_headers)
        assert resp_zero.status_code == 422


# ---------------------------------------------------------------------------
# Pagination and ordering
# ---------------------------------------------------------------------------

class TestPaginationOrdering:
    @pytest.fixture
    def veinticinico_pedidos(
        self,
        test_db_session: Session,
        sample_user,
        sample_estados_pedido,
        sample_formas_pago,
    ):
        """Seed 25 pedidos for sample_user."""
        from features.orders.models import Pedido

        pedidos = [
            Pedido(
                user_id=sample_user.id,
                total=Decimal(f"{i + 1}.00"),
                costo_envio=Decimal("0.00"),
                forma_pago_codigo="EFECTIVO",
                estado_codigo="PENDIENTE",
            )
            for i in range(25)
        ]
        for p in pedidos:
            test_db_session.add(p)
        test_db_session.commit()
        for p in pedidos:
            test_db_session.refresh(p)
        return pedidos

    def test_paginacion_page_2(
        self, client: TestClient, auth_headers: dict, veinticinico_pedidos
    ):
        """25 pedidos, page=2&limit=10 → 10 items, total=25."""
        resp = client.get(BASE_URL + "?page=2&limit=10", headers=auth_headers)
        assert resp.status_code == 200
        body = resp.json()
        assert body["total"] == 25
        assert body["page"] == 2
        assert body["limit"] == 10
        assert len(body["items"]) == 10

    def test_paginacion_fuera_de_rango(
        self, client: TestClient, auth_headers: dict, veinticinico_pedidos
    ):
        """page=10&limit=10 with 25 total → items=[], total=25."""
        resp = client.get(BASE_URL + "?page=10&limit=10", headers=auth_headers)
        assert resp.status_code == 200
        body = resp.json()
        assert body["total"] == 25
        assert body["items"] == []
        assert body["page"] == 10

    def test_orden_creado_en_desc(
        self,
        client: TestClient,
        auth_headers: dict,
        sample_pedidos_user_a,
    ):
        """Items ordered creado_en DESC — first item has largest creado_en."""
        resp = client.get(BASE_URL, headers=auth_headers)
        assert resp.status_code == 200
        items = resp.json()["items"]
        assert len(items) == 3
        fechas = [item["creado_en"] for item in items]
        assert fechas == sorted(fechas, reverse=True)

    def test_total_respeta_filtros_de_ownership(
        self,
        client: TestClient,
        auth_headers: dict,
        sample_pedidos_user_a,
        pedidos_user_b,
    ):
        """CLIENT with 3 own pedidos and 2 foreign → total=3 (not 13)."""
        resp = client.get(BASE_URL, headers=auth_headers)
        assert resp.status_code == 200
        assert resp.json()["total"] == 3

    def test_page_negativo_o_cero_422(self, client: TestClient, auth_headers: dict):
        """page=0 → 422."""
        resp = client.get(BASE_URL + "?page=0", headers=auth_headers)
        assert resp.status_code == 422


# ---------------------------------------------------------------------------
# Response shape
# ---------------------------------------------------------------------------

class TestResponseShape:
    def test_items_count_en_response(
        self,
        client: TestClient,
        auth_headers: dict,
        sample_pedidos_user_a,
    ):
        """Each PedidoListItem has an items_count field."""
        resp = client.get(BASE_URL, headers=auth_headers)
        assert resp.status_code == 200
        for item in resp.json()["items"]:
            assert "items_count" in item
            assert isinstance(item["items_count"], int)

    def test_items_no_contienen_relaciones(
        self,
        client: TestClient,
        auth_headers: dict,
        sample_pedidos_user_a,
    ):
        """List items must NOT contain items/historial/pagos/direccion_snapshot."""
        resp = client.get(BASE_URL, headers=auth_headers)
        assert resp.status_code == 200
        for item in resp.json()["items"]:
            assert "items" not in item
            assert "historial" not in item
            assert "pagos" not in item
            assert "direccion_snapshot" not in item

    def test_total_serializado_como_string(
        self,
        client: TestClient,
        auth_headers: dict,
        sample_pedidos_user_a,
    ):
        """Decimal fields serialized as strings (no float precision loss)."""
        resp = client.get(BASE_URL, headers=auth_headers)
        assert resp.status_code == 200
        for item in resp.json()["items"]:
            assert isinstance(item["total"], str)
            assert isinstance(item["costo_envio"], str)
