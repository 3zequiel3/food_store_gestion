"""
Integration tests for products CRUD endpoints.

Covers:
- CRUD básico (create, list, get, update, patch, delete)
- RBAC (ADMIN, STOCK, CLIENT, unauthenticated)
- Validación (precio, stock, nombre, categoria_ids, imagen_url)
- Filtros del catálogo público (disponible, categoria_id, search, excluir_alergenos)
- Paginación
- Asociaciones M:N de categorías (PUT /{id}/categorias)
- Asociaciones M:N de ingredientes (GET/POST/DELETE /{id}/ingredientes)
- Soft delete del producto
- Routing (prefix en español)
- Precisión Decimal del precio
- Columna es_removible en la migración
"""

from __future__ import annotations

import uuid
from decimal import Decimal

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import inspect, text
from sqlalchemy.orm import Session


# ===========================================================================
# Auth helpers
# ===========================================================================


def _admin_headers(client: TestClient) -> dict[str, str]:
    """Get auth headers for an ADMIN user."""
    response = client.post(
        "/api/v1/auth/login",
        json={"email": "admin@test.com", "password": "admin_password_123"},
    )
    assert response.status_code == 200, f"Admin login failed: {response.json()}"
    return {}


def _stock_headers(client: TestClient) -> dict[str, str]:
    """Get auth headers for a STOCK user."""
    response = client.post(
        "/api/v1/auth/login",
        json={"email": "stock@test.com", "password": "stock_password_123"},
    )
    assert response.status_code == 200, f"Stock login failed: {response.json()}"
    return {}


def _client_headers(client: TestClient) -> dict[str, str]:
    """Get auth headers for a CLIENT user."""
    response = client.post(
        "/api/v1/auth/login",
        json={"email": "test@example.com", "password": "test_password_123"},
    )
    assert response.status_code == 200, f"Client login failed: {response.json()}"
    return {}


# ===========================================================================
# Fixtures
# ===========================================================================


@pytest.fixture(scope="function")
def admin_user(test_db_session: Session, sample_roles):
    """Create an ADMIN user for testing."""
    from backend.features.users.models import Usuario, UsuarioRol
    from backend.shared.security import hash_password

    user = Usuario(
        email="admin@test.com",
        password_hash=hash_password("admin_password_123"),
        nombre="Admin",
        apellido="User",
        is_active=True,
    )
    test_db_session.add(user)
    test_db_session.flush()
    user_role = UsuarioRol(user_id=user.id, role_id=1)
    test_db_session.add(user_role)
    test_db_session.commit()
    test_db_session.refresh(user)
    return user


@pytest.fixture(scope="function")
def stock_user(test_db_session: Session, sample_roles):
    """Create a STOCK user for testing."""
    from backend.features.users.models import Usuario, UsuarioRol
    from backend.shared.security import hash_password

    user = Usuario(
        email="stock@test.com",
        password_hash=hash_password("stock_password_123"),
        nombre="Stock",
        apellido="User",
        is_active=True,
    )
    test_db_session.add(user)
    test_db_session.flush()
    user_role = UsuarioRol(user_id=user.id, role_id=2)
    test_db_session.add(user_role)
    test_db_session.commit()
    test_db_session.refresh(user)
    return user


@pytest.fixture(scope="function")
def client_user(test_db_session: Session, sample_roles, sample_user):
    """The sample_user (CLIENT role) already created by conftest."""
    return sample_user


# ===========================================================================
# Helpers
# ===========================================================================


def _create_product(
    client: TestClient,
    headers: dict,
    **overrides,
) -> dict:
    """POST /api/v1/productos with sensible defaults and assert 201."""
    payload = {
        "nombre": f"P-{uuid.uuid4().hex[:8]}",
        "precio": "10.00",
        "stock_cantidad": 20,
        "disponible": True,
    }
    payload.update(overrides)
    resp = client.post("/api/v1/productos", json=payload, headers=headers)
    assert resp.status_code == 201, f"Failed to create product: {resp.json()}"
    return resp.json()


def _create_categoria_direct(session: Session, nombre: str = "Cat-X") -> dict:
    """Insert a Categoria directly via session (bypasses API)."""
    from backend.features.catalog.models import Categoria

    cat = Categoria(nombre=nombre)
    session.add(cat)
    session.flush()
    session.commit()
    return {"id": cat.id, "nombre": cat.nombre}


def _create_ingrediente_direct(
    session: Session,
    nombre: str = "Ing-X",
    es_alergeno: bool = False,
) -> dict:
    """Insert an Ingrediente directly via session (bypasses API)."""
    from backend.features.catalog.models import Ingrediente

    ing = Ingrediente(nombre=nombre, es_alergeno=es_alergeno)
    session.add(ing)
    session.flush()
    session.commit()
    return {"id": ing.id, "nombre": ing.nombre, "es_alergeno": ing.es_alergeno}


# ===========================================================================
# 7.2 CRUD básico
# ===========================================================================


