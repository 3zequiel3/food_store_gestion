"""
Integration tests for ingredients CRUD endpoints.

Covers:
- Happy path CRUD (create, read, list, update, delete)
- RBAC (ADMIN, STOCK, CLIENT, unauthenticated)
- Validation (empty nombre, too long, duplicates)
- Filters and pagination (es_alergeno, page, limit)
- 404 cases (not found, soft-deleted)
- Soft delete without guards
- Routing (versioned prefix, Spanish path)
"""

from __future__ import annotations

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import text
from sqlalchemy.orm import Session


# =========================================================================
# Auth helpers
# =========================================================================


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
    """Get auth headers for a CLIENT user (test@example.com from sample_user)."""
    response = client.post(
        "/api/v1/auth/login",
        json={"email": "test@example.com", "password": "test_password_123"},
    )
    assert response.status_code == 200, f"Client login failed: {response.json()}"
    return {}


# =========================================================================
# Fixtures
# =========================================================================


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
    user_role = UsuarioRol(user_id=user.id, role_id=1)  # role_id=1 = ADMIN
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
    user_role = UsuarioRol(user_id=user.id, role_id=2)  # role_id=2 = STOCK
    test_db_session.add(user_role)
    test_db_session.commit()
    test_db_session.refresh(user)
    return user


# =========================================================================
# Helper: create an ingredient via POST
# =========================================================================


def _create_ing(
    client: TestClient,
    headers: dict,
    nombre: str,
    es_alergeno: bool = False,
) -> dict:
    """POST /api/v1/ingredientes and assert 201."""
    resp = client.post(
        "/api/v1/ingredientes",
        json={"nombre": nombre, "es_alergeno": es_alergeno},
        headers=headers,
    )
    assert resp.status_code == 201, f"Failed to create ingredient: {resp.json()}"
    return resp.json()


# =========================================================================
# 7.1 Happy path CRUD
# =========================================================================


class TestCreate:
    """POST /api/v1/ingredientes — create ingredient."""

    def test_create_as_admin(self, client: TestClient, sample_roles, admin_user):
        """POST as ADMIN with es_alergeno=false → 201 with correct body."""
        headers = _admin_headers(client)
        resp = client.post(
            "/api/v1/ingredientes",
            json={"nombre": "Tomate", "es_alergeno": False},
            headers=headers,
        )
        assert resp.status_code == 201
        data = resp.json()
        assert data["nombre"] == "Tomate"
        assert data["es_alergeno"] is False
        assert "id" in data
        assert "creado_en" in data
        assert "actualizado_en" in data

    def test_create_as_stock_with_alergeno_true(
        self, client: TestClient, sample_roles, stock_user
    ):
        """POST as STOCK with es_alergeno=true → 201."""
        headers = _stock_headers(client)
        resp = client.post(
            "/api/v1/ingredientes",
            json={"nombre": "Mani", "es_alergeno": True},
            headers=headers,
        )
        assert resp.status_code == 201
        assert resp.json()["es_alergeno"] is True

    def test_create_default_es_alergeno_false(
        self, client: TestClient, sample_roles, admin_user
    ):
        """POST without es_alergeno field → 201 with es_alergeno: false."""
        headers = _admin_headers(client)
        resp = client.post(
            "/api/v1/ingredientes",
            json={"nombre": "Lechuga"},
            headers=headers,
        )
        assert resp.status_code == 201
        assert resp.json()["es_alergeno"] is False


class TestGetById:
    """GET /api/v1/ingredientes/{id}."""

    def test_get_by_id_returns_ingredient(
        self, client: TestClient, sample_roles, admin_user
    ):
        """Create then GET by id → 200 with correct body."""
        headers = _admin_headers(client)
        created = _create_ing(client, headers, "Sal")
        ing_id = created["id"]

        resp = client.get(f"/api/v1/ingredientes/{ing_id}")
        assert resp.status_code == 200
        data = resp.json()
        assert data["id"] == ing_id
        assert data["nombre"] == "Sal"


class TestList:
    """GET /api/v1/ingredientes — list with pagination."""

    def test_list_default_pagination(
        self, client: TestClient, sample_roles, admin_user
    ):
        """Create 3 ingredients, GET without params → total=3, page=1, limit=20."""
        headers = _admin_headers(client)
        for name in ["Tomate", "Lechuga", "Cebolla"]:
            _create_ing(client, headers, name)

        resp = client.get("/api/v1/ingredientes")
        assert resp.status_code == 200
        data = resp.json()
        assert data["total"] == 3
        assert data["page"] == 1
        assert data["limit"] == 20
        assert len(data["items"]) == 3


