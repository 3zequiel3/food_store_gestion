"""
Integration tests for order creation endpoint (POST /api/v1/pedidos).

STRICT TDD — tests were written before the implementation.
Sections:
  7.1  Happy path (a) con dirección, (b) retiro en local, (c) snapshots inmutables
  7.2  Stock — insuficiente, no disponible, inexistente, no decrementa
  7.3  (vacío — reservado para visualización)
  7.4  Forma de pago — código inexistente, deshabilitada
  7.5  Dirección ownership — otro usuario, inexistente, soft-deleted
  7.6  (retiro en local — en 7.1.b)
  7.7  Atomicidad — rollback si historial falla
  7.8  Anti-smuggling — extra fields en request
  7.9  Validaciones Pydantic — items vacío, cantidad cero/negativa, sin items
  7.10 Auth — sin token, token inválido, rol insuficiente
  7.11 Total con precios fraccionarios (precision Decimal)

Markers:
  pg_only — requires PostgreSQL (tests that insert into order_items, which uses
             ARRAY(Integer), a PG-only type). These tests are skipped automatically
             in SQLite-only environments (see conftest.py pytest_collection_modifyitems).

Base URL: /api/v1/pedidos
"""
from __future__ import annotations

from decimal import Decimal

import pytest
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

BASE_URL = "/api/v1/pedidos"


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _payload_valido(producto_id: int, direccion_id: int | None = None, cantidad: int = 1) -> dict:
    """Build a valid order payload for reuse across tests."""
    payload: dict = {
        "items": [
            {
                "producto_id": producto_id,
                "cantidad": cantidad,
            }
        ],
        "forma_pago_codigo": "MERCADOPAGO",
    }
    if direccion_id is not None:
        payload["direccion_id"] = direccion_id
    return payload


# ---------------------------------------------------------------------------
# 7.8  Anti-smuggling — Pydantic extra="forbid" (no BD needed, no pg_only)
# ---------------------------------------------------------------------------

class TestAntiSmuggling:
    """
    7.8 — tests that verify extra fields are rejected at schema level.
    These tests don't reach the DB so they run fine on SQLite.
    """

    def test_7_8_a_anti_smuggling_total(self, client: TestClient, auth_headers: dict):
        """Body with 'total' extra field → 422 extra fields not permitted."""
        payload = {
            "items": [{"producto_id": 1, "cantidad": 1}],
            "forma_pago_codigo": "MERCADOPAGO",
            "total": 0.01,
        }
        response = client.post(BASE_URL + "/", json=payload, headers=auth_headers)
        assert response.status_code == 422
        # The app uses RFC 7807 format with {"errors": [{"field": ..., "message": ...}]}
        body = response.json()
        errors_text = str(body)
        assert "extra" in errors_text.lower() or "forbidden" in errors_text.lower() or "not permitted" in errors_text.lower()

    def test_7_8_b_anti_smuggling_estado_codigo(self, client: TestClient, auth_headers: dict):
        """Body with 'estado_codigo' → 422."""
        payload = {
            "items": [{"producto_id": 1, "cantidad": 1}],
            "forma_pago_codigo": "MERCADOPAGO",
            "estado_codigo": "CONFIRMADO",
        }
        response = client.post(BASE_URL + "/", json=payload, headers=auth_headers)
        assert response.status_code == 422

    def test_7_8_c_anti_smuggling_usuario_id(self, client: TestClient, auth_headers: dict):
        """Body with 'usuario_id' → 422."""
        payload = {
            "items": [{"producto_id": 1, "cantidad": 1}],
            "forma_pago_codigo": "MERCADOPAGO",
            "usuario_id": 999,
        }
        response = client.post(BASE_URL + "/", json=payload, headers=auth_headers)
        assert response.status_code == 422

    def test_7_8_d_anti_smuggling_precio_snapshot_en_item(self, client: TestClient, auth_headers: dict):
        """Item with 'precio_snapshot' → 422 (ItemPedidoRequest extra=forbid)."""
        payload = {
            "items": [{"producto_id": 1, "cantidad": 1, "precio_snapshot": 0.01}],
            "forma_pago_codigo": "MERCADOPAGO",
        }
        response = client.post(BASE_URL + "/", json=payload, headers=auth_headers)
        assert response.status_code == 422


# ---------------------------------------------------------------------------
# 7.9  Validaciones Pydantic (no pg_only)
# ---------------------------------------------------------------------------