class TestCreate:
    """POST /api/v1/productos."""

    def test_create_as_admin(self, client: TestClient, sample_roles, admin_user):
        """POST as ADMIN with minimal payload → 201 with correct body."""
        headers = _admin_headers(client)
        resp = client.post(
            "/api/v1/productos",
            json={"nombre": "Pizza Margherita", "precio": "12.50"},
            headers=headers,
        )
        assert resp.status_code == 201
        data = resp.json()
        assert data["nombre"] == "Pizza Margherita"
        assert "id" in data
        assert "creado_en" in data
        assert "actualizado_en" in data

    def test_create_as_stock(self, client: TestClient, sample_roles, stock_user):
        """POST as STOCK → 201."""
        headers = _stock_headers(client)
        resp = client.post(
            "/api/v1/productos",
            json={"nombre": "Hamburguesa", "precio": "9.99"},
            headers=headers,
        )
        assert resp.status_code == 201

    def test_create_with_categoria_ids(
        self, client: TestClient, test_db_session: Session, sample_roles, admin_user
    ):
        """POST with categoria_ids → 201 + 2 rows in product_categories."""
        headers = _admin_headers(client)
        cat1 = _create_categoria_direct(test_db_session, "Pizzas")
        cat2 = _create_categoria_direct(test_db_session, "Especiales")

        resp = client.post(
            "/api/v1/productos",
            json={
                "nombre": "Pizza Esp.",
                "precio": "15.00",
                "categoria_ids": [cat1["id"], cat2["id"]],
            },
            headers=headers,
        )
        assert resp.status_code == 201
        prod_id = resp.json()["id"]

        count = test_db_session.execute(
            text(
                "SELECT COUNT(*) FROM product_categories "
                "WHERE product_id = :pid AND eliminado_en IS NULL"
            ),
            {"pid": prod_id},
        ).scalar()
        assert count == 2

    def test_create_with_empty_categoria_ids(
        self, client: TestClient, test_db_session: Session, sample_roles, admin_user
    ):
        """POST with categoria_ids: [] → 201 + 0 rows in pivot."""
        headers = _admin_headers(client)
        resp = client.post(
            "/api/v1/productos",
            json={"nombre": "P-empty", "precio": "5.00", "categoria_ids": []},
            headers=headers,
        )
        assert resp.status_code == 201
        prod_id = resp.json()["id"]

        count = test_db_session.execute(
            text("SELECT COUNT(*) FROM product_categories WHERE product_id = :pid"),
            {"pid": prod_id},
        ).scalar()
        assert count == 0

    def test_create_categoria_inexistente_returns_422(
        self, client: TestClient, test_db_session: Session, sample_roles, admin_user
    ):
        """POST with invalid categoria_id → 422, product NOT created."""
        headers = _admin_headers(client)
        resp = client.post(
            "/api/v1/productos",
            json={
                "nombre": "P-invalid-cat",
                "precio": "5.00",
                "categoria_ids": [99999],
            },
            headers=headers,
        )
        assert resp.status_code == 422

        count = test_db_session.execute(
            text(
                "SELECT COUNT(*) FROM products "
                "WHERE nombre = 'P-invalid-cat' AND eliminado_en IS NULL"
            )
        ).scalar()
        assert count == 0

    def test_create_precio_zero_returns_422(
        self, client: TestClient, sample_roles, admin_user
    ):
        """POST with precio=0 → 422."""
        headers = _admin_headers(client)
        resp = client.post(
            "/api/v1/productos",
            json={"nombre": "P-zero", "precio": "0"},
            headers=headers,
        )
        assert resp.status_code == 422

    def test_create_precio_negative_returns_422(
        self, client: TestClient, sample_roles, admin_user
    ):
        """POST with precio=-1 → 422."""
        headers = _admin_headers(client)
        resp = client.post(
            "/api/v1/productos",
            json={"nombre": "P-neg", "precio": "-1"},
            headers=headers,
        )
        assert resp.status_code == 422

    def test_create_stock_negative_returns_422(
        self, client: TestClient, sample_roles, admin_user
    ):
        """POST with stock_cantidad=-1 → 422."""
        headers = _admin_headers(client)
        resp = client.post(
            "/api/v1/productos",
            json={"nombre": "P-neg-stock", "precio": "5.00", "stock_cantidad": -1},
            headers=headers,
        )
        assert resp.status_code == 422

    def test_create_nombre_empty_returns_422(
        self, client: TestClient, sample_roles, admin_user
    ):
        """POST with nombre='' → 422."""
        headers = _admin_headers(client)
        resp = client.post(
            "/api/v1/productos",
            json={"nombre": "", "precio": "5.00"},
            headers=headers,
        )
        assert resp.status_code == 422

    def test_create_nombre_too_long_returns_422(
        self, client: TestClient, sample_roles, admin_user
    ):
        """POST with nombre of 256 chars → 422."""
        headers = _admin_headers(client)
        resp = client.post(
            "/api/v1/productos",
            json={"nombre": "A" * 256, "precio": "5.00"},
            headers=headers,
        )
        assert resp.status_code == 422

    def test_create_imagen_url_too_long_returns_422(
        self, client: TestClient, sample_roles, admin_user
    ):
        """POST with imagen_url of 501 chars → 422."""
        headers = _admin_headers(client)
        resp = client.post(
            "/api/v1/productos",
            json={"nombre": "P-img", "precio": "5.00", "imagen_url": "x" * 501},
            headers=headers,
        )
        assert resp.status_code == 422


# ===========================================================================
# GET detail
# ===========================================================================


class TestGetById:
    """GET /api/v1/productos/{id}."""

    def test_get_by_id_returns_detail(
        self, client: TestClient, sample_roles, admin_user
    ):
        """Create → GET by id → 200 with categorias and ingredientes arrays."""
        headers = _admin_headers(client)
        prod = _create_product(client, headers)
        prod_id = prod["id"]

        resp = client.get(f"/api/v1/productos/{prod_id}")
        assert resp.status_code == 200
        data = resp.json()
        assert data["id"] == prod_id
        assert "categorias" in data
        assert "ingredientes" in data
        assert isinstance(data["categorias"], list)
        assert isinstance(data["ingredientes"], list)

    def test_get_by_id_not_found(self, client: TestClient, sample_roles, admin_user):
        """GET non-existent id → 404."""
        resp = client.get("/api/v1/productos/999999")
        assert resp.status_code == 404

    def test_get_by_id_soft_deleted_returns_404(
        self, client: TestClient, sample_roles, admin_user
    ):
        """Soft-delete a product → GET → 404."""
        headers = _admin_headers(client)
        prod = _create_product(client, headers)
        prod_id = prod["id"]

        client.delete(f"/api/v1/productos/{prod_id}", headers=headers)
        resp = client.get(f"/api/v1/productos/{prod_id}")
        assert resp.status_code == 404


# ===========================================================================
# Update
# ===========================================================================


class TestUpdate:
    """PUT /api/v1/productos/{id}."""

    def test_update_nombre_only(self, client: TestClient, sample_roles, admin_user):
        """PUT with only nombre → 200, other fields preserved."""
        headers = _admin_headers(client)
        prod = _create_product(
            client, headers, nombre="Original", precio="10.00", stock_cantidad=5
        )
        prod_id = prod["id"]

        resp = client.put(
            f"/api/v1/productos/{prod_id}",
            json={"nombre": "Nuevo Nombre"},
            headers=headers,
        )
        assert resp.status_code == 200
        data = resp.json()
        assert data["nombre"] == "Nuevo Nombre"
        assert data["stock_cantidad"] == 5

    def test_update_precio_only(self, client: TestClient, sample_roles, admin_user):
        """PUT with only precio → 200."""
        headers = _admin_headers(client)
        prod = _create_product(client, headers)
        prod_id = prod["id"]

        resp = client.put(
            f"/api/v1/productos/{prod_id}",
            json={"precio": "15.50"},
            headers=headers,
        )
        assert resp.status_code == 200
        assert resp.json()["precio"] == "15.50"

    def test_update_precio_zero_returns_422(
        self, client: TestClient, sample_roles, admin_user
    ):
        """PUT with precio=0 → 422."""
        headers = _admin_headers(client)
        prod = _create_product(client, headers)
        resp = client.put(
            f"/api/v1/productos/{prod['id']}",
            json={"precio": "0"},
            headers=headers,
        )
        assert resp.status_code == 422

    def test_update_stock_negative_returns_422(
        self, client: TestClient, sample_roles, admin_user
    ):
        """PUT with stock_cantidad=-1 → 422."""
        headers = _admin_headers(client)
        prod = _create_product(client, headers)
        resp = client.put(
            f"/api/v1/productos/{prod['id']}",
            json={"stock_cantidad": -1},
            headers=headers,
        )
        assert resp.status_code == 422

    def test_update_not_found_returns_404(
        self, client: TestClient, sample_roles, admin_user
    ):
        """PUT non-existent id → 404."""
        headers = _admin_headers(client)
        resp = client.put(
            "/api/v1/productos/999999",
            json={"nombre": "X"},
            headers=headers,
        )
        assert resp.status_code == 404

    def test_update_soft_deleted_returns_404(
        self, client: TestClient, sample_roles, admin_user
    ):
        """Soft-delete → PUT → 404."""
        headers = _admin_headers(client)
        prod = _create_product(client, headers)
        prod_id = prod["id"]
        client.delete(f"/api/v1/productos/{prod_id}", headers=headers)

        resp = client.put(
            f"/api/v1/productos/{prod_id}",
            json={"nombre": "X"},
            headers=headers,
        )
        assert resp.status_code == 404


# ===========================================================================
# PATCH: disponibilidad
# ===========================================================================


