"""
Integration tests for categories CRUD endpoints.

Covers:
- Create (auth, RBAC, validation, uniqueness)
- Read tree (public, nesting, soft-delete exclusion)
- Update (partial, parent change, cycle detection)
- Delete (soft-delete, guards, idempotency)
"""

from __future__ import annotations

from datetime import datetime, timezone

import pytest
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from features.catalog.models import Categoria
from features.products.models import Producto, ProductoCategoria


# =========================================================================
# Helpers
# =========================================================================


def _admin_headers(client: TestClient) -> dict[str, str]:
    """Get auth headers for an ADMIN user."""
    from shared.security import hash_password

    # Obtain test_db_session and sample_roles from the app state / fixtures.
    # We create an admin user by calling the register endpoint with a role
    # that gets admin privileges. But that requires the roles fixture.
    #
    # Instead, use the existing pattern from conftest: POST /login
    # for the admin user created in the fixture below.
    #
    # This helper assumes the fixture has created the admin.
    response = client.post(
        "/api/v1/auth/login",
        json={
            "email": "admin@test.com",
            "password": "admin_password_123",
        },
    )
    assert response.status_code == 200, f"Admin login failed: {response.json()}"
    data = response.json()
    return {}


def _stock_headers(client: TestClient) -> dict[str, str]:
    """Get auth headers for a STOCK user."""
    response = client.post(
        "/api/v1/auth/login",
        json={
            "email": "stock@test.com",
            "password": "stock_password_123",
        },
    )
    assert response.status_code == 200, f"Stock login failed: {response.json()}"
    data = response.json()
    return {}


# =========================================================================
# Fixtures
# =========================================================================


@pytest.fixture(scope="function")
def admin_user(test_db_session: Session, sample_roles):
    """Create an ADMIN user for testing."""
    from features.users.models import Usuario, UsuarioRol
    from shared.security import hash_password

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
    from features.users.models import Usuario, UsuarioRol
    from shared.security import hash_password

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
# CREATE
# =========================================================================