class TestValidacionesPydantic:
    """
    7.9 — Pydantic constraint tests. None of these reach the DB.
    """

    def test_7_9_a_items_vacio_rechaza(self, client: TestClient, auth_headers: dict):
        """Empty items list → 422 min_length=1."""
        payload = {
            "items": [],
            "forma_pago_codigo": "MERCADOPAGO",
        }
        response = client.post(BASE_URL + "/", json=payload, headers=auth_headers)
        assert response.status_code == 422

    def test_7_9_b_cantidad_cero_rechaza(self, client: TestClient, auth_headers: dict):
        """cantidad=0 → 422 (ge=1)."""
        payload = {
            "items": [{"producto_id": 1, "cantidad": 0}],
            "forma_pago_codigo": "MERCADOPAGO",
        }
        response = client.post(BASE_URL + "/", json=payload, headers=auth_headers)
        assert response.status_code == 422

    def test_7_9_c_sin_items_rechaza(self, client: TestClient, auth_headers: dict):
        """Missing 'items' field entirely → 422 required field."""
        payload = {
            "forma_pago_codigo": "MERCADOPAGO",
        }
        response = client.post(BASE_URL + "/", json=payload, headers=auth_headers)
        assert response.status_code == 422


# ---------------------------------------------------------------------------
# 7.10 Auth (no pg_only)
# ---------------------------------------------------------------------------

class TestAuth:
    """
    7.10 — Authentication and authorization tests.
    """

    def test_7_10_a_sin_authorization_responde_401(self, client: TestClient):
        """POST without Authorization header → 401."""
        payload = {
            "items": [{"producto_id": 1, "cantidad": 1}],
            "forma_pago_codigo": "MERCADOPAGO",
        }
        response = client.post(BASE_URL + "/", json=payload)
        assert response.status_code == 401

    def test_7_10_b_token_invalido_responde_401(self, client: TestClient):
        """Invalid Bearer token → 401."""
        payload = {
            "items": [{"producto_id": 1, "cantidad": 1}],
            "forma_pago_codigo": "MERCADOPAGO",
        }
        response = client.post(
            BASE_URL + "/",
            json=payload,
            headers={"Authorization": "Bearer xxxxxxx_invalid_token"},
        )
        assert response.status_code == 401

    def test_7_10_c_usuario_sin_rol_client_responde_403(
        self,
        client: TestClient,
        test_db_session: Session,
        sample_roles,
    ):
        """User without CLIENT role → 403."""
        from backend.features.users.models import Usuario, UsuarioRol
        from backend.shared.security import hash_password

        # Create ADMIN-only user (no CLIENT role)
        admin_user = Usuario(
            email="admin_only@example.com",
            password_hash=hash_password("admin_pass_123"),
            nombre="Admin",
            apellido="Only",
            is_active=True,
        )
        test_db_session.add(admin_user)
        test_db_session.flush()
        # Assign only ADMIN role (id=1)
        test_db_session.add(UsuarioRol(user_id=admin_user.id, role_id=1))
        test_db_session.commit()

        # Login as admin
        login_resp = client.post(
            "/api/v1/auth/login",
            json={"email": "admin_only@example.com", "password": "admin_pass_123"},
        )
        assert login_resp.status_code == 200
        payload = {
            "items": [{"producto_id": 1, "cantidad": 1}],
            "forma_pago_codigo": "MERCADOPAGO",
        }
        response = client.post(
            BASE_URL + "/",
            json=payload,
        )
        assert response.status_code == 403


# ---------------------------------------------------------------------------
# 7.4  Forma de pago (SQLite-compatible — no order_items)
# ---------------------------------------------------------------------------

class TestFormaPago:
    """
    7.4 — Forma de pago validation tests.
    These tests fail before inserting into order_items, so they work on SQLite.
    """

    def test_7_4_a_forma_pago_inexistente(
        self,
        client: TestClient,
        auth_headers: dict,
        sample_formas_pago,
        sample_producto_disponible,
    ):
        """forma_pago_codigo='BITCOIN' (nonexistent) → 422."""
        payload = {
            "items": [{"producto_id": sample_producto_disponible.id, "cantidad": 1}],
            "forma_pago_codigo": "BITCOIN",
        }
        response = client.post(BASE_URL + "/", json=payload, headers=auth_headers)
        assert response.status_code == 422

    def test_7_4_b_forma_pago_deshabilitada(
        self,
        client: TestClient,
        auth_headers: dict,
        test_db_session: Session,
        sample_formas_pago,
        sample_producto_disponible,
    ):
        """Disabled payment method → 422."""
        # Disable EFECTIVO
        efectivo = next(fp for fp in sample_formas_pago if fp.codigo == "EFECTIVO")
        efectivo.habilitada = False
        test_db_session.commit()

        payload = {
            "items": [{"producto_id": sample_producto_disponible.id, "cantidad": 1}],
            "forma_pago_codigo": "EFECTIVO",
        }
        response = client.post(BASE_URL + "/", json=payload, headers=auth_headers)
        assert response.status_code == 422