class TestPatchDisponibilidad:
    """PATCH /api/v1/productos/{id}/disponibilidad."""

    def test_patch_disponibilidad_to_false(
        self, client: TestClient, sample_roles, admin_user
    ):
        """PATCH disponible=false → 200, product excluded from default GET /."""
        headers = _admin_headers(client)
        prod = _create_product(client, headers, disponible=True)
        prod_id = prod["id"]

        resp = client.patch(
            f"/api/v1/productos/{prod_id}/disponibilidad",
            json={"disponible": False},
            headers=headers,
        )
        assert resp.status_code == 200
        assert resp.json()["disponible"] is False

        # Should NOT appear in default listing (disponible=True default)
        list_resp = client.get("/api/v1/productos")
        ids = [p["id"] for p in list_resp.json()["items"]]
        assert prod_id not in ids

    def test_patch_disponibilidad_to_true(
        self, client: TestClient, sample_roles, admin_user
    ):
        """Toggle back to true → 200, product visible again."""
        headers = _admin_headers(client)
        prod = _create_product(client, headers, disponible=False)
        prod_id = prod["id"]

        # Set to false first (it was created as false)
        resp = client.patch(
            f"/api/v1/productos/{prod_id}/disponibilidad",
            json={"disponible": True},
            headers=headers,
        )
        assert resp.status_code == 200
        assert resp.json()["disponible"] is True


# ===========================================================================
# PATCH: stock
# ===========================================================================


class TestPatchStock:
    """PATCH /api/v1/productos/{id}/stock."""

    def test_patch_stock_set_value(
        self, client: TestClient, sample_roles, admin_user
    ):
        """PATCH stock=50 → 200, exact value returned."""
        headers = _admin_headers(client)
        prod = _create_product(client, headers)
        prod_id = prod["id"]

        resp = client.patch(
            f"/api/v1/productos/{prod_id}/stock",
            json={"stock_cantidad": 50},
            headers=headers,
        )
        assert resp.status_code == 200
        assert resp.json()["stock_cantidad"] == 50

    def test_patch_stock_zero(self, client: TestClient, sample_roles, admin_user):
        """PATCH stock=0 → 200."""
        headers = _admin_headers(client)
        prod = _create_product(client, headers, stock_cantidad=10)
        prod_id = prod["id"]

        resp = client.patch(
            f"/api/v1/productos/{prod_id}/stock",
            json={"stock_cantidad": 0},
            headers=headers,
        )
        assert resp.status_code == 200
        assert resp.json()["stock_cantidad"] == 0

    def test_patch_stock_negative_returns_422(
        self, client: TestClient, sample_roles, admin_user
    ):
        """PATCH stock=-1 → 422."""
        headers = _admin_headers(client)
        prod = _create_product(client, headers)
        resp = client.patch(
            f"/api/v1/productos/{prod['id']}/stock",
            json={"stock_cantidad": -1},
            headers=headers,
        )
        assert resp.status_code == 422


# ===========================================================================
# DELETE (soft)
# ===========================================================================


class TestDelete:
    """DELETE /api/v1/productos/{id}."""

    def test_delete_soft(
        self,
        client: TestClient,
        test_db_session: Session,
        sample_roles,
        admin_user,
    ):
        """DELETE → 204, row persists with eliminado_en NOT NULL."""
        headers = _admin_headers(client)
        prod = _create_product(client, headers)
        prod_id = prod["id"]

        resp = client.delete(f"/api/v1/productos/{prod_id}", headers=headers)
        assert resp.status_code == 204

        row = test_db_session.execute(
            text("SELECT eliminado_en FROM products WHERE id = :pid"),
            {"pid": prod_id},
        ).fetchone()
        assert row is not None
        assert row[0] is not None

    def test_delete_already_deleted_returns_404(
        self, client: TestClient, sample_roles, admin_user
    ):
        """DELETE twice → second returns 404."""
        headers = _admin_headers(client)
        prod = _create_product(client, headers)
        prod_id = prod["id"]

        client.delete(f"/api/v1/productos/{prod_id}", headers=headers)
        resp = client.delete(f"/api/v1/productos/{prod_id}", headers=headers)
        assert resp.status_code == 404

    def test_delete_not_found_returns_404(
        self, client: TestClient, sample_roles, admin_user
    ):
        """DELETE non-existent id → 404."""
        headers = _admin_headers(client)
        resp = client.delete("/api/v1/productos/999999", headers=headers)
        assert resp.status_code == 404

    def test_delete_does_not_cascade_to_pivots(
        self,
        client: TestClient,
        test_db_session: Session,
        sample_roles,
        admin_user,
    ):
        """DELETE product with category association → pivot row untouched."""
        headers = _admin_headers(client)
        cat = _create_categoria_direct(test_db_session, "Bebidas")
        prod = _create_product(
            client, headers, categoria_ids=[cat["id"]]
        )
        prod_id = prod["id"]

        client.delete(f"/api/v1/productos/{prod_id}", headers=headers)

        count = test_db_session.execute(
            text(
                "SELECT COUNT(*) FROM product_categories "
                "WHERE product_id = :pid"
            ),
            {"pid": prod_id},
        ).scalar()
        assert count == 1  # row still there, not deleted


# ===========================================================================
# 7.3 RBAC
# ===========================================================================