class TestUpdate:
    """PUT /api/v1/ingredientes/{id}."""

    def test_update_nombre_only_preserves_alergeno(
        self, client: TestClient, sample_roles, admin_user
    ):
        """Create with es_alergeno=true, PUT with only nombre → es_alergeno preserved."""
        headers = _admin_headers(client)
        created = _create_ing(client, headers, "Tomate", es_alergeno=True)
        ing_id = created["id"]

        resp = client.put(
            f"/api/v1/ingredientes/{ing_id}",
            json={"nombre": "Tomate Cherry"},
            headers=headers,
        )
        assert resp.status_code == 200
        data = resp.json()
        assert data["nombre"] == "Tomate Cherry"
        assert data["es_alergeno"] is True  # MUST be preserved

    def test_update_alergeno_only_preserves_nombre(
        self, client: TestClient, sample_roles, admin_user
    ):
        """Create with nombre=Mani, PUT with only es_alergeno=true → nombre preserved."""
        headers = _admin_headers(client)
        created = _create_ing(client, headers, "Mani", es_alergeno=False)
        ing_id = created["id"]

        resp = client.put(
            f"/api/v1/ingredientes/{ing_id}",
            json={"es_alergeno": True},
            headers=headers,
        )
        assert resp.status_code == 200
        data = resp.json()
        assert data["nombre"] == "Mani"  # MUST be preserved
        assert data["es_alergeno"] is True

    def test_update_both_fields(
        self, client: TestClient, sample_roles, admin_user
    ):
        """PUT with both fields → 200 with both updated."""
        headers = _admin_headers(client)
        created = _create_ing(client, headers, "Sal", es_alergeno=False)
        ing_id = created["id"]

        resp = client.put(
            f"/api/v1/ingredientes/{ing_id}",
            json={"nombre": "Sal Marina", "es_alergeno": True},
            headers=headers,
        )
        assert resp.status_code == 200
        data = resp.json()
        assert data["nombre"] == "Sal Marina"
        assert data["es_alergeno"] is True


class TestDelete:
    """DELETE /api/v1/ingredientes/{id}."""

    def test_delete_soft(
        self, client: TestClient, sample_roles, admin_user, test_db_session: Session
    ):
        """Create, DELETE → 204, row still in table with eliminado_en set."""
        headers = _admin_headers(client)
        created = _create_ing(client, headers, "Orégano")
        ing_id = created["id"]

        resp = client.delete(f"/api/v1/ingredientes/{ing_id}", headers=headers)
        assert resp.status_code == 204

        # Row still exists in DB
        row = test_db_session.execute(
            text("SELECT eliminado_en FROM ingredients WHERE id = :id"),
            {"id": ing_id},
        ).fetchone()
        assert row is not None
        assert row[0] is not None  # eliminado_en IS NOT NULL


# =========================================================================
# 7.2 RBAC
# =========================================================================


class TestRBAC:
    """Authentication and authorization checks."""

    def test_create_unauthenticated_returns_401(self, client: TestClient):
        """POST without token → 401."""
        resp = client.post(
            "/api/v1/ingredientes",
            json={"nombre": "Tomate"},
        )
        assert resp.status_code == 401
        assert resp.json()["status"] == 401

    def test_create_as_client_returns_403(
        self, client: TestClient, sample_user, sample_roles
    ):
        """POST as CLIENT → 403."""
        headers = _client_headers(client)
        resp = client.post(
            "/api/v1/ingredientes",
            json={"nombre": "Tomate"},
            headers=headers,
        )
        assert resp.status_code == 403
        assert resp.json()["status"] == 403

    def test_put_as_client_returns_403(
        self, client: TestClient, sample_user, sample_roles, admin_user
    ):
        """PUT as CLIENT → 403."""
        admin_hdrs = _admin_headers(client)
        created = _create_ing(client, admin_hdrs, "Tomate2")
        ing_id = created["id"]

        client_hdrs = _client_headers(client)
        resp = client.put(
            f"/api/v1/ingredientes/{ing_id}",
            json={"nombre": "Tomate Modificado"},
            headers=client_hdrs,
        )
        assert resp.status_code == 403

    def test_delete_as_client_returns_403(
        self, client: TestClient, sample_user, sample_roles, admin_user
    ):
        """DELETE as CLIENT → 403."""
        admin_hdrs = _admin_headers(client)
        created = _create_ing(client, admin_hdrs, "Tomate3")
        ing_id = created["id"]

        client_hdrs = _client_headers(client)
        resp = client.delete(f"/api/v1/ingredientes/{ing_id}", headers=client_hdrs)
        assert resp.status_code == 403

    def test_get_list_is_public(self, client: TestClient):
        """GET / without token → 200 (public)."""
        resp = client.get("/api/v1/ingredientes")
        assert resp.status_code == 200

    def test_get_by_id_is_public(
        self, client: TestClient, sample_roles, admin_user
    ):
        """GET /{id} without token → 200 (public)."""
        headers = _admin_headers(client)
        created = _create_ing(client, headers, "Azucar")
        ing_id = created["id"]

        resp = client.get(f"/api/v1/ingredientes/{ing_id}")
        assert resp.status_code == 200