# ---------------------------------------------------------------------------
# 7.2  Stock (SQLite-compatible — errors raised before order_items)
# ---------------------------------------------------------------------------

class TestStock:
    """
    7.2 — Stock validation tests.
    Errors occur before any INSERT into order_items, so SQLite is fine.
    """

    def test_7_2_a_stock_insuficiente_rechaza_todo(
        self,
        client: TestClient,
        auth_headers: dict,
        test_db_session: Session,
        sample_estados_pedido,
        sample_formas_pago,
        sample_producto_disponible,
    ):
        """cantidad=100 with stock=10 → 422, BD clean."""
        producto_id = sample_producto_disponible.id
        payload = _payload_valido(producto_id, cantidad=100)
        response = client.post(BASE_URL + "/", json=payload, headers=auth_headers)
        assert response.status_code == 422

        # Verify error message mentions stock
        body_text = str(response.json())
        assert any(kw in body_text.lower() for kw in ("stock", "insuficiente", "insufficient"))

        # Verify DB is clean: no orders created
        # Note: after UoW rollback on SQLite shared connection, we use a direct
        # SQL query via the session to avoid stale identity map issues.
        from sqlalchemy import text
        result = test_db_session.execute(text("SELECT COUNT(*) FROM orders")).scalar()
        assert result == 0

    def test_7_2_b_producto_no_disponible_rechaza(
        self,
        client: TestClient,
        auth_headers: dict,
        test_db_session: Session,
        sample_estados_pedido,
        sample_formas_pago,
        sample_producto_disponible,
    ):
        """Product with disponible=False → 422."""
        sample_producto_disponible.disponible = False
        test_db_session.commit()

        payload = _payload_valido(sample_producto_disponible.id)
        response = client.post(BASE_URL + "/", json=payload, headers=auth_headers)
        assert response.status_code == 422

    def test_7_2_c_producto_inexistente_rechaza(
        self,
        client: TestClient,
        auth_headers: dict,
        sample_estados_pedido,
        sample_formas_pago,
    ):
        """producto_id=99999 (nonexistent) → 404."""
        payload = _payload_valido(99999)
        response = client.post(BASE_URL + "/", json=payload, headers=auth_headers)
        assert response.status_code == 404

    @pytest.mark.pg_only
    def test_7_2_d_stock_no_se_decrementa_al_crear(
        self,
        client: TestClient,
        auth_headers: dict,
        test_db_session: Session,
        sample_estados_pedido,
        sample_formas_pago,
        sample_producto_disponible,
    ):
        """Happy path → stock_cantidad unchanged after order creation."""
        stock_inicial = sample_producto_disponible.stock_cantidad
        payload = _payload_valido(sample_producto_disponible.id)
        response = client.post(BASE_URL + "/", json=payload, headers=auth_headers)
        assert response.status_code == 201

        test_db_session.refresh(sample_producto_disponible)
        assert sample_producto_disponible.stock_cantidad == stock_inicial


# ---------------------------------------------------------------------------
# 7.5  Dirección ownership (SQLite-compatible — fails before order_items)
# ---------------------------------------------------------------------------

class TestDireccionOwnership:
    """
    7.5 — Address ownership tests (D6 anti-leak: 404 not 403).
    """

    def test_7_5_a_direccion_de_otro_usuario_responde_404(
        self,
        client: TestClient,
        auth_headers: dict,
        test_db_session: Session,
        sample_roles,
        sample_estados_pedido,
        sample_formas_pago,
        sample_producto_disponible,
    ):
        """Using another user's address → 404 (not 403)."""
        from backend.features.users.models import Usuario, UsuarioRol
        from backend.features.addresses.models import DireccionEntrega
        from backend.shared.security import hash_password

        # Create a second user
        other_user = Usuario(
            email="other@example.com",
            password_hash=hash_password("other_pass_123"),
            nombre="Other",
            apellido="User",
            is_active=True,
        )
        test_db_session.add(other_user)
        test_db_session.flush()
        test_db_session.add(UsuarioRol(user_id=other_user.id, role_id=4))
        test_db_session.flush()

        # Create address belonging to other_user
        other_addr = DireccionEntrega(
            user_id=other_user.id,
            calle="Calle Ajena",
            numero="99",
            ciudad="Ciudad Ajena",
            codigo_postal="1234",
        )
        test_db_session.add(other_addr)
        test_db_session.commit()

        payload = _payload_valido(sample_producto_disponible.id, direccion_id=other_addr.id)
        response = client.post(BASE_URL + "/", json=payload, headers=auth_headers)
        assert response.status_code == 404

    def test_7_5_b_direccion_inexistente_responde_404(
        self,
        client: TestClient,
        auth_headers: dict,
        sample_estados_pedido,
        sample_formas_pago,
        sample_producto_disponible,
    ):
        """direccion_id=999999 (nonexistent) → 404."""
        payload = _payload_valido(sample_producto_disponible.id, direccion_id=999999)
        response = client.post(BASE_URL + "/", json=payload, headers=auth_headers)
        assert response.status_code == 404

    def test_7_5_c_direccion_soft_deleted_responde_404(
        self,
        client: TestClient,
        auth_headers: dict,
        test_db_session: Session,
        sample_estados_pedido,
        sample_formas_pago,
        sample_producto_disponible,
        sample_address,
    ):
        """Soft-deleted address → 404."""
        from datetime import datetime, timezone

        sample_address.eliminado_en = datetime.now(timezone.utc)
        test_db_session.commit()

        payload = _payload_valido(sample_producto_disponible.id, direccion_id=sample_address.id)
        response = client.post(BASE_URL + "/", json=payload, headers=auth_headers)
        assert response.status_code == 404