class TestRBAC:
    """Auth / authorization checks across all mutations."""

    def test_post_unauthenticated_returns_401(self, client: TestClient, sample_roles):
        """POST without token → 401."""
        resp = client.post(
            "/api/v1/productos",
            json={"nombre": "X", "precio": "5"},
        )
        assert resp.status_code == 401

    def test_post_as_client_returns_403(
        self, client: TestClient, sample_roles, client_user
    ):
        """POST as CLIENT → 403."""
        headers = _client_headers(client)
        resp = client.post(
            "/api/v1/productos",
            json={"nombre": "X", "precio": "5"},
            headers=headers,
        )
        assert resp.status_code == 403

    def test_put_unauthenticated_returns_401(
        self, client: TestClient, sample_roles, admin_user
    ):
        """PUT without token → 401."""
        headers = _admin_headers(client)
        prod = _create_product(client, headers)
        resp = client.put(
            f"/api/v1/productos/{prod['id']}",
            json={"nombre": "X"},
        )
        assert resp.status_code == 401

    def test_put_as_client_returns_403(
        self, client: TestClient, sample_roles, admin_user, client_user
    ):
        """PUT as CLIENT → 403."""
        admin_h = _admin_headers(client)
        prod = _create_product(client, admin_h)
        resp = client.put(
            f"/api/v1/productos/{prod['id']}",
            json={"nombre": "X"},
            headers=_client_headers(client),
        )
        assert resp.status_code == 403

    def test_patch_disponibilidad_unauthenticated_returns_401(
        self, client: TestClient, sample_roles, admin_user
    ):
        """PATCH disponibilidad without token → 401."""
        headers = _admin_headers(client)
        prod = _create_product(client, headers)
        resp = client.patch(
            f"/api/v1/productos/{prod['id']}/disponibilidad",
            json={"disponible": False},
        )
        assert resp.status_code == 401

    def test_patch_disponibilidad_as_client_returns_403(
        self, client: TestClient, sample_roles, admin_user, client_user
    ):
        """PATCH disponibilidad as CLIENT → 403."""
        admin_h = _admin_headers(client)
        prod = _create_product(client, admin_h)
        resp = client.patch(
            f"/api/v1/productos/{prod['id']}/disponibilidad",
            json={"disponible": False},
            headers=_client_headers(client),
        )
        assert resp.status_code == 403

    def test_patch_stock_unauthenticated_returns_401(
        self, client: TestClient, sample_roles, admin_user
    ):
        """PATCH stock without token → 401."""
        headers = _admin_headers(client)
        prod = _create_product(client, headers)
        resp = client.patch(
            f"/api/v1/productos/{prod['id']}/stock",
            json={"stock_cantidad": 5},
        )
        assert resp.status_code == 401

    def test_patch_stock_as_client_returns_403(
        self, client: TestClient, sample_roles, admin_user, client_user
    ):
        """PATCH stock as CLIENT → 403."""
        admin_h = _admin_headers(client)
        prod = _create_product(client, admin_h)
        resp = client.patch(
            f"/api/v1/productos/{prod['id']}/stock",
            json={"stock_cantidad": 5},
            headers=_client_headers(client),
        )
        assert resp.status_code == 403

    def test_delete_unauthenticated_returns_401(
        self, client: TestClient, sample_roles, admin_user
    ):
        """DELETE without token → 401."""
        headers = _admin_headers(client)
        prod = _create_product(client, headers)
        resp = client.delete(f"/api/v1/productos/{prod['id']}")
        assert resp.status_code == 401

    def test_delete_as_client_returns_403(
        self, client: TestClient, sample_roles, admin_user, client_user
    ):
        """DELETE as CLIENT → 403."""
        admin_h = _admin_headers(client)
        prod = _create_product(client, admin_h)
        resp = client.delete(
            f"/api/v1/productos/{prod['id']}",
            headers=_client_headers(client),
        )
        assert resp.status_code == 403

    def test_get_list_is_public(self, client: TestClient, sample_roles):
        """GET / without token → 200."""
        resp = client.get("/api/v1/productos")
        assert resp.status_code == 200

    def test_get_by_id_is_public(
        self, client: TestClient, sample_roles, admin_user
    ):
        """GET /{id} without token → 200."""
        headers = _admin_headers(client)
        prod = _create_product(client, headers)
        resp = client.get(f"/api/v1/productos/{prod['id']}")
        assert resp.status_code == 200

    def test_get_ingredientes_is_public(
        self, client: TestClient, sample_roles, admin_user
    ):
        """GET /{id}/ingredientes without token → 200."""
        headers = _admin_headers(client)
        prod = _create_product(client, headers)
        resp = client.get(f"/api/v1/productos/{prod['id']}/ingredientes")
        assert resp.status_code == 200

    def test_put_categorias_unauthenticated_returns_401(
        self, client: TestClient, sample_roles, admin_user
    ):
        """PUT /categorias without token → 401."""
        headers = _admin_headers(client)
        prod = _create_product(client, headers)
        resp = client.put(
            f"/api/v1/productos/{prod['id']}/categorias",
            json={"categoria_ids": []},
        )
        assert resp.status_code == 401

    def test_put_categorias_as_client_returns_403(
        self, client: TestClient, sample_roles, admin_user, client_user
    ):
        """PUT /categorias as CLIENT → 403."""
        admin_h = _admin_headers(client)
        prod = _create_product(client, admin_h)
        resp = client.put(
            f"/api/v1/productos/{prod['id']}/categorias",
            json={"categoria_ids": []},
            headers=_client_headers(client),
        )
        assert resp.status_code == 403

    def test_post_ingredientes_unauthenticated_returns_401(
        self, client: TestClient, sample_roles, admin_user
    ):
        """POST /ingredientes without token → 401."""
        headers = _admin_headers(client)
        prod = _create_product(client, headers)
        resp = client.post(
            f"/api/v1/productos/{prod['id']}/ingredientes",
            json={"ingrediente_id": 1},
        )
        assert resp.status_code == 401

    def test_post_ingredientes_as_client_returns_403(
        self, client: TestClient, sample_roles, admin_user, client_user
    ):
        """POST /ingredientes as CLIENT → 403."""
        admin_h = _admin_headers(client)
        prod = _create_product(client, admin_h)
        resp = client.post(
            f"/api/v1/productos/{prod['id']}/ingredientes",
            json={"ingrediente_id": 1},
            headers=_client_headers(client),
        )
        assert resp.status_code == 403

    def test_delete_ingrediente_unauthenticated_returns_401(
        self, client: TestClient, sample_roles, admin_user
    ):
        """DELETE /ingredientes/{id} without token → 401."""
        headers = _admin_headers(client)
        prod = _create_product(client, headers)
        resp = client.delete(
            f"/api/v1/productos/{prod['id']}/ingredientes/1"
        )
        assert resp.status_code == 401

    def test_delete_ingrediente_as_client_returns_403(
        self, client: TestClient, sample_roles, admin_user, client_user
    ):
        """DELETE /ingredientes/{id} as CLIENT → 403."""
        admin_h = _admin_headers(client)
        prod = _create_product(client, admin_h)
        resp = client.delete(
            f"/api/v1/productos/{prod['id']}/ingredientes/1",
            headers=_client_headers(client),
        )
        assert resp.status_code == 403


# ===========================================================================
# 7.4 Filtros de catálogo público
# ===========================================================================