# =========================================================================
# 7.3 Validación y unicidad
# =========================================================================


class TestValidation:
    """Input validation and uniqueness constraints."""

    def test_create_empty_nombre_returns_422(
        self, client: TestClient, sample_roles, admin_user
    ):
        """POST with nombre='' → 422."""
        headers = _admin_headers(client)
        resp = client.post(
            "/api/v1/ingredientes",
            json={"nombre": ""},
            headers=headers,
        )
        assert resp.status_code == 422

    def test_create_nombre_too_long_returns_422(
        self, client: TestClient, sample_roles, admin_user
    ):
        """POST with nombre of 256 chars → 422."""
        headers = _admin_headers(client)
        resp = client.post(
            "/api/v1/ingredientes",
            json={"nombre": "A" * 256},
            headers=headers,
        )
        assert resp.status_code == 422

    def test_create_duplicate_name_returns_409(
        self, client: TestClient, sample_roles, admin_user
    ):
        """Create 'Tomate', then POST 'Tomate' again → 409."""
        headers = _admin_headers(client)
        _create_ing(client, headers, "Tomate")

        resp = client.post(
            "/api/v1/ingredientes",
            json={"nombre": "Tomate"},
            headers=headers,
        )
        assert resp.status_code == 409
        assert resp.json()["status"] == 409

    def test_create_duplicate_of_soft_deleted_returns_409(
        self, client: TestClient, sample_roles, admin_user
    ):
        """Create 'Pimienta', soft-delete, POST 'Pimienta' again → 409.

        The UNIQUE constraint uq_ingredients_nombre covers all rows regardless
        of eliminado_en. The service's find_by_nombre also does not filter by
        eliminado_en, so it detects the name reservation.
        """
        headers = _admin_headers(client)
        created = _create_ing(client, headers, "Pimienta")
        ing_id = created["id"]

        # Soft-delete
        del_resp = client.delete(f"/api/v1/ingredientes/{ing_id}", headers=headers)
        assert del_resp.status_code == 204

        # Try to recreate with the same name
        resp = client.post(
            "/api/v1/ingredientes",
            json={"nombre": "Pimienta"},
            headers=headers,
        )
        assert resp.status_code == 409

    def test_update_to_existing_name_returns_409(
        self, client: TestClient, sample_roles, admin_user
    ):
        """Create A and B, PUT B with A's name → 409."""
        headers = _admin_headers(client)
        _create_ing(client, headers, "Tomate")
        ing_b = _create_ing(client, headers, "Lechuga")

        resp = client.put(
            f"/api/v1/ingredientes/{ing_b['id']}",
            json={"nombre": "Tomate"},
            headers=headers,
        )
        assert resp.status_code == 409

    def test_update_to_same_name_succeeds(
        self, client: TestClient, sample_roles, admin_user
    ):
        """PUT with same nombre → 200 (no conflict with itself)."""
        headers = _admin_headers(client)
        created = _create_ing(client, headers, "Aceite")
        ing_id = created["id"]

        resp = client.put(
            f"/api/v1/ingredientes/{ing_id}",
            json={"nombre": "Aceite"},
            headers=headers,
        )
        assert resp.status_code == 200
        assert resp.json()["nombre"] == "Aceite"

    def test_update_empty_nombre_returns_422(
        self, client: TestClient, sample_roles, admin_user
    ):
        """PUT with nombre='' → 422 (Pydantic min_length validation)."""
        headers = _admin_headers(client)
        created = _create_ing(client, headers, "Vinagre")
        ing_id = created["id"]

        resp = client.put(
            f"/api/v1/ingredientes/{ing_id}",
            json={"nombre": ""},
            headers=headers,
        )
        assert resp.status_code == 422