class TestCreate:
    """Tests for POST /api/v1/categorias."""

    def test_create_root_categoria_as_admin(
        self, client: TestClient, sample_roles, admin_user
    ):
        """Create a root category as ADMIN → 201."""
        headers = _admin_headers(client)
        response = client.post(
            "/api/v1/categorias",
            json={"nombre": "Bebidas"},
            headers=headers,
        )
        assert response.status_code == 201
        data = response.json()
        assert data["nombre"] == "Bebidas"
        assert data["padre_id"] is None
        assert "id" in data
        assert "creado_en" in data

    def test_create_subcategoria_as_stock(
        self, client: TestClient, sample_roles, stock_user
    ):
        """Create a root first, then a subcategory as STOCK → 201."""
        headers = _stock_headers(client)

        # Create root
        root_resp = client.post(
            "/api/v1/categorias",
            json={"nombre": "Bebidas"},
            headers=headers,
        )
        assert root_resp.status_code == 201
        root_id = root_resp.json()["id"]

        # Create subcategory
        child_resp = client.post(
            "/api/v1/categorias",
            json={"nombre": "Gaseosas", "padre_id": root_id},
            headers=headers,
        )
        assert child_resp.status_code == 201
        child_data = child_resp.json()
        assert child_data["nombre"] == "Gaseosas"
        assert child_data["padre_id"] == root_id

    def test_create_unauthenticated_returns_401(self, client: TestClient):
        """POST without token → 401."""
        response = client.post(
            "/api/v1/categorias",
            json={"nombre": "Bebidas"},
        )
        assert response.status_code == 401
        data = response.json()
        assert data["status"] == 401

    def test_create_as_client_returns_403(
        self, client: TestClient, sample_user, sample_roles
    ):
        """POST as CLIENT → 403."""
        headers = _get_auth_headers(client)
        response = client.post(
            "/api/v1/categorias",
            json={"nombre": "Bebidas"},
            headers=headers,
        )
        assert response.status_code == 403
        data = response.json()
        assert data["status"] == 403

    def test_create_empty_nombre_returns_422(
        self, client: TestClient, sample_roles, admin_user
    ):
        """POST with empty nombre → 422."""
        headers = _admin_headers(client)
        response = client.post(
            "/api/v1/categorias",
            json={"nombre": ""},
            headers=headers,
        )
        assert response.status_code == 422

    def test_create_nombre_too_long_returns_422(
        self, client: TestClient, sample_roles, admin_user
    ):
        """POST with 101-char nombre → 422."""
        headers = _admin_headers(client)
        response = client.post(
            "/api/v1/categorias",
            json={"nombre": "A" * 101},
            headers=headers,
        )
        assert response.status_code == 422

    def test_create_duplicate_root_name_returns_409(
        self, client: TestClient, sample_roles, admin_user
    ):
        """Two root categories with same name → 409."""
        headers = _admin_headers(client)
        client.post(
            "/api/v1/categorias", json={"nombre": "Bebidas"}, headers=headers
        )
        response = client.post(
            "/api/v1/categorias", json={"nombre": "Bebidas"}, headers=headers
        )
        assert response.status_code == 409

    def test_create_duplicate_sibling_name_returns_409(
        self, client: TestClient, sample_roles, admin_user
    ):
        """Two children of same parent with same name → 409."""
        headers = _admin_headers(client)

        root_resp = client.post(
            "/api/v1/categorias", json={"nombre": "Bebidas"}, headers=headers
        )
        root_id = root_resp.json()["id"]

        client.post(
            "/api/v1/categorias",
            json={"nombre": "Gaseosas", "padre_id": root_id},
            headers=headers,
        )
        response = client.post(
            "/api/v1/categorias",
            json={"nombre": "Gaseosas", "padre_id": root_id},
            headers=headers,
        )
        assert response.status_code == 409

    def test_create_same_name_different_levels_allowed(
        self, client: TestClient, sample_roles, admin_user
    ):
        """Same name at different levels → both 201."""
        headers = _admin_headers(client)

        # Root "Promos"
        resp1 = client.post(
            "/api/v1/categorias", json={"nombre": "Promos"}, headers=headers
        )
        assert resp1.status_code == 201

        # Create a child of root, then another "Promos" under it
        resp_inter = client.post(
            "/api/v1/categorias",
            json={"nombre": "Hamburguesas", "padre_id": resp1.json()["id"]},
            headers=headers,
        )
        resp2 = client.post(
            "/api/v1/categorias",
            json={"nombre": "Promos", "padre_id": resp_inter.json()["id"]},
            headers=headers,
        )
        assert resp2.status_code == 201
        assert resp2.json()["nombre"] == "Promos"

    def test_create_with_nonexistent_parent_returns_422(
        self, client: TestClient, sample_roles, admin_user
    ):
        """POST with non-existent padre_id → 422 or 404."""
        headers = _admin_headers(client)
        response = client.post(
            "/api/v1/categorias",
            json={"nombre": "Bebidas", "padre_id": 99999},
            headers=headers,
        )
        # BusinessRuleError maps to 422 per D9 in design.md
        assert response.status_code == 422


# =========================================================================
# READ / TREE
# =========================================================================


