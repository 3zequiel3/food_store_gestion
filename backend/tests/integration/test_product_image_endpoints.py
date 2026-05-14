"""
Integration tests for product image CRUD endpoints and categoria_ids validation.

Covers:
- POST /{id}/imagenes (file upload)
- POST /{id}/imagenes/url
- DELETE /{id}/imagenes/{img_id}
- PATCH /{id}/imagenes/{img_id}/orden
- PATCH /{id}/imagenes/{img_id}/primaria
- Legacy POST /{id}/imagen also creates ProductoImagen
- categoria_ids required validation
- ingrediente_ids support on creation
"""

from __future__ import annotations

import io
import uuid

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import text
from sqlalchemy.orm import Session

from features.products.models import ProductoImagen


# ===========================================================================
# Auth helpers (reuse from test_products.py pattern)
# ===========================================================================


def _admin_headers(client: TestClient) -> dict[str, str]:
    response = client.post(
        "/api/v1/auth/login",
        json={"email": "admin@test.com", "password": "admin_password_123"},
    )
    assert response.status_code == 200, f"Admin login failed: {response.json()}"
    return {}


# ===========================================================================
# Fixtures
# ===========================================================================


@pytest.fixture(scope="function")
def admin_user(test_db_session: Session, sample_roles):
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
    user_role = UsuarioRol(user_id=user.id, role_id=1)
    test_db_session.add(user_role)
    test_db_session.commit()
    test_db_session.refresh(user)
    return user


@pytest.fixture(scope="function")
def stock_user(test_db_session: Session, sample_roles):
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
    user_role = UsuarioRol(user_id=user.id, role_id=2)
    test_db_session.add(user_role)
    test_db_session.commit()
    test_db_session.refresh(user)
    return user


def _create_product_direct(test_db_session: Session) -> dict:
    """Create a product + category directly in DB (bypasses API auth)."""
    from decimal import Decimal
    from features.products.models import Producto, ProductoCategoria
    from features.catalog.models import Categoria

    cat = Categoria(nombre=f"Cat-{uuid.uuid4().hex[:4]}")
    test_db_session.add(cat)
    test_db_session.flush()

    p = Producto(
        nombre=f"P-{uuid.uuid4().hex[:8]}",
        precio=Decimal("10.00"),
        stock_cantidad=10,
        disponible=True,
    )
    test_db_session.add(p)
    test_db_session.flush()
    test_db_session.commit()
    test_db_session.refresh(p)

    pc = ProductoCategoria(product_id=p.id, category_id=cat.id)
    test_db_session.add(pc)
    test_db_session.commit()

    return {"id": p.id}


def _create_product(
    client: TestClient, headers: dict, test_db_session: Session = None, **overrides
) -> dict:
    payload = {
        "nombre": f"P-{uuid.uuid4().hex[:8]}",
        "precio": "10.00",
        "stock_cantidad": 20,
        "disponible": True,
    }
    # If no categoria_ids provided and test_db_session available, create one
    if "categoria_ids" not in overrides and test_db_session is not None:
        cat = _create_categoria_direct(test_db_session, f"Cat-{uuid.uuid4().hex[:4]}")
        payload["categoria_ids"] = [cat["id"]]
    payload.update(overrides)
    resp = client.post("/api/v1/productos", json=payload, headers=headers)
    assert resp.status_code == 201, f"Failed to create product: {resp.json()}"
    return resp.json()


def _create_categoria_direct(session: Session, nombre: str = "Cat-X") -> dict:
    from features.catalog.models import Categoria

    cat = Categoria(nombre=nombre)
    session.add(cat)
    session.flush()
    session.commit()
    return {"id": cat.id, "nombre": cat.nombre}


def _create_ingrediente_direct(
    session: Session, nombre: str = "Ing-X", es_alergeno: bool = False
) -> dict:
    from features.catalog.models import Ingrediente

    ing = Ingrediente(nombre=nombre, es_alergeno=es_alergeno)
    session.add(ing)
    session.flush()
    session.commit()
    return {"id": ing.id, "nombre": ing.nombre, "es_alergeno": ing.es_alergeno}


# ===========================================================================
# Image CRUD endpoints
# ===========================================================================