# =========================================================================
# 7.4 Filtros y paginación
# =========================================================================


class TestFiltersAndPagination:
    """Pagination, es_alergeno filter, and edge cases."""

    def test_list_filter_es_alergeno_true(
        self, client: TestClient, sample_roles, admin_user
    ):
        """3 allergens + 7 non-allergens; GET ?es_alergeno=true → total=3."""
        headers = _admin_headers(client)
        for i in range(3):
            _create_ing(client, headers, f"Alergeno{i}", es_alergeno=True)
        for i in range(7):
            _create_ing(client, headers, f"Normal{i}", es_alergeno=False)

        resp = client.get("/api/v1/ingredientes?es_alergeno=true")
        assert resp.status_code == 200
        data = resp.json()
        assert data["total"] == 3
        assert len(data["items"]) == 3
        assert all(item["es_alergeno"] is True for item in data["items"])

    def test_list_filter_es_alergeno_false(
        self, client: TestClient, sample_roles, admin_user
    ):
        """3 allergens + 7 non-allergens; GET ?es_alergeno=false → total=7."""
        headers = _admin_headers(client)
        for i in range(3):
            _create_ing(client, headers, f"Alerg{i}", es_alergeno=True)
        for i in range(7):
            _create_ing(client, headers, f"NoAlerg{i}", es_alergeno=False)

        resp = client.get("/api/v1/ingredientes?es_alergeno=false")
        assert resp.status_code == 200
        data = resp.json()
        assert data["total"] == 7
        assert all(item["es_alergeno"] is False for item in data["items"])

    def test_list_pagination_respects_limit(
        self, client: TestClient, sample_roles, admin_user
    ):
        """Create 25 ingredients, GET ?limit=10 → items.length=10, total=25."""
        headers = _admin_headers(client)
        for i in range(25):
            _create_ing(client, headers, f"Ing{i:02d}")

        resp = client.get("/api/v1/ingredientes?limit=10")
        assert resp.status_code == 200
        data = resp.json()
        assert data["total"] == 25
        assert data["page"] == 1
        assert data["limit"] == 10
        assert len(data["items"]) == 10

    def test_list_pagination_page_2(
        self, client: TestClient, sample_roles, admin_user
    ):
        """Create 25 ingredients, GET ?page=2&limit=10 → items.length=10, page=2."""
        headers = _admin_headers(client)
        for i in range(25):
            _create_ing(client, headers, f"Pag{i:02d}")

        resp = client.get("/api/v1/ingredientes?page=2&limit=10")
        assert resp.status_code == 200
        data = resp.json()
        assert data["page"] == 2
        assert len(data["items"]) == 10

    def test_list_pagination_last_page_partial(
        self, client: TestClient, sample_roles, admin_user
    ):
        """Create 25 ingredients, GET ?page=3&limit=10 → items.length=5."""
        headers = _admin_headers(client)
        for i in range(25):
            _create_ing(client, headers, f"Parcial{i:02d}")

        resp = client.get("/api/v1/ingredientes?page=3&limit=10")
        assert resp.status_code == 200
        data = resp.json()
        assert data["page"] == 3
        assert len(data["items"]) == 5

    def test_list_limit_above_100_returns_422(self, client: TestClient):
        """GET ?limit=200 → 422."""
        resp = client.get("/api/v1/ingredientes?limit=200")
        assert resp.status_code == 422

    def test_list_page_zero_returns_422(self, client: TestClient):
        """GET ?page=0 → 422."""
        resp = client.get("/api/v1/ingredientes?page=0")
        assert resp.status_code == 422

    def test_list_excludes_soft_deleted(
        self, client: TestClient, sample_roles, admin_user
    ):
        """Create 3, soft-delete 1, GET → total=2."""
        headers = _admin_headers(client)
        a = _create_ing(client, headers, "IngA")
        _create_ing(client, headers, "IngB")
        _create_ing(client, headers, "IngC")

        client.delete(f"/api/v1/ingredientes/{a['id']}", headers=headers)

        resp = client.get("/api/v1/ingredientes")
        assert resp.status_code == 200
        assert resp.json()["total"] == 2