class TestTree:
    """Tests for GET /api/v1/categorias."""

    def test_get_tree_empty_returns_empty_list(
        self, client: TestClient, sample_roles
    ):
        """GET on empty table → 200 + []."""
        response = client.get("/api/v1/categorias")
        assert response.status_code == 200
        assert response.json() == []

    def test_get_tree_returns_nested_structure(
        self, client: TestClient, sample_roles, admin_user
    ):
        """Create a 3-level hierarchy, GET, validate nesting."""
        headers = _admin_headers(client)

        # Level 1
        r1 = client.post(
            "/api/v1/categorias", json={"nombre": "Bebidas"}, headers=headers
        ).json()
        # Level 2
        r2 = client.post(
            "/api/v1/categorias",
            json={"nombre": "Gaseosas", "padre_id": r1["id"]},
            headers=headers,
        ).json()
        # Level 3
        r3 = client.post(
            "/api/v1/categorias",
            json={"nombre": "Cola", "padre_id": r2["id"]},
            headers=headers,
        ).json()

        response = client.get("/api/v1/categorias")
        assert response.status_code == 200
        tree = response.json()
        assert len(tree) == 1  # Only one root
        assert tree[0]["nombre"] == "Bebidas"
        assert len(tree[0]["subcategorias"]) == 1
        assert tree[0]["subcategorias"][0]["nombre"] == "Gaseosas"
        assert len(tree[0]["subcategorias"][0]["subcategorias"]) == 1
        assert tree[0]["subcategorias"][0]["subcategorias"][0]["nombre"] == "Cola"

    def test_get_tree_excludes_soft_deleted(
        self, client: TestClient, sample_roles, admin_user, test_db_session
    ):
        """Soft-deleted nodes should NOT appear in the tree."""
        headers = _admin_headers(client)

        r1 = client.post(
            "/api/v1/categorias", json={"nombre": "Bebidas"}, headers=headers
        ).json()
        r2 = client.post(
            "/api/v1/categorias",
            json={"nombre": "Gaseosas", "padre_id": r1["id"]},
            headers=headers,
        ).json()

        # Soft-delete the child
        client.delete(f"/api/v1/categorias/{r2['id']}", headers=headers)

        # GET tree
        response = client.get("/api/v1/categorias")
        tree = response.json()
        assert len(tree) == 1
        assert len(tree[0]["subcategorias"]) == 0

    def test_get_tree_is_public(
        self, client: TestClient, sample_roles, admin_user
    ):
        """GET without token → 200."""
        headers = _admin_headers(client)
        client.post(
            "/api/v1/categorias", json={"nombre": "Bebidas"}, headers=headers
        )
        response = client.get("/api/v1/categorias")
        assert response.status_code == 200


# =========================================================================
# UPDATE
# =========================================================================


class TestUpdate:
    """Tests for PUT /api/v1/categorias/{id}."""

    def test_update_nombre_only(
        self, client: TestClient, sample_roles, admin_user
    ):
        """PUT with only nombre → 200, padre_id unchanged."""
        headers = _admin_headers(client)

        root = client.post(
            "/api/v1/categorias", json={"nombre": "Bebidas"}, headers=headers
        ).json()

        response = client.put(
            f"/api/v1/categorias/{root['id']}",
            json={"nombre": "Bebidas Sin Alcohol"},
            headers=headers,
        )
        assert response.status_code == 200
        data = response.json()
        assert data["nombre"] == "Bebidas Sin Alcohol"
        assert data["padre_id"] is None

    def test_update_padre_id_to_another_category(
        self, client: TestClient, sample_roles, admin_user
    ):
        """PUT with new padre_id → 200."""
        headers = _admin_headers(client)

        root = client.post(
            "/api/v1/categorias", json={"nombre": "Bebidas"}, headers=headers
        ).json()
        target = client.post(
            "/api/v1/categorias", json={"nombre": "Snacks"}, headers=headers
        ).json()
        child = client.post(
            "/api/v1/categorias",
            json={"nombre": "Gaseosas", "padre_id": root["id"]},
            headers=headers,
        ).json()

        response = client.put(
            f"/api/v1/categorias/{child['id']}",
            json={"padre_id": target["id"]},
            headers=headers,
        )
        assert response.status_code == 200
        assert response.json()["padre_id"] == target["id"]

    def test_update_promote_to_root(
        self, client: TestClient, sample_roles, admin_user
    ):
        """PUT with padre_id: null → 200, promote to root."""
        headers = _admin_headers(client)

        root = client.post(
            "/api/v1/categorias", json={"nombre": "Bebidas"}, headers=headers
        ).json()
        child = client.post(
            "/api/v1/categorias",
            json={"nombre": "Gaseosas", "padre_id": root["id"]},
            headers=headers,
        ).json()

        response = client.put(
            f"/api/v1/categorias/{child['id']}",
            json={"padre_id": None},
            headers=headers,
        )
        assert response.status_code == 200
        assert response.json()["padre_id"] is None

    def test_update_self_parent_returns_422(
        self, client: TestClient, sample_roles, admin_user
    ):
        """PUT with padre_id == self.id → 422."""
        headers = _admin_headers(client)

        root = client.post(
            "/api/v1/categorias", json={"nombre": "Bebidas"}, headers=headers
        ).json()

        response = client.put(
            f"/api/v1/categorias/{root['id']}",
            json={"padre_id": root["id"]},
            headers=headers,
        )
        assert response.status_code == 422

    def test_update_creates_direct_cycle_returns_422(
        self, client: TestClient, sample_roles, admin_user
    ):
        """A←B, PUT A with padre_id=B → 422 (direct cycle)."""
        headers = _admin_headers(client)

        a = client.post(
            "/api/v1/categorias", json={"nombre": "A"}, headers=headers
        ).json()
        b = client.post(
            "/api/v1/categorias",
            json={"nombre": "B", "padre_id": a["id"]},
            headers=headers,
        ).json()

        response = client.put(
            f"/api/v1/categorias/{a['id']}",
            json={"padre_id": b["id"]},
            headers=headers,
        )
        assert response.status_code == 422

    def test_update_creates_indirect_cycle_returns_422(
        self, client: TestClient, sample_roles, admin_user
    ):
        """A←B←C, PUT A with padre_id=C → 422 (indirect cycle)."""
        headers = _admin_headers(client)

        a = client.post(
            "/api/v1/categorias", json={"nombre": "A"}, headers=headers
        ).json()
        b = client.post(
            "/api/v1/categorias",
            json={"nombre": "B", "padre_id": a["id"]},
            headers=headers,
        ).json()
        c = client.post(
            "/api/v1/categorias",
            json={"nombre": "C", "padre_id": b["id"]},
            headers=headers,
        ).json()

        response = client.put(
            f"/api/v1/categorias/{a['id']}",
            json={"padre_id": c["id"]},
            headers=headers,
        )
        assert response.status_code == 422

    def test_update_nonexistent_returns_404(
        self, client: TestClient, sample_roles, admin_user
    ):
        """PUT with non-existent id → 404."""
        headers = _admin_headers(client)
        response = client.put(
            "/api/v1/categorias/99999",
            json={"nombre": "Nueva"},
            headers=headers,
        )
        assert response.status_code == 404

    def test_update_soft_deleted_returns_404(
        self, client: TestClient, sample_roles, admin_user
    ):
        """PUT to soft-deleted category → 404."""
        headers = _admin_headers(client)

        root = client.post(
            "/api/v1/categorias", json={"nombre": "Bebidas"}, headers=headers
        ).json()
        client.delete(f"/api/v1/categorias/{root['id']}", headers=headers)

        response = client.put(
            f"/api/v1/categorias/{root['id']}",
            json={"nombre": "Actualizado"},
            headers=headers,
        )
        assert response.status_code == 404