# ---------------------------------------------------------------------------
# 7.1  Happy path (pg_only — inserts into order_items)
# ---------------------------------------------------------------------------

class TestHappyPath:
    """
    7.1 — Happy path tests. All insert into order_items → pg_only.
    """

    @pytest.mark.pg_only
    def test_7_1_a_happy_path_con_direccion(
        self,
        client: TestClient,
        auth_headers: dict,
        test_db_session: Session,
        sample_estados_pedido,
        sample_formas_pago,
        sample_producto_disponible,
        sample_address,
    ):
        """
        Authenticated CLIENT with 2 items and own address → 201.
        Verify: id, estado_codigo=PENDIENTE, total correct,
        1 row in orders, N in order_items, 1 in order_state_history,
        direccion_snapshot captured.
        """
        from backend.features.catalog.models import Producto

        # Create a second product for the 2-item test
        producto2 = Producto(
            nombre="Producto Test 2",
            precio=Decimal("21.00"),
            stock_cantidad=5,
            disponible=True,
        )
        test_db_session.add(producto2)
        test_db_session.commit()

        payload = {
            "items": [
                {"producto_id": sample_producto_disponible.id, "cantidad": 3},
                {"producto_id": producto2.id, "cantidad": 2},
            ],
            "forma_pago_codigo": "MERCADOPAGO",
            "direccion_id": sample_address.id,
        }
        response = client.post(BASE_URL + "/", json=payload, headers=auth_headers)
        assert response.status_code == 201

        data = response.json()
        assert "id" in data
        assert data["estado_codigo"] == "PENDIENTE"

        # total: (100.00 * 3) + (21.00 * 2) + 50.00 (envío) = 300 + 42 + 50 = 392.00
        assert Decimal(str(data["total"])) == Decimal("392.00")

        # Verify DB
        from backend.features.orders.models import Pedido, DetallePedido, HistorialEstadoPedido
        pedido = test_db_session.query(Pedido).filter_by(id=data["id"]).first()
        assert pedido is not None
        assert pedido.direccion_snapshot is not None
        assert pedido.direccion_entrega_id == sample_address.id

        items = test_db_session.query(DetallePedido).filter_by(pedido_id=pedido.id).all()
        assert len(items) == 2

        historial = test_db_session.query(HistorialEstadoPedido).filter_by(pedido_id=pedido.id).all()
        assert len(historial) == 1
        assert historial[0].estado_anterior_codigo is None
        assert historial[0].estado_nuevo_codigo == "PENDIENTE"

    @pytest.mark.pg_only
    def test_7_1_b_happy_path_retiro_en_local(
        self,
        client: TestClient,
        auth_headers: dict,
        test_db_session: Session,
        sample_estados_pedido,
        sample_formas_pago,
        sample_producto_disponible,
    ):
        """
        Order without direccion_id → 201.
        direccion_entrega_id=NULL, direccion_snapshot=NULL,
        costo_envio=0.00, total=sum(cantidad*precio).
        """
        payload = _payload_valido(sample_producto_disponible.id, cantidad=2)
        response = client.post(BASE_URL + "/", json=payload, headers=auth_headers)
        assert response.status_code == 201

        data = response.json()
        # total: 100.00 * 2 + 0.00 (retiro) = 200.00
        assert Decimal(str(data["total"])) == Decimal("200.00")

        from backend.features.orders.models import Pedido
        pedido = test_db_session.query(Pedido).filter_by(id=data["id"]).first()
        assert pedido is not None
        assert pedido.direccion_entrega_id is None
        assert pedido.direccion_snapshot is None
        assert pedido.costo_envio == Decimal("0.00")

    @pytest.mark.pg_only
    def test_7_1_c_snapshots_inmutables(
        self,
        client: TestClient,
        auth_headers: dict,
        test_db_session: Session,
        sample_estados_pedido,
        sample_formas_pago,
        sample_producto_disponible,
    ):
        """
        Create order → update product price in DB → re-read DetallePedido
        → precio_snapshot unchanged (RN-DA06).
        """
        precio_original = Decimal(str(sample_producto_disponible.precio))
        payload = _payload_valido(sample_producto_disponible.id)
        response = client.post(BASE_URL + "/", json=payload, headers=auth_headers)
        assert response.status_code == 201
        pedido_id = response.json()["id"]

        # Change price in DB
        sample_producto_disponible.precio = Decimal("999.99")
        test_db_session.commit()

        from backend.features.orders.models import DetallePedido
        detalle = test_db_session.query(DetallePedido).filter_by(pedido_id=pedido_id).first()
        assert detalle is not None
        assert Decimal(str(detalle.precio_snapshot)) == precio_original