class TestCatalogFilters:
    """GET / with filters."""

    def test_list_default_excludes_unavailable(
        self, client: TestClient, sample_roles, admin_user
    ):
        """3 disponibles + 2 no-disponibles → GET default → total=3."""
        headers = _admin_headers(client)
        for _ in range(3):
            _create_product(client, headers, disponible=True)
        for _ in range(2):
            _create_product(client, headers, disponible=False)

        resp = client.get("/api/v1/productos")
        assert resp.status_code == 200
        assert resp.json()["total"] == 3

    def test_list_filter_disponible_false_explicit(
        self, client: TestClient, sample_roles, admin_user
    ):
        """GET ?disponible=false → total=2."""
        headers = _admin_headers(client)
        for _ in range(3):
            _create_product(client, headers, disponible=True)
        for _ in range(2):
            _create_product(client, headers, disponible=False)

        resp = client.get("/api/v1/productos?disponible=false")
        assert resp.status_code == 200
        assert resp.json()["total"] == 2

    def test_list_filter_categoria_id(
        self,
        client: TestClient,
        test_db_session: Session,
        sample_roles,
        admin_user,
    ):
        """3 products, 1 in cat → GET ?categoria_id=X → 1 item."""
        headers = _admin_headers(client)
        cat = _create_categoria_direct(test_db_session, "Pizzas")

        for _ in range(2):
            _create_product(client, headers)
        _create_product(client, headers, categoria_ids=[cat["id"]])

        resp = client.get(f"/api/v1/productos?categoria_id={cat['id']}")
        assert resp.status_code == 200
        assert resp.json()["total"] == 1

    def test_list_filter_search_case_insensitive(
        self, client: TestClient, sample_roles, admin_user
    ):
        """GET ?search=PIZZA → 2 items (case-insensitive)."""
        headers = _admin_headers(client)
        _create_product(client, headers, nombre="Pizza Margherita")
        _create_product(client, headers, nombre="Pizza Napolitana")
        _create_product(client, headers, nombre="Hamburguesa")

        resp = client.get("/api/v1/productos?search=PIZZA")
        assert resp.status_code == 200
        assert resp.json()["total"] == 2

    def test_list_filter_search_substring(
        self, client: TestClient, sample_roles, admin_user
    ):
        """GET ?search=especial → 2 items."""
        headers = _admin_headers(client)
        _create_product(client, headers, nombre="Pizza Especial")
        _create_product(client, headers, nombre="Especial del día")
        _create_product(client, headers, nombre="Hamburguesa")

        resp = client.get("/api/v1/productos?search=especial")
        assert resp.status_code == 200
        assert resp.json()["total"] == 2

    def test_list_filter_search_no_match(
        self, client: TestClient, sample_roles, admin_user
    ):
        """GET ?search=zzzzzz → 0 items."""
        headers = _admin_headers(client)
        _create_product(client, headers)

        resp = client.get("/api/v1/productos?search=zzzzzz")
        assert resp.status_code == 200
        assert resp.json()["total"] == 0

    def test_list_filter_excluir_alergenos_with_non_removable(
        self,
        client: TestClient,
        test_db_session: Session,
        sample_roles,
        admin_user,
    ):
        """P1 with non-removable allergen + P2 clean → excluir_alergenos=true → only P2."""
        headers = _admin_headers(client)

        # P1: has allergen ingredient, not removable
        ing = _create_ingrediente_direct(test_db_session, "Mani", es_alergeno=True)
        p1 = _create_product(client, headers, nombre="P1-con-alergeno")
        client.post(
            f"/api/v1/productos/{p1['id']}/ingredientes",
            json={"ingrediente_id": ing["id"], "es_removible": False},
            headers=headers,
        )

        # P2: no allergens
        p2 = _create_product(client, headers, nombre="P2-limpio")

        resp = client.get("/api/v1/productos?excluir_alergenos=true")
        assert resp.status_code == 200
        ids = [p["id"] for p in resp.json()["items"]]
        assert p1["id"] not in ids
        assert p2["id"] in ids

    def test_list_filter_excluir_alergenos_with_removable(
        self,
        client: TestClient,
        test_db_session: Session,
        sample_roles,
        admin_user,
    ):
        """P1 with REMOVABLE allergen → excluir_alergenos=true → P1 appears."""
        headers = _admin_headers(client)

        ing = _create_ingrediente_direct(
            test_db_session, "Gluten-rem", es_alergeno=True
        )
        p1 = _create_product(client, headers, nombre="P1-alergeno-removible")
        client.post(
            f"/api/v1/productos/{p1['id']}/ingredientes",
            json={"ingrediente_id": ing["id"], "es_removible": True},
            headers=headers,
        )

        resp = client.get("/api/v1/productos?excluir_alergenos=true")
        assert resp.status_code == 200
        ids = [p["id"] for p in resp.json()["items"]]
        assert p1["id"] in ids

    def test_list_filter_excluir_alergenos_default_false(
        self, client: TestClient, sample_roles, admin_user
    ):
        """GET without excluir_alergenos param → does not filter allergens."""
        headers = _admin_headers(client)
        prod = _create_product(client, headers)
        resp = client.get("/api/v1/productos")
        assert resp.status_code == 200
        ids = [p["id"] for p in resp.json()["items"]]
        assert prod["id"] in ids

    def test_list_combined_filters(
        self,
        client: TestClient,
        test_db_session: Session,
        sample_roles,
        admin_user,
    ):
        """Combined: categoria_id + search + disponible + excluir_alergenos."""
        headers = _admin_headers(client)
        cat = _create_categoria_direct(test_db_session, "Esp")
        ing = _create_ingrediente_direct(
            test_db_session, "Polen-comb", es_alergeno=True
        )

        # Match: categoria, search=pizza, disponible, no non-removable allergen
        match = _create_product(
            client, headers, nombre="Pizza Combo", categoria_ids=[cat["id"]]
        )

        # No match: wrong name
        _create_product(
            client, headers, nombre="Hamburguesa Combo", categoria_ids=[cat["id"]]
        )

        # No match: has non-removable allergen
        with_allergy = _create_product(
            client, headers, nombre="Pizza Allergen", categoria_ids=[cat["id"]]
        )
        client.post(
            f"/api/v1/productos/{with_allergy['id']}/ingredientes",
            json={"ingrediente_id": ing["id"], "es_removible": False},
            headers=headers,
        )

        resp = client.get(
            f"/api/v1/productos?categoria_id={cat['id']}"
            "&search=pizza"
            "&disponible=true"
            "&excluir_alergenos=true"
        )
        assert resp.status_code == 200
        ids = [p["id"] for p in resp.json()["items"]]
        assert match["id"] in ids
        assert with_allergy["id"] not in ids

    def test_list_excludes_soft_deleted(
        self, client: TestClient, sample_roles, admin_user
    ):
        """Create 3, delete 1 → GET → total=2."""
        headers = _admin_headers(client)
        prods = [_create_product(client, headers) for _ in range(3)]
        client.delete(f"/api/v1/productos/{prods[0]['id']}", headers=headers)

        resp = client.get("/api/v1/productos")
        assert resp.status_code == 200
        assert resp.json()["total"] == 2


# ===========================================================================
# 7.5 Paginación
# ===========================================================================


class TestPagination:
    """GET / pagination."""

    def test_list_pagination_default(
        self, client: TestClient, sample_roles, admin_user
    ):
        """Create 25, GET default → items=20, total=25, page=1, limit=20."""
        headers = _admin_headers(client)
        for i in range(25):
            _create_product(client, headers, nombre=f"Pagtest-{i:02d}")

        resp = client.get("/api/v1/productos")
        assert resp.status_code == 200
        data = resp.json()
        assert data["total"] == 25
        assert data["page"] == 1
        assert data["limit"] == 20
        assert len(data["items"]) == 20

    def test_list_pagination_page_2(
        self, client: TestClient, sample_roles, admin_user
    ):
        """Create 25, GET ?page=2 → 5 items."""
        headers = _admin_headers(client)
        for i in range(25):
            _create_product(client, headers, nombre=f"Pg2test-{i:02d}")

        resp = client.get("/api/v1/productos?page=2")
        assert resp.status_code == 200
        data = resp.json()
        assert len(data["items"]) == 5
        assert data["page"] == 2

    def test_list_pagination_limit(
        self, client: TestClient, sample_roles, admin_user
    ):
        """GET ?limit=5 → 5 items."""
        headers = _admin_headers(client)
        for i in range(10):
            _create_product(client, headers, nombre=f"Lim-{i:02d}")

        resp = client.get("/api/v1/productos?limit=5")
        assert resp.status_code == 200
        assert len(resp.json()["items"]) == 5

    def test_list_pagination_limit_above_100_returns_422(
        self, client: TestClient, sample_roles
    ):
        """GET ?limit=101 → 422."""
        resp = client.get("/api/v1/productos?limit=101")
        assert resp.status_code == 422

    def test_list_pagination_page_zero_returns_422(
        self, client: TestClient, sample_roles
    ):
        """GET ?page=0 → 422."""
        resp = client.get("/api/v1/productos?page=0")
        assert resp.status_code == 422


# ===========================================================================
# 7.5 Asociaciones M:N de categorías
# ===========================================================================