class TestImageUpload:
    """POST /{id}/imagenes (file upload)."""

    def test_upload_first_image_is_primary(
        self, client: TestClient, sample_roles, admin_user, test_db_session: Session
    ):
        """Upload first image → es_primaria=true, orden=0."""
        headers = _admin_headers(client)
        prod = _create_product(client, headers, test_db_session)
        prod_id = prod["id"]

        # Create a fake JPEG file
        file_content = b"\xff\xd8\xff\xe0" + b"\x00" * 100  # Minimal JPEG header
        resp = client.post(
            f"/api/v1/productos/{prod_id}/imagenes",
            files={"file": ("test.jpg", io.BytesIO(file_content), "image/jpeg")},
            headers=headers,
        )
        assert resp.status_code == 201, resp.json()
        data = resp.json()
        assert data["es_primaria"] is True
        assert data["orden"] == 0
        assert "url" in data

    def test_upload_second_image_not_primary(
        self, client: TestClient, sample_roles, admin_user, test_db_session: Session
    ):
        """Upload when primary exists → es_primaria=false, orden=1."""
        headers = _admin_headers(client)
        prod = _create_product(client, headers, test_db_session)
        prod_id = prod["id"]

        file_content = b"\xff\xd8\xff\xe0" + b"\x00" * 100
        # First image
        client.post(
            f"/api/v1/productos/{prod_id}/imagenes",
            files={"file": ("img1.jpg", io.BytesIO(file_content), "image/jpeg")},
            headers=headers,
        )
        # Second image
        resp = client.post(
            f"/api/v1/productos/{prod_id}/imagenes",
            files={"file": ("img2.jpg", io.BytesIO(file_content), "image/jpeg")},
            headers=headers,
        )
        assert resp.status_code == 201, resp.json()
        data = resp.json()
        assert data["es_primaria"] is False
        assert data["orden"] == 1

    def test_upload_invalid_file_type_rejected(
        self, client: TestClient, sample_roles, admin_user, test_db_session: Session
    ):
        """Upload PDF → 422."""
        headers = _admin_headers(client)
        prod = _create_product(client, headers, test_db_session)

        resp = client.post(
            f"/api/v1/productos/{prod['id']}/imagenes",
            files={"file": ("doc.pdf", io.BytesIO(b"%PDF-1.4"), "application/pdf")},
            headers=headers,
        )
        assert resp.status_code == 422

    def test_upload_unauthenticated_returns_401(
        self, client: TestClient, sample_roles, admin_user, test_db_session: Session
    ):
        """POST /imagenes without auth → 401."""
        prod = _create_product_direct(test_db_session)

        file_content = b"\xff\xd8\xff\xe0" + b"\x00" * 100
        resp = client.post(
            f"/api/v1/productos/{prod['id']}/imagenes",
            files={"file": ("test.jpg", io.BytesIO(file_content), "image/jpeg")},
        )
        assert resp.status_code == 401


class TestImageUrl:
    """POST /{id}/imagenes/url."""

    def test_add_image_by_url(
        self, client: TestClient, sample_roles, admin_user, test_db_session: Session
    ):
        """POST /imagenes/url with valid URL → 201."""
        headers = _admin_headers(client)
        prod = _create_product(client, headers, test_db_session)

        resp = client.post(
            f"/api/v1/productos/{prod['id']}/imagenes/url",
            json={"url": "https://example.com/img.jpg"},
            headers=headers,
        )
        assert resp.status_code == 201, resp.json()
        data = resp.json()
        assert data["url"] == "https://example.com/img.jpg"

    def test_invalid_url_rejected(
        self, client: TestClient, sample_roles, admin_user, test_db_session: Session
    ):
        """POST /imagenes/url with invalid URL → 422."""
        prod = _create_product_direct(test_db_session)
        headers = _admin_headers(client)

        resp = client.post(
            f"/api/v1/productos/{prod['id']}/imagenes/url",
            json={"url": "not-a-url"},
            headers=headers,
        )
        assert resp.status_code == 422