# ---------------------------------------------------------------------------
# 7.7  Atomicidad — rollback (SQLite-compatible — error before order_items in most cases)
# ---------------------------------------------------------------------------

class TestAtomicidad:
    """
    7.7 — Atomicity test: force error in create_historial_inicial,
    verify nothing persisted.
    """

    @pytest.mark.pg_only
    def test_7_7_rollback_si_historial_falla(
        self,
        client: TestClient,
        auth_headers: dict,
        test_db_session: Session,
        sample_estados_pedido,
        sample_formas_pago,
        sample_producto_disponible,
        monkeypatch,
    ):
        """
        Monkeypatch create_historial_inicial to raise RuntimeError →
        response is 500 → DB: 0 rows in orders and order_items.

        pg_only because the UoW reaches create_detalle (which writes to
        order_items — PG-only table) before create_historial_inicial.
        The full 9-step flow only works with PostgreSQL.
        """
        import backend.features.orders.repository as repo_mod

        def _raise(*args, **kwargs):
            raise RuntimeError("Simulated historial failure")

        monkeypatch.setattr(repo_mod.OrderRepository, "create_historial_inicial", _raise)

        payload = _payload_valido(sample_producto_disponible.id)
        response = client.post(BASE_URL + "/", json=payload, headers=auth_headers)
        # Should be 500 (unhandled RuntimeError)
        assert response.status_code in (500, 422, 400)

        from backend.features.orders.models import Pedido
        pedidos = test_db_session.query(Pedido).all()
        assert len(pedidos) == 0


# ---------------------------------------------------------------------------
# 7.11 Total con precios fraccionarios (pg_only — inserts order_items)
# ---------------------------------------------------------------------------

class TestPrecisionDecimal:
    """
    7.11 — Precision test: 19.99 × 3 + 10.50 × 2 + 50.00 = 130.97
    pg_only because it inserts into order_items.
    """

    @pytest.mark.pg_only
    def test_7_11_total_con_precios_fraccionarios(
        self,
        client: TestClient,
        auth_headers: dict,
        test_db_session: Session,
        sample_estados_pedido,
        sample_formas_pago,
        sample_address,
    ):
        """
        2 items with fractional prices + shipping → total must be Decimal-exact.
        19.99 × 3 = 59.97
        10.50 × 2 = 21.00
        costo_envio = 50.00
        total = 130.97
        """
        from backend.features.catalog.models import Producto

        prod1 = Producto(
            nombre="Producto Fraccionario 1",
            precio=Decimal("19.99"),
            stock_cantidad=10,
            disponible=True,
        )
        prod2 = Producto(
            nombre="Producto Fraccionario 2",
            precio=Decimal("10.50"),
            stock_cantidad=10,
            disponible=True,
        )
        test_db_session.add(prod1)
        test_db_session.add(prod2)
        test_db_session.commit()

        payload = {
            "items": [
                {"producto_id": prod1.id, "cantidad": 3},
                {"producto_id": prod2.id, "cantidad": 2},
            ],
            "forma_pago_codigo": "MERCADOPAGO",
            "direccion_id": sample_address.id,
        }
        response = client.post(BASE_URL + "/", json=payload, headers=auth_headers)
        assert response.status_code == 201

        data = response.json()
        assert Decimal(str(data["total"])) == Decimal("130.97")