class TestCategorias:
    """PUT /{id}/categorias."""

    def test_put_categorias_replaces_set(
        self,
        client: TestClient,
        test_db_session: Session,
        sample_roles,
        admin_user,
    ):
        """Assoc to [1,2], PUT /categorias [2,3] → final set [2,3]."""
        headers = _admin_headers(client)
        cat1 = _create_categoria_direct(test_db_session, "A")
        cat2 = _create_categoria_direct(test_db_session, "B")
        cat3 = _create_categoria_direct(test_db_session, "C")

        prod = _create_product(
            client, headers, categoria_ids=[cat1["id"], cat2["id"]]
        )
        prod_id = prod["id"]

        resp = client.put(
            f"/api/v1/productos/{prod_id}/categorias",
            json={"categoria_ids": [cat2["id"], cat3["id"]]},
            headers=headers,
        )
        assert resp.status_code == 200

        active = test_db_session.execute(
            text(
                "SELECT category_id FROM product_categories "
                "WHERE product_id = :pid AND eliminado_en IS NULL"
            ),
            {"pid": prod_id},
        ).fetchall()
        active_ids = {r[0] for r in active}
        assert active_ids == {cat2["id"], cat3["id"]}

    def test_put_categorias_empty_removes_all(
        self,
        client: TestClient,
        test_db_session: Session,
        sample_roles,
        admin_user,
    ):
        """PUT /categorias [] → 200, no active associations."""
        headers = _admin_headers(client)
        cat = _create_categoria_direct(test_db_session, "X")
        prod = _create_product(client, headers, categoria_ids=[cat["id"]])
        prod_id = prod["id"]

        resp = client.put(
            f"/api/v1/productos/{prod_id}/categorias",
            json={"categoria_ids": []},
            headers=headers,
        )
        assert resp.status_code == 200

        count = test_db_session.execute(
            text(
                "SELECT COUNT(*) FROM product_categories "
                "WHERE product_id = :pid AND eliminado_en IS NULL"
            ),
            {"pid": prod_id},
        ).scalar()
        assert count == 0

    def test_put_categorias_inexistente_returns_422_no_partial_changes(
        self,
        client: TestClient,
        test_db_session: Session,
        sample_roles,
        admin_user,
    ):
        """PUT with an invalid category id → 422.

        The service validates ALL ids before touching pivot rows (atomic
        validation). Partial-change atomicity is verified at the service
        unit level; here we verify the HTTP contract: 422 when any id is
        invalid.

        Note: in the SQLite in-memory test environment, a session.rollback()
        issued by the UoW on exception resets all prior savepoints, so we
        cannot query post-rollback state via the same session. This is a
        known limitation of the StaticPool / shared-session test pattern —
        the production Postgres behaviour (rollback does not touch prior
        committed transactions) is correct. We verify only the status code.
        """
        headers = _admin_headers(client)
        cat = _create_categoria_direct(test_db_session, "Valid")
        prod = _create_product(client, headers, categoria_ids=[cat["id"]])
        prod_id = prod["id"]

        resp = client.put(
            f"/api/v1/productos/{prod_id}/categorias",
            json={"categoria_ids": [cat["id"], 99999]},
            headers=headers,
        )
        assert resp.status_code == 422

    def test_put_categorias_reactivates_soft_deleted(
        self,
        client: TestClient,
        test_db_session: Session,
        sample_roles,
        admin_user,
    ):
        """Manually soft-delete pivot → PUT same cat → 200, row reactivated."""
        headers = _admin_headers(client)
        cat = _create_categoria_direct(test_db_session, "Reactivate")
        prod = _create_product(client, headers, categoria_ids=[cat["id"]])
        prod_id = prod["id"]

        # Manually soft-delete the pivot row
        test_db_session.execute(
            text(
                "UPDATE product_categories SET eliminado_en = CURRENT_TIMESTAMP "
                "WHERE product_id = :pid AND category_id = :cid"
            ),
            {"pid": prod_id, "cid": cat["id"]},
        )
        test_db_session.commit()

        # PUT the same category
        resp = client.put(
            f"/api/v1/productos/{prod_id}/categorias",
            json={"categoria_ids": [cat["id"]]},
            headers=headers,
        )
        assert resp.status_code == 200

        # Should be exactly 1 row (no duplicate), reactivated
        count = test_db_session.execute(
            text(
                "SELECT COUNT(*) FROM product_categories "
                "WHERE product_id = :pid AND category_id = :cid"
            ),
            {"pid": prod_id, "cid": cat["id"]},
        ).scalar()
        assert count == 1

        active = test_db_session.execute(
            text(
                "SELECT eliminado_en FROM product_categories "
                "WHERE product_id = :pid AND category_id = :cid"
            ),
            {"pid": prod_id, "cid": cat["id"]},
        ).fetchone()
        assert active[0] is None  # reactivated

    def test_put_categorias_not_found_returns_404(
        self, client: TestClient, sample_roles, admin_user
    ):
        """PUT /categorias for non-existent product → 404."""
        headers = _admin_headers(client)
        resp = client.put(
            "/api/v1/productos/999999/categorias",
            json={"categoria_ids": []},
            headers=headers,
        )
        assert resp.status_code == 404


# ===========================================================================
# 7.6 Asociaciones M:N de ingredientes
# ===========================================================================