class TestImageDelete:
    """DELETE /{id}/imagenes/{img_id}."""

    def test_delete_non_primary_image(
        self, client: TestClient, sample_roles, admin_user, test_db_session: Session
    ):
        """Delete non-primary → 204, primary remains."""
        headers = _admin_headers(client)
        prod = _create_product(client, headers, test_db_session)
        prod_id = prod["id"]

        file_content = b"\xff\xd8\xff\xe0" + b"\x00" * 100
        # Upload two images
        resp1 = client.post(
            f"/api/v1/productos/{prod_id}/imagenes",
            files={"file": ("a.jpg", io.BytesIO(file_content), "image/jpeg")},
            headers=headers,
        )
        img1_id = resp1.json()["id"]
        resp2 = client.post(
            f"/api/v1/productos/{prod_id}/imagenes",
            files={"file": ("b.jpg", io.BytesIO(file_content), "image/jpeg")},
            headers=headers,
        )
        img2_id = resp2.json()["id"]

        # Delete second (non-primary)
        resp = client.delete(
            f"/api/v1/productos/{prod_id}/imagenes/{img2_id}",
            headers=headers,
        )
        assert resp.status_code == 204

        # First image still primary
        primary_count = test_db_session.execute(
            text(
                "SELECT COUNT(*) FROM product_images "
                "WHERE producto_id = :pid AND es_primaria = 1 AND eliminado_en IS NULL"
            ),
            {"pid": prod_id},
        ).scalar()
        assert primary_count == 1

    def test_delete_primary_reassigns(
        self, client: TestClient, sample_roles, admin_user, test_db_session: Session
    ):
        """Delete primary → next image becomes primary."""
        headers = _admin_headers(client)
        prod = _create_product(client, headers, test_db_session)
        prod_id = prod["id"]

        file_content = b"\xff\xd8\xff\xe0" + b"\x00" * 100
        resp1 = client.post(
            f"/api/v1/productos/{prod_id}/imagenes",
            files={"file": ("a.jpg", io.BytesIO(file_content), "image/jpeg")},
            headers=headers,
        )
        img1_id = resp1.json()["id"]
        client.post(
            f"/api/v1/productos/{prod_id}/imagenes",
            files={"file": ("b.jpg", io.BytesIO(file_content), "image/jpeg")},
            headers=headers,
        )

        # Delete primary
        resp = client.delete(
            f"/api/v1/productos/{prod_id}/imagenes/{img1_id}",
            headers=headers,
        )
        assert resp.status_code == 204

        # Second image should now be primary
        rows = test_db_session.execute(
            text(
                "SELECT COUNT(*) FROM product_images "
                "WHERE producto_id = :pid AND es_primaria = 1 AND eliminado_en IS NULL"
            ),
            {"pid": prod_id},
        ).fetchone()
        assert rows[0] == 1

    def test_delete_last_image(
        self, client: TestClient, sample_roles, admin_user, test_db_session: Session
    ):
        """Delete last image → 204, product has no images."""
        headers = _admin_headers(client)
        prod = _create_product(client, headers, test_db_session)
        prod_id = prod["id"]

        file_content = b"\xff\xd8\xff\xe0" + b"\x00" * 100
        resp = client.post(
            f"/api/v1/productos/{prod_id}/imagenes",
            files={"file": ("only.jpg", io.BytesIO(file_content), "image/jpeg")},
            headers=headers,
        )
        img_id = resp.json()["id"]

        resp = client.delete(
            f"/api/v1/productos/{prod_id}/imagenes/{img_id}",
            headers=headers,
        )
        assert resp.status_code == 204

        count = test_db_session.execute(
            text(
                "SELECT COUNT(*) FROM product_images "
                "WHERE producto_id = :pid AND eliminado_en IS NULL"
            ),
            {"pid": prod_id},
        ).scalar()
        assert count == 0

    def test_delete_not_found_returns_404(
        self, client: TestClient, sample_roles, admin_user, test_db_session: Session
    ):
        """DELETE non-existent image → 404."""
        prod = _create_product_direct(test_db_session)
        headers = _admin_headers(client)

        resp = client.delete(
            f"/api/v1/productos/{prod['id']}/imagenes/99999",
            headers=headers,
        )
        assert resp.status_code == 404