# =========================================================================
# 7.5 404s
# =========================================================================


class Test404:
    """Not-found and soft-deleted ingredient responses."""

    def test_get_by_id_not_found(self, client: TestClient):
        """GET non-existent id → 404."""
        resp = client.get("/api/v1/ingredientes/99999")
        assert resp.status_code == 404

    def test_get_by_id_soft_deleted_returns_404(
        self, client: TestClient, sample_roles, admin_user
    ):
        """Soft-delete then GET → 404."""
        headers = _admin_headers(client)
        created = _create_ing(client, headers, "Borrado")
        ing_id = created["id"]

        client.delete(f"/api/v1/ingredientes/{ing_id}", headers=headers)

        resp = client.get(f"/api/v1/ingredientes/{ing_id}")
        assert resp.status_code == 404

    def test_update_not_found_returns_404(
        self, client: TestClient, sample_roles, admin_user
    ):
        """PUT non-existent id → 404."""
        headers = _admin_headers(client)
        resp = client.put(
            "/api/v1/ingredientes/99999",
            json={"nombre": "X"},
            headers=headers,
        )
        assert resp.status_code == 404

    def test_update_soft_deleted_returns_404(
        self, client: TestClient, sample_roles, admin_user
    ):
        """Soft-delete then PUT → 404."""
        headers = _admin_headers(client)
        created = _create_ing(client, headers, "BorradoPUT")
        ing_id = created["id"]

        client.delete(f"/api/v1/ingredientes/{ing_id}", headers=headers)

        resp = client.put(
            f"/api/v1/ingredientes/{ing_id}",
            json={"nombre": "Nuevo"},
            headers=headers,
        )
        assert resp.status_code == 404

    def test_delete_not_found_returns_404(
        self, client: TestClient, sample_roles, admin_user
    ):
        """DELETE non-existent id → 404."""
        headers = _admin_headers(client)
        resp = client.delete("/api/v1/ingredientes/99999", headers=headers)
        assert resp.status_code == 404

    def test_delete_already_deleted_returns_404(
        self, client: TestClient, sample_roles, admin_user
    ):
        """DELETE twice → 2nd call returns 404."""
        headers = _admin_headers(client)
        created = _create_ing(client, headers, "DeleteTwice")
        ing_id = created["id"]

        first = client.delete(f"/api/v1/ingredientes/{ing_id}", headers=headers)
        assert first.status_code == 204

        second = client.delete(f"/api/v1/ingredientes/{ing_id}", headers=headers)
        assert second.status_code == 404


# =========================================================================
# 7.6 Soft delete sin guards
# =========================================================================


class TestSoftDelete:
    """Soft delete mechanics and D4 (no guard on product associations)."""

    def test_delete_does_not_hard_delete(
        self, client: TestClient, sample_roles, admin_user, test_db_session: Session
    ):
        """Verify via direct SQL that the row remains with eliminado_en set."""
        headers = _admin_headers(client)
        created = _create_ing(client, headers, "PermanentRow")
        ing_id = created["id"]

        client.delete(f"/api/v1/ingredientes/{ing_id}", headers=headers)

        row = test_db_session.execute(
            text("SELECT id, eliminado_en FROM ingredients WHERE id = :id"),
            {"id": ing_id},
        ).fetchone()
        assert row is not None, "Row was hard-deleted — MUST NOT happen"
        assert row[1] is not None, "eliminado_en should be set after soft delete"

    def test_delete_with_associated_products_succeeds(
        self, client: TestClient, sample_roles, admin_user, test_db_session: Session
    ):
        """DELETE an ingredient that has product_ingredients rows → 204 (no guard).

        We insert a minimal product row and a product_ingredients pivot row
        directly via SQL to simulate an association. The DELETE must succeed
        without checking the pivot table (D4 in design.md).
        The pivot row must remain after the soft delete.
        """
        headers = _admin_headers(client)
        created = _create_ing(client, headers, "IngConProducto", es_alergeno=False)
        ing_id = created["id"]

        # Insert a minimal product (only required non-null columns).
        # Column names match the Producto model: stock_cantidad, disponible.
        # precio must be > 0 (CHECK constraint ck_products_precio_positivo).
        test_db_session.execute(
            text(
                "INSERT INTO products (nombre, descripcion, precio, stock_cantidad, disponible) "
                "VALUES ('ProdTest', 'desc', 1.0, 0, 1)"
            )
        )
        test_db_session.flush()
        product_row = test_db_session.execute(
            text("SELECT id FROM products WHERE nombre = 'ProdTest'")
        ).fetchone()
        product_id = product_row[0]

        # Insert product_ingredients pivot row
        test_db_session.execute(
            text(
                "INSERT INTO product_ingredients (product_id, ingredient_id) "
                "VALUES (:pid, :iid)"
            ),
            {"pid": product_id, "iid": ing_id},
        )
        test_db_session.commit()

        # Delete the ingredient — must succeed without guard
        resp = client.delete(f"/api/v1/ingredientes/{ing_id}", headers=headers)
        assert resp.status_code == 204

        # Pivot row must still exist
        pivot = test_db_session.execute(
            text(
                "SELECT 1 FROM product_ingredients "
                "WHERE product_id = :pid AND ingredient_id = :iid"
            ),
            {"pid": product_id, "iid": ing_id},
        ).fetchone()
        assert pivot is not None, "Pivot row should remain after soft delete"