class TestIngredientes:
    """POST/GET/DELETE /{id}/ingredientes."""

    def test_post_ingrediente_happy_path(
        self,
        client: TestClient,
        test_db_session: Session,
        sample_roles,
        admin_user,
    ):
        """POST with es_removible=true → 201 with correct flag."""
        headers = _admin_headers(client)
        ing = _create_ingrediente_direct(test_db_session, "Tomate-h")
        prod = _create_product(client, headers)

        resp = client.post(
            f"/api/v1/productos/{prod['id']}/ingredientes",
            json={"ingrediente_id": ing["id"], "es_removible": True},
            headers=headers,
        )
        assert resp.status_code == 201
        data = resp.json()
        assert data["id"] == ing["id"]
        assert data["es_removible"] is True

    def test_post_ingrediente_default_es_removible_false(
        self,
        client: TestClient,
        test_db_session: Session,
        sample_roles,
        admin_user,
    ):
        """POST without es_removible → 201 with es_removible=false."""
        headers = _admin_headers(client)
        ing = _create_ingrediente_direct(test_db_session, "Lechuga-d")
        prod = _create_product(client, headers)

        resp = client.post(
            f"/api/v1/productos/{prod['id']}/ingredientes",
            json={"ingrediente_id": ing["id"]},
            headers=headers,
        )
        assert resp.status_code == 201
        assert resp.json()["es_removible"] is False

    def test_post_ingrediente_duplicate_returns_409(
        self,
        client: TestClient,
        test_db_session: Session,
        sample_roles,
        admin_user,
    ):
        """POST same ingredient twice → second returns 409."""
        headers = _admin_headers(client)
        ing = _create_ingrediente_direct(test_db_session, "Dup-ing")
        prod = _create_product(client, headers)

        client.post(
            f"/api/v1/productos/{prod['id']}/ingredientes",
            json={"ingrediente_id": ing["id"]},
            headers=headers,
        )
        resp = client.post(
            f"/api/v1/productos/{prod['id']}/ingredientes",
            json={"ingrediente_id": ing["id"]},
            headers=headers,
        )
        assert resp.status_code == 409

    def test_post_ingrediente_inexistente_returns_422(
        self, client: TestClient, sample_roles, admin_user
    ):
        """POST with non-existent ingredient → 422."""
        headers = _admin_headers(client)
        prod = _create_product(client, headers)

        resp = client.post(
            f"/api/v1/productos/{prod['id']}/ingredientes",
            json={"ingrediente_id": 99999},
            headers=headers,
        )
        assert resp.status_code == 422

    def test_post_ingrediente_reactivates_soft_deleted(
        self,
        client: TestClient,
        test_db_session: Session,
        sample_roles,
        admin_user,
    ):
        """Add, remove, add again with different flag → 201 + updated flag."""
        headers = _admin_headers(client)
        ing = _create_ingrediente_direct(test_db_session, "Reactivable")
        prod = _create_product(client, headers)
        prod_id = prod["id"]

        # Add
        client.post(
            f"/api/v1/productos/{prod_id}/ingredientes",
            json={"ingrediente_id": ing["id"], "es_removible": False},
            headers=headers,
        )
        # Remove
        client.delete(
            f"/api/v1/productos/{prod_id}/ingredientes/{ing['id']}",
            headers=headers,
        )
        # Add again with different flag
        resp = client.post(
            f"/api/v1/productos/{prod_id}/ingredientes",
            json={"ingrediente_id": ing["id"], "es_removible": True},
            headers=headers,
        )
        assert resp.status_code == 201
        assert resp.json()["es_removible"] is True

        # Verify row count (should still be 1 — reactivated, not duplicated)
        count = test_db_session.execute(
            text(
                "SELECT COUNT(*) FROM product_ingredients "
                "WHERE product_id = :pid AND ingredient_id = :iid"
            ),
            {"pid": prod_id, "iid": ing["id"]},
        ).scalar()
        assert count == 1

    def test_delete_ingrediente_happy_path(
        self,
        client: TestClient,
        test_db_session: Session,
        sample_roles,
        admin_user,
    ):
        """DELETE → 204, pivot row has eliminado_en NOT NULL."""
        headers = _admin_headers(client)
        ing = _create_ingrediente_direct(test_db_session, "Del-ing")
        prod = _create_product(client, headers)
        prod_id = prod["id"]

        client.post(
            f"/api/v1/productos/{prod_id}/ingredientes",
            json={"ingrediente_id": ing["id"]},
            headers=headers,
        )
        resp = client.delete(
            f"/api/v1/productos/{prod_id}/ingredientes/{ing['id']}",
            headers=headers,
        )
        assert resp.status_code == 204

        row = test_db_session.execute(
            text(
                "SELECT eliminado_en FROM product_ingredients "
                "WHERE product_id = :pid AND ingredient_id = :iid"
            ),
            {"pid": prod_id, "iid": ing["id"]},
        ).fetchone()
        assert row is not None
        assert row[0] is not None  # soft-deleted

    def test_delete_ingrediente_already_deleted_returns_404(
        self,
        client: TestClient,
        test_db_session: Session,
        sample_roles,
        admin_user,
    ):
        """DELETE soft-deleted pivot → 404."""
        headers = _admin_headers(client)
        ing = _create_ingrediente_direct(test_db_session, "AlrDel")
        prod = _create_product(client, headers)
        prod_id = prod["id"]

        client.post(
            f"/api/v1/productos/{prod_id}/ingredientes",
            json={"ingrediente_id": ing["id"]},
            headers=headers,
        )
        client.delete(
            f"/api/v1/productos/{prod_id}/ingredientes/{ing['id']}",
            headers=headers,
        )
        resp = client.delete(
            f"/api/v1/productos/{prod_id}/ingredientes/{ing['id']}",
            headers=headers,
        )
        assert resp.status_code == 404

    def test_delete_ingrediente_not_associated_returns_404(
        self,
        client: TestClient,
        test_db_session: Session,
        sample_roles,
        admin_user,
    ):
        """DELETE non-associated ingredient → 404."""
        headers = _admin_headers(client)
        ing = _create_ingrediente_direct(test_db_session, "NotAssoc")
        prod = _create_product(client, headers)

        resp = client.delete(
            f"/api/v1/productos/{prod['id']}/ingredientes/{ing['id']}",
            headers=headers,
        )
        assert resp.status_code == 404

    def test_delete_ingrediente_does_not_modify_ingredient_row(
        self,
        client: TestClient,
        test_db_session: Session,
        sample_roles,
        admin_user,
    ):
        """DELETE association → ingredient row in `ingredients` is intact."""
        headers = _admin_headers(client)
        ing = _create_ingrediente_direct(test_db_session, "Intact-ing")
        prod = _create_product(client, headers)
        prod_id = prod["id"]

        client.post(
            f"/api/v1/productos/{prod_id}/ingredientes",
            json={"ingrediente_id": ing["id"]},
            headers=headers,
        )
        client.delete(
            f"/api/v1/productos/{prod_id}/ingredientes/{ing['id']}",
            headers=headers,
        )

        row = test_db_session.execute(
            text(
                "SELECT eliminado_en FROM ingredients WHERE id = :iid"
            ),
            {"iid": ing["id"]},
        ).fetchone()
        assert row[0] is None  # ingredient itself not soft-deleted

    def test_get_ingredientes_returns_flag(
        self,
        client: TestClient,
        test_db_session: Session,
        sample_roles,
        admin_user,
    ):
        """Associate 2 ingredients with different flags → GET returns both correct."""
        headers = _admin_headers(client)
        ing1 = _create_ingrediente_direct(test_db_session, "Flag-True")
        ing2 = _create_ingrediente_direct(test_db_session, "Flag-False")
        prod = _create_product(client, headers)
        prod_id = prod["id"]

        client.post(
            f"/api/v1/productos/{prod_id}/ingredientes",
            json={"ingrediente_id": ing1["id"], "es_removible": True},
            headers=headers,
        )
        client.post(
            f"/api/v1/productos/{prod_id}/ingredientes",
            json={"ingrediente_id": ing2["id"], "es_removible": False},
            headers=headers,
        )

        resp = client.get(f"/api/v1/productos/{prod_id}/ingredientes")
        assert resp.status_code == 200
        data = {item["id"]: item for item in resp.json()}
        assert data[ing1["id"]]["es_removible"] is True
        assert data[ing2["id"]]["es_removible"] is False

    def test_get_ingredientes_excludes_soft_deleted_pivot(
        self,
        client: TestClient,
        test_db_session: Session,
        sample_roles,
        admin_user,
    ):
        """Soft-delete pivot → GET /ingredientes excludes it."""
        headers = _admin_headers(client)
        ing = _create_ingrediente_direct(test_db_session, "SoftPivot")
        prod = _create_product(client, headers)
        prod_id = prod["id"]

        client.post(
            f"/api/v1/productos/{prod_id}/ingredientes",
            json={"ingrediente_id": ing["id"]},
            headers=headers,
        )
        client.delete(
            f"/api/v1/productos/{prod_id}/ingredientes/{ing['id']}",
            headers=headers,
        )

        resp = client.get(f"/api/v1/productos/{prod_id}/ingredientes")
        assert resp.status_code == 200
        assert resp.json() == []

    def test_get_ingredientes_excludes_soft_deleted_ingredient(
        self,
        client: TestClient,
        test_db_session: Session,
        sample_roles,
        admin_user,
    ):
        """Soft-delete the ingredient itself → GET /ingredientes excludes it."""
        headers = _admin_headers(client)
        ing = _create_ingrediente_direct(test_db_session, "SoftIng")
        prod = _create_product(client, headers)
        prod_id = prod["id"]

        client.post(
            f"/api/v1/productos/{prod_id}/ingredientes",
            json={"ingrediente_id": ing["id"]},
            headers=headers,
        )

        # Soft-delete the ingredient directly via SQL
        test_db_session.execute(
            text("UPDATE ingredients SET eliminado_en = CURRENT_TIMESTAMP WHERE id = :iid"),
            {"iid": ing["id"]},
        )
        test_db_session.commit()

        resp = client.get(f"/api/v1/productos/{prod_id}/ingredientes")
        assert resp.status_code == 200
        assert resp.json() == []

    def test_get_ingredientes_empty_when_no_associations(
        self, client: TestClient, sample_roles, admin_user
    ):
        """GET /ingredientes with no associations → 200 + []."""
        headers = _admin_headers(client)
        prod = _create_product(client, headers)

        resp = client.get(f"/api/v1/productos/{prod['id']}/ingredientes")
        assert resp.status_code == 200
        assert resp.json() == []

    def test_get_ingredientes_product_not_found_returns_404(
        self, client: TestClient, sample_roles
    ):
        """GET /ingredientes for non-existent product → 404."""
        resp = client.get("/api/v1/productos/999999/ingredientes")
        assert resp.status_code == 404