class TestImageOrder:
    """PATCH /{id}/imagenes/{img_id}/orden."""

    def test_change_image_order(
        self, client: TestClient, sample_roles, admin_user, test_db_session: Session
    ):
        """PATCH orden → 200 with new orden."""
        headers = _admin_headers(client)
        prod = _create_product(client, headers, test_db_session)
        prod_id = prod["id"]

        file_content = b"\xff\xd8\xff\xe0" + b"\x00" * 100
        resp = client.post(
            f"/api/v1/productos/{prod_id}/imagenes",
            files={"file": ("test.jpg", io.BytesIO(file_content), "image/jpeg")},
            headers=headers,
        )
        img_id = resp.json()["id"]

        resp = client.patch(
            f"/api/v1/productos/{prod_id}/imagenes/{img_id}/orden",
            json={"orden": 5},
            headers=headers,
        )
        assert resp.status_code == 200, resp.json()
        assert resp.json()["orden"] == 5


class TestImagePrimary:
    """PATCH /{id}/imagenes/{img_id}/primaria."""

    def test_set_new_primary(
        self, client: TestClient, sample_roles, admin_user, test_db_session: Session
    ):
        """Set B as primary → A becomes non-primary."""
        headers = _admin_headers(client)
        prod = _create_product(client, headers, test_db_session)
        prod_id = prod["id"]

        file_content = b"\xff\xd8\xff\xe0" + b"\x00" * 100
        resp_a = client.post(
            f"/api/v1/productos/{prod_id}/imagenes",
            files={"file": ("a.jpg", io.BytesIO(file_content), "image/jpeg")},
            headers=headers,
        )
        img_a_id = resp_a.json()["id"]
        resp_b = client.post(
            f"/api/v1/productos/{prod_id}/imagenes",
            files={"file": ("b.jpg", io.BytesIO(file_content), "image/jpeg")},
            headers=headers,
        )
        img_b_id = resp_b.json()["id"]

        # Set B as primary
        resp = client.patch(
            f"/api/v1/productos/{prod_id}/imagenes/{img_b_id}/primaria",
            headers=headers,
        )
        assert resp.status_code == 200, resp.json()
        assert resp.json()["es_primaria"] is True

        # Verify A is no longer primary
        rows = test_db_session.execute(
            text("SELECT es_primaria FROM product_images WHERE id = :iid"),
            {"iid": img_a_id},
        ).fetchone()
        assert rows[0] == 0  # False in SQLite


class TestLegacyImagen:
    """Legacy POST /{id}/imagen also creates ProductoImagen."""

    def test_legacy_upload_creates_producto_imagen(
        self, client: TestClient, sample_roles, admin_user, test_db_session: Session
    ):
        """Legacy POST /{id}/imagen → also creates ProductoImagen row."""
        headers = _admin_headers(client)
        prod = _create_product(client, headers, test_db_session)
        prod_id = prod["id"]

        file_content = b"\xff\xd8\xff\xe0" + b"\x00" * 100
        resp = client.post(
            f"/api/v1/productos/{prod_id}/imagen",
            files={"file": ("legacy.jpg", io.BytesIO(file_content), "image/jpeg")},
            headers=headers,
        )
        assert resp.status_code == 200

        # Verify ProductoImagen row was created
        count = test_db_session.execute(
            text(
                "SELECT COUNT(*) FROM product_images "
                "WHERE producto_id = :pid AND eliminado_en IS NULL"
            ),
            {"pid": prod_id},
        ).scalar()
        assert count == 1


# ===========================================================================
# categoria_ids required validation
# ===========================================================================