# =========================================================================
# 7.7 Routing
# =========================================================================


class TestRouting:
    """Verify versioned Spanish prefix and reject wrong paths."""

    def test_endpoint_uses_v1_prefix_and_spanish_path(self, client: TestClient):
        """English path or missing v1 prefix → 404.

        The correct path is /api/v1/ingredientes (Spanish, versioned).
        - /api/v1/ingredients (English) → 404
        - /api/ingredientes (missing v1) → 404
        """
        resp_english = client.get("/api/v1/ingredients")
        assert resp_english.status_code == 404, (
            "English path /api/v1/ingredients should not exist"
        )

        resp_no_version = client.get("/api/ingredientes")
        assert resp_no_version.status_code == 404, (
            "Unversioned /api/ingredientes should not exist"
        )


# =========================================================================
# incluir_eliminados — RN-CA10 (US-064)
# =========================================================================


class TestIncluidoEliminados:
    """GET /api/v1/ingredientes?incluir_eliminados=true — RN-CA10.

    Only ADMIN can see soft-deleted ingredients. Other roles and
    unauthenticated requests ignore the flag and always see only active ones.
    """

    def test_admin_incluir_eliminados_ve_soft_deleted(
        self, client: TestClient, sample_roles, admin_user
    ):
        """ADMIN + incluir_eliminados=true → response includes soft-deleted ingredient."""
        headers = _admin_headers(client)
        ing = _create_ing(client, headers, nombre="Ing-a-eliminar")
        # Soft-delete the ingredient
        client.delete(f"/api/v1/ingredientes/{ing['id']}", headers=headers)

        # Without flag: not visible
        resp_sin = client.get("/api/v1/ingredientes")
        ids_sin = [i["id"] for i in resp_sin.json()["items"]]
        assert ing["id"] not in ids_sin

        # With flag: visible
        resp_con = client.get(
            "/api/v1/ingredientes?incluir_eliminados=true", headers=headers
        )
        assert resp_con.status_code == 200
        ids_con = [i["id"] for i in resp_con.json()["items"]]
        assert ing["id"] in ids_con

    def test_client_incluir_eliminados_no_ve_soft_deleted(
        self, client: TestClient, sample_roles, admin_user, sample_user
    ):
        """CLIENT + incluir_eliminados=true → soft-deleted ingredient NOT visible."""
        admin_h = _admin_headers(client)
        ing = _create_ing(client, admin_h, nombre="Ing-client-no-ve")
        client.delete(f"/api/v1/ingredientes/{ing['id']}", headers=admin_h)

        resp = client.get(
            "/api/v1/ingredientes?incluir_eliminados=true",
            headers=_client_headers(client),
        )
        assert resp.status_code == 200
        ids = [i["id"] for i in resp.json()["items"]]
        assert ing["id"] not in ids

    def test_sin_auth_incluir_eliminados_no_ve_soft_deleted(
        self, client: TestClient, sample_roles, admin_user
    ):
        """Unauthenticated + incluir_eliminados=true → soft-deleted NOT visible."""
        headers = _admin_headers(client)
        ing = _create_ing(client, headers, nombre="Ing-anon-no-ve")
        client.delete(f"/api/v1/ingredientes/{ing['id']}", headers=headers)

        resp = client.get("/api/v1/ingredientes?incluir_eliminados=true")
        assert resp.status_code == 200
        ids = [i["id"] for i in resp.json()["items"]]
        assert ing["id"] not in ids