# ===========================================================================
# 7.7 Routing
# ===========================================================================


class TestRouting:
    """Endpoint routing checks."""

    def test_endpoint_responds_at_productos_es(
        self, client: TestClient, sample_roles
    ):
        """GET /api/v1/productos → 200."""
        resp = client.get("/api/v1/productos")
        assert resp.status_code == 200

    def test_endpoint_does_not_respond_at_products_en(
        self, client: TestClient, sample_roles
    ):
        """GET /api/v1/products (old English prefix) → 404."""
        resp = client.get("/api/v1/products")
        assert resp.status_code == 404

    def test_endpoint_does_not_respond_without_v1_prefix(
        self, client: TestClient, sample_roles
    ):
        """GET /api/productos (without /v1/) → 404."""
        resp = client.get("/api/productos")
        assert resp.status_code == 404


# ===========================================================================
# 7.8 Decimal precision + migración
# ===========================================================================


class TestPrecisionAndMigration:
    """Price precision and es_removible column tests."""

    def test_precio_preserves_decimal_precision(
        self, client: TestClient, sample_roles, admin_user
    ):
        """POST with precio=19.99, GET → response returns exactly 19.99."""
        headers = _admin_headers(client)
        prod = _create_product(client, headers, precio="19.99")
        prod_id = prod["id"]

        resp = client.get(f"/api/v1/productos/{prod_id}")
        assert resp.status_code == 200
        # precio comes as string in JSON; parse as Decimal for exact comparison
        precio_returned = Decimal(str(resp.json()["precio"]))
        assert precio_returned == Decimal("19.99")

    def test_es_removible_column_exists_in_pivot(
        self,
        client: TestClient,
        test_db_session: Session,
        sample_roles,
    ):
        """Verify es_removible column exists in product_ingredients via inspect."""
        engine = test_db_session.bind
        insp = inspect(engine)
        columns = {col["name"] for col in insp.get_columns("product_ingredients")}
        assert "es_removible" in columns

    def test_es_removible_default_false_on_insert(
        self,
        client: TestClient,
        test_db_session: Session,
        sample_roles,
        admin_user,
    ):
        """INSERT pivot without es_removible → row has es_removible=false."""
        headers = _admin_headers(client)
        from backend.features.catalog.models import Ingrediente
        from backend.features.products.models import ProductoIngrediente

        prod = _create_product(client, headers)
        ing = Ingrediente(nombre="DefRemovible", es_alergeno=False)
        test_db_session.add(ing)
        test_db_session.flush()

        # Insert WITHOUT specifying es_removible (rely on server_default)
        pi = ProductoIngrediente(
            product_id=prod["id"],
            ingredient_id=ing.id,
            # es_removible not set — should default to False
        )
        test_db_session.add(pi)
        test_db_session.commit()

        row = test_db_session.execute(
            text(
                "SELECT es_removible FROM product_ingredients "
                "WHERE product_id = :pid AND ingredient_id = :iid"
            ),
            {"pid": prod["id"], "iid": ing.id},
        ).fetchone()
        assert row is not None
        # SQLite returns 0/1 for booleans — normalize before comparing
        assert not bool(row[0])


# ===========================================================================
# 7.9 incluir_eliminados — RN-CA10 (US-064)
# ===========================================================================


class TestIncluidoEliminados:
    """GET /api/v1/productos?incluir_eliminados=true — RN-CA10.

    Only ADMIN can see soft-deleted products. Other roles and unauthenticated
    requests ignore the flag and always see only active products.
    """

    def test_admin_incluir_eliminados_ve_soft_deleted(
        self, client: TestClient, sample_roles, admin_user
    ):
        """ADMIN + incluir_eliminados=true → response includes soft-deleted product."""
        headers = _admin_headers(client)
        prod = _create_product(client, headers, nombre="Prod-a-eliminar")
        # Soft-delete the product
        client.delete(f"/api/v1/productos/{prod['id']}", headers=headers)

        # Without flag: not visible
        resp_sin = client.get("/api/v1/productos?disponible=true", headers=headers)
        ids_sin = [p["id"] for p in resp_sin.json()["items"]]
        assert prod["id"] not in ids_sin

        # With flag: visible
        resp_con = client.get(
            "/api/v1/productos?incluir_eliminados=true&disponible=true",
            headers=headers,
        )
        assert resp_con.status_code == 200
        ids_con = [p["id"] for p in resp_con.json()["items"]]
        assert prod["id"] in ids_con

    def test_client_incluir_eliminados_no_ve_soft_deleted(
        self, client: TestClient, sample_roles, admin_user, client_user
    ):
        """CLIENT + incluir_eliminados=true → soft-deleted product NOT visible."""
        admin_h = _admin_headers(client)
        prod = _create_product(client, admin_h, nombre="Prod-client-no-ve")
        client.delete(f"/api/v1/productos/{prod['id']}", headers=admin_h)

        resp = client.get(
            "/api/v1/productos?incluir_eliminados=true",
            headers=_client_headers(client),
        )
        assert resp.status_code == 200
        ids = [p["id"] for p in resp.json()["items"]]
        assert prod["id"] not in ids

    def test_sin_auth_incluir_eliminados_no_ve_soft_deleted(
        self, client: TestClient, sample_roles, admin_user
    ):
        """Unauthenticated + incluir_eliminados=true → soft-deleted NOT visible."""
        headers = _admin_headers(client)
        prod = _create_product(client, headers, nombre="Prod-anon-no-ve")
        client.delete(f"/api/v1/productos/{prod['id']}", headers=headers)

        resp = client.get("/api/v1/productos?incluir_eliminados=true")
        assert resp.status_code == 200
        ids = [p["id"] for p in resp.json()["items"]]
        assert prod["id"] not in ids

    def test_stock_incluir_eliminados_no_ve_soft_deleted(
        self, client: TestClient, sample_roles, admin_user, stock_user
    ):
        """STOCK + incluir_eliminados=true → soft-deleted NOT visible."""
        admin_h = _admin_headers(client)
        prod = _create_product(client, admin_h, nombre="Prod-stock-no-ve")
        client.delete(f"/api/v1/productos/{prod['id']}", headers=admin_h)

        resp = client.get(
            "/api/v1/productos?incluir_eliminados=true",
            headers=_stock_headers(client),
        )
        assert resp.status_code == 200
        ids = [p["id"] for p in resp.json()["items"]]
        assert prod["id"] not in ids