# =========================================================================
# DELETE (soft)
# =========================================================================


class TestDelete:
    """Tests for DELETE /api/v1/categorias/{id}."""

    def test_delete_leaf_succeeds(
        self, client: TestClient, sample_roles, admin_user, test_db_session
    ):
        """DELETE on leaf (no children, no products) → 204 + soft-deleted."""
        headers = _admin_headers(client)

        root = client.post(
            "/api/v1/categorias", json={"nombre": "Bebidas"}, headers=headers
        ).json()

        response = client.delete(
            f"/api/v1/categorias/{root['id']}", headers=headers
        )
        assert response.status_code == 204

        # Verify soft-deleted in DB
        cat = test_db_session.query(Categoria).filter_by(id=root["id"]).first()
        assert cat is not None
        assert cat.eliminado_en is not None

    def test_delete_does_not_hard_delete(
        self, client: TestClient, sample_roles, admin_user, test_db_session
    ):
        """Verify the row still exists with eliminado_en set."""
        headers = _admin_headers(client)

        root = client.post(
            "/api/v1/categorias", json={"nombre": "Bebidas"}, headers=headers
        ).json()
        client.delete(f"/api/v1/categorias/{root['id']}", headers=headers)

        # Row should still exist
        cat = test_db_session.query(Categoria).filter_by(id=root["id"]).first()
        assert cat is not None
        assert cat.eliminado_en is not None

    def test_delete_with_active_children_returns_422(
        self, client: TestClient, sample_roles, admin_user
    ):
        """DELETE on parent with active child → 422."""
        headers = _admin_headers(client)

        root = client.post(
            "/api/v1/categorias", json={"nombre": "Bebidas"}, headers=headers
        ).json()
        client.post(
            "/api/v1/categorias",
            json={"nombre": "Gaseosas", "padre_id": root["id"]},
            headers=headers,
        )

        response = client.delete(
            f"/api/v1/categorias/{root['id']}", headers=headers
        )
        assert response.status_code == 422

    def test_delete_after_children_soft_deleted_succeeds(
        self, client: TestClient, sample_roles, admin_user, test_db_session
    ):
        """Delete children first, then parent → 204."""
        headers = _admin_headers(client)

        root = client.post(
            "/api/v1/categorias", json={"nombre": "Bebidas"}, headers=headers
        ).json()
        child = client.post(
            "/api/v1/categorias",
            json={"nombre": "Gaseosas", "padre_id": root["id"]},
            headers=headers,
        ).json()

        # Delete child first
        client.delete(f"/api/v1/categorias/{child['id']}", headers=headers)

        # Now delete parent
        response = client.delete(
            f"/api/v1/categorias/{root['id']}", headers=headers
        )
        assert response.status_code == 204

    def test_delete_with_active_products_returns_422(
        self, client: TestClient, sample_roles, admin_user, test_db_session
    ):
        """DELETE on category with active product → 422."""
        headers = _admin_headers(client)

        root = client.post(
            "/api/v1/categorias", json={"nombre": "Bebidas"}, headers=headers
        ).json()

        # Create a product and associate it directly
        product = Producto(
            nombre="Cola 500ml",
            precio=10.50,
            stock_cantidad=100,
            disponible=True,
        )
        test_db_session.add(product)
        test_db_session.flush()

        pivot = ProductoCategoria(
            product_id=product.id, category_id=root["id"]
        )
        test_db_session.add(pivot)
        test_db_session.commit()

        response = client.delete(
            f"/api/v1/categorias/{root['id']}", headers=headers
        )
        assert response.status_code == 422

    def test_delete_already_deleted_returns_404(
        self, client: TestClient, sample_roles, admin_user
    ):
        """DELETE twice → 2nd time 404."""
        headers = _admin_headers(client)

        root = client.post(
            "/api/v1/categorias", json={"nombre": "Bebidas"}, headers=headers
        ).json()

        client.delete(f"/api/v1/categorias/{root['id']}", headers=headers)
        response = client.delete(
            f"/api/v1/categorias/{root['id']}", headers=headers
        )
        assert response.status_code == 404

    def test_delete_unauthenticated_returns_401(
        self, client: TestClient, sample_roles, admin_user
    ):
        """DELETE without token → 401."""
        headers = _admin_headers(client)
        root = client.post(
            "/api/v1/categorias", json={"nombre": "Bebidas"}, headers=headers
        ).json()

        response = client.delete(f"/api/v1/categorias/{root['id']}")
        assert response.status_code == 401

    def test_delete_as_client_returns_403(
        self, client: TestClient, sample_user, sample_roles, admin_user
    ):
        """DELETE as CLIENT → 403."""
        headers = _admin_headers(client)
        root = client.post(
            "/api/v1/categorias", json={"nombre": "Bebidas"}, headers=headers
        ).json()

        client_headers = _get_auth_headers(client)
        response = client.delete(
            f"/api/v1/categorias/{root['id']}", headers=client_headers
        )
        assert response.status_code == 403


# =========================================================================
# ROUTE PREFIX
# =========================================================================


class TestRouting:
    """Tests for URL prefix and routing."""

    def test_endpoints_use_v1_prefix_and_spanish_path(
        self, client: TestClient, sample_roles, admin_user
    ):
        """Verify correct and incorrect URLs."""
        headers = _admin_headers(client)

        # English path should 404
        response_en = client.get("/api/v1/categories", headers=headers)
        assert response_en.status_code == 404

        # Without v1 should 404
        response_no_v1 = client.get("/api/categorias", headers=headers)
        assert response_no_v1.status_code == 404

        # Correct path should work
        response_correct = client.get(
            "/api/v1/categorias", headers=headers
        )
        assert response_correct.status_code == 200


# =========================================================================
# Internal helper — reuses the sample_user CLIENT fixture from conftest
# =========================================================================


def _get_auth_headers(client: TestClient) -> dict[str, str]:
    """Get auth headers for the default sample_user (CLIENT role)."""
    response = client.post(
        "/api/v1/auth/login",
        json={
            "email": "test@example.com",
            "password": "test_password_123",
        },
    )
    assert response.status_code == 200
    data = response.json()
    return {}