class TestCategoriaIdsRequired:
    """categoria_ids is now REQUIRED in ProductoCreate."""

    def test_create_with_valid_categoria_ids(
        self, client: TestClient, test_db_session: Session, sample_roles, admin_user
    ):
        """POST with valid categoria_ids → 201."""
        headers = _admin_headers(client)
        cat = _create_categoria_direct(test_db_session, "Pizzas")

        resp = client.post(
            "/api/v1/productos",
            json={"nombre": "Pizza", "precio": "12.00", "categoria_ids": [cat["id"]]},
            headers=headers,
        )
        assert resp.status_code == 201

    def test_create_missing_categoria_ids_returns_422(
        self, client: TestClient, sample_roles, admin_user
    ):
        """POST without categoria_ids → 422 (Pydantic required field)."""
        headers = _admin_headers(client)
        resp = client.post(
            "/api/v1/productos",
            json={"nombre": "Pizza", "precio": "12.00"},
            headers=headers,
        )
        assert resp.status_code == 422

    def test_create_empty_categoria_ids_returns_422(
        self, client: TestClient, test_db_session: Session, sample_roles, admin_user
    ):
        """POST with categoria_ids: [] → 422 (min_length validation)."""
        headers = _admin_headers(client)
        resp = client.post(
            "/api/v1/productos",
            json={"nombre": "Pizza", "precio": "12.00", "categoria_ids": []},
            headers=headers,
        )
        assert resp.status_code == 422
        # Pydantic min_length=1 validation or service BusinessRuleError
        body = resp.json()
        detail = body.get("detail", "")
        errors = body.get("errors", [])
        error_msg = detail + " " + " ".join(e.get("message", "") for e in errors)
        assert "al menos una categoría" in error_msg or "at least 1" in error_msg


# ===========================================================================
# ingrediente_ids on creation
# ===========================================================================


class TestIngredienteIdsOnCreate:
    """ingrediente_ids support in ProductoCreate."""

    def test_create_with_ingredients(
        self, client: TestClient, test_db_session: Session, sample_roles, admin_user
    ):
        """POST with ingrediente_ids → 201 + ingredients associated."""
        headers = _admin_headers(client)
        cat = _create_categoria_direct(test_db_session, "Pizzas")
        ing1 = _create_ingrediente_direct(test_db_session, "Tomate")
        ing2 = _create_ingrediente_direct(test_db_session, "Queso")

        resp = client.post(
            "/api/v1/productos",
            json={
                "nombre": "Pizza Esp",
                "precio": "15.00",
                "categoria_ids": [cat["id"]],
                "ingrediente_ids": [
                    {"ingrediente_id": ing1["id"], "es_removible": True},
                    {"ingrediente_id": ing2["id"], "es_removible": False},
                ],
            },
            headers=headers,
        )
        assert resp.status_code == 201, resp.json()
        prod_id = resp.json()["id"]

        # Verify ingredients associated
        resp_detail = client.get(f"/api/v1/productos/{prod_id}")
        assert resp_detail.status_code == 200
        ings = resp_detail.json()["ingredientes"]
        ing_ids = {i["id"] for i in ings}
        assert ing1["id"] in ing_ids
        assert ing2["id"] in ing_ids

    def test_create_with_nonexistent_ingredient_returns_422(
        self, client: TestClient, test_db_session: Session, sample_roles, admin_user
    ):
        """POST with non-existent ingredient → 422 + no product created."""
        headers = _admin_headers(client)
        cat = _create_categoria_direct(test_db_session, "Pizzas")

        before_count = test_db_session.execute(
            text("SELECT COUNT(*) FROM products WHERE eliminado_en IS NULL")
        ).scalar()

        resp = client.post(
            "/api/v1/productos",
            json={
                "nombre": "Pizza Bad",
                "precio": "15.00",
                "categoria_ids": [cat["id"]],
                "ingrediente_ids": [{"ingrediente_id": 99999, "es_removible": True}],
            },
            headers=headers,
        )
        assert resp.status_code == 422

        after_count = test_db_session.execute(
            text("SELECT COUNT(*) FROM products WHERE eliminado_en IS NULL")
        ).scalar()
        assert after_count == before_count  # No product created (rollback)

    def test_create_without_ingredients(
        self, client: TestClient, test_db_session: Session, sample_roles, admin_user
    ):
        """POST without ingrediente_ids → 201, no ingredients."""
        headers = _admin_headers(client)
        cat = _create_categoria_direct(test_db_session, "Pizzas")

        resp = client.post(
            "/api/v1/productos",
            json={
                "nombre": "Pizza Simple",
                "precio": "10.00",
                "categoria_ids": [cat["id"]],
            },
            headers=headers,
        )
        assert resp.status_code == 201
        prod_id = resp.json()["id"]

        resp_detail = client.get(f"/api/v1/productos/{prod_id}")
        assert resp_detail.json()["ingredientes"] == []
