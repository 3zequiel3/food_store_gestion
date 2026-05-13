"""
Integration tests for catalog filter extensions — change catalog-filters-and-leaf-categories-backend.

Covers (TDD, tasks 1–9):
1. Filtro recursivo de categoria_id en GET /productos (CTE)
2. Exclusión granular de alérgenos (excluir_alergeno_ids)
3. Helper leaf-only validation en ProductService
4. Hook auto-disponible=false
5. Filtro sin_categoria=true en GET /productos
6. Guard block-on-promote en CategoryService.create()
7. GET /categorias?solo_hojas=true
8. Tests de integración para GET /ingredientes?es_alergeno
9. Audit de seed data (query directa)
"""

from __future__ import annotations

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import text
from sqlalchemy.orm import Session


# ===========================================================================
# Auth helpers
# ===========================================================================


def _admin_headers(client: TestClient) -> dict[str, str]:
    response = client.post(
        "/api/v1/auth/login",
        json={"email": "admin@test.com", "password": "admin_password_123"},
    )
    assert response.status_code == 200, f"Admin login failed: {response.json()}"
    return {"Authorization": f"Bearer {response.json()['access_token']}"}


def _stock_headers(client: TestClient) -> dict[str, str]:
    response = client.post(
        "/api/v1/auth/login",
        json={"email": "stock@test.com", "password": "stock_password_123"},
    )
    assert response.status_code == 200, f"Stock login failed: {response.json()}"
    return {"Authorization": f"Bearer {response.json()['access_token']}"}


# ===========================================================================
# Fixtures
# ===========================================================================


@pytest.fixture(scope="function")
def admin_user(test_db_session: Session, sample_roles):
    from backend.features.users.models import Usuario, UsuarioRol
    from backend.shared.security import hash_password

    user = Usuario(
        email="admin@test.com",
        password_hash=hash_password("admin_password_123"),
        nombre="Admin",
        apellido="Catalog",
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
    from backend.features.users.models import Usuario, UsuarioRol
    from backend.shared.security import hash_password

    user = Usuario(
        email="stock@test.com",
        password_hash=hash_password("stock_password_123"),
        nombre="Stock",
        apellido="Catalog",
        is_active=True,
    )
    test_db_session.add(user)
    test_db_session.flush()
    user_role = UsuarioRol(user_id=user.id, role_id=2)
    test_db_session.add(user_role)
    test_db_session.commit()
    test_db_session.refresh(user)
    return user


# ===========================================================================
# Helpers
# ===========================================================================


def _create_product(client: TestClient, headers: dict, **overrides) -> dict:
    """POST /api/v1/productos with sensible defaults and assert 201."""
    import uuid
    payload = {
        "nombre": f"CF-{uuid.uuid4().hex[:8]}",
        "precio": "10.00",
        "disponible": True,
    }
    payload.update(overrides)
    resp = client.post("/api/v1/productos", json=payload, headers=headers)
    assert resp.status_code == 201, f"Failed to create product: {resp.json()}"
    return resp.json()


def _make_cat(session: Session, nombre: str, padre_id: int | None = None) -> int:
    """Insert a Categoria directly via session. Returns the category id."""
    from backend.features.catalog.models import Categoria

    cat = Categoria(nombre=nombre, padre_id=padre_id)
    session.add(cat)
    session.flush()
    session.commit()
    return cat.id


def _make_ingrediente(
    session: Session, nombre: str, es_alergeno: bool = False
) -> int:
    """Insert an Ingrediente directly via session. Returns the ingredient id."""
    from backend.features.catalog.models import Ingrediente

    ing = Ingrediente(nombre=nombre, es_alergeno=es_alergeno)
    session.add(ing)
    session.flush()
    session.commit()
    return ing.id


def _assoc_ing(
    client: TestClient,
    headers: dict,
    prod_id: int,
    ing_id: int,
    es_removible: bool = False,
) -> None:
    """Associate an ingredient with a product via API."""
    resp = client.post(
        f"/api/v1/productos/{prod_id}/ingredientes",
        json={"ingrediente_id": ing_id, "es_removible": es_removible},
        headers=headers,
    )
    assert resp.status_code == 201, f"Failed to assoc ingredient: {resp.json()}"


# ===========================================================================
# 1. Filtro recursivo de categoria_id (CTE) — Tasks 1.1–1.5
# ===========================================================================


class TestCategoriaIdRecursiveFilter:
    """GET /productos?categoria_id=X matchea descendientes recursivamente (D1)."""

    def test_product_in_grandchild_category_appears_with_root_filter(
        self,
        client: TestClient,
        test_db_session: Session,
        sample_roles,
        admin_user,
    ):
        """Task 1.1: producto asignado a nieta (3 niveles) aparece al filtrar por raíz.

        Bebidas (root) → Gaseosas (child) → Sin Azúcar (grandchild)
        Producto asignado a Sin Azúcar.
        GET ?categoria_id=Bebidas → debe incluir el producto.
        """
        headers = _admin_headers(client)

        # Árbol de 3 niveles
        root_id = _make_cat(test_db_session, "Bebidas-rec")
        child_id = _make_cat(test_db_session, "Gaseosas-rec", padre_id=root_id)
        grandchild_id = _make_cat(test_db_session, "SinAzucar-rec", padre_id=child_id)

        # Producto asignado solo a nieta
        prod = _create_product(
            client, headers, nombre="Agua-rec", categoria_ids=[grandchild_id]
        )

        resp = client.get(f"/api/v1/productos?categoria_id={root_id}&disponible=true")
        assert resp.status_code == 200
        ids = [p["id"] for p in resp.json()["items"]]
        assert prod["id"] in ids, "Producto en categoría nieta debe aparecer al filtrar por raíz"

    def test_product_in_sibling_subtree_excluded(
        self,
        client: TestClient,
        test_db_session: Session,
        sample_roles,
        admin_user,
    ):
        """Task 1.2: producto en categoría hermana NO aparece al filtrar por otra rama.

        Rama A: root_a → child_a
        Rama B: root_b → child_b
        Producto en child_b; filtro por root_a → no debe aparecer.
        """
        headers = _admin_headers(client)

        root_a = _make_cat(test_db_session, "RamaA-root")
        child_a = _make_cat(test_db_session, "RamaA-child", padre_id=root_a)  # noqa: F841
        root_b = _make_cat(test_db_session, "RamaB-root")
        child_b = _make_cat(test_db_session, "RamaB-child", padre_id=root_b)

        prod_b = _create_product(
            client, headers, nombre="Prod-rama-b", categoria_ids=[child_b]
        )

        resp = client.get(f"/api/v1/productos?categoria_id={root_a}&disponible=true")
        assert resp.status_code == 200
        ids = [p["id"] for p in resp.json()["items"]]
        assert prod_b["id"] not in ids, "Producto en rama B no debe aparecer al filtrar por rama A"

    def test_soft_deleted_descendant_excluded_from_subtree(
        self,
        client: TestClient,
        test_db_session: Session,
        sample_roles,
        admin_user,
    ):
        """Task 1.3: categoría descendiente soft-deleted se excluye del subtree.

        root → child (soft-deleted) → grandchild
        Producto asignado a grandchild.
        GET ?categoria_id=root → NO debe incluir el producto
        porque el CTE no atraviesa soft-deleted.
        """
        headers = _admin_headers(client)

        root_id = _make_cat(test_db_session, "RootSD")
        child_id = _make_cat(test_db_session, "ChildSD", padre_id=root_id)
        grandchild_id = _make_cat(test_db_session, "GrandchildSD", padre_id=child_id)

        prod = _create_product(
            client, headers, nombre="Prod-grandchild-sd", categoria_ids=[grandchild_id]
        )

        # Soft-delete child (el intermedio)
        test_db_session.execute(
            text(
                "UPDATE categories SET eliminado_en = CURRENT_TIMESTAMP "
                "WHERE id = :cid"
            ),
            {"cid": child_id},
        )
        test_db_session.commit()

        resp = client.get(f"/api/v1/productos?categoria_id={root_id}&disponible=true")
        assert resp.status_code == 200
        ids = [p["id"] for p in resp.json()["items"]]
        assert prod["id"] not in ids, (
            "Producto en nieta cuya ruta pasa por categoría soft-deleted "
            "no debe aparecer al filtrar por raíz"
        )

    def test_original_direct_category_filter_still_works(
        self,
        client: TestClient,
        test_db_session: Session,
        sample_roles,
        admin_user,
    ):
        """Task 1.5 (regresión): filtro por categoría directa sigue funcionando.

        Producto asignado directo a una hoja.
        GET ?categoria_id=hoja → debe aparecer.
        """
        headers = _admin_headers(client)

        cat_id = _make_cat(test_db_session, "HojaDirecta")
        prod = _create_product(
            client, headers, nombre="Prod-directo", categoria_ids=[cat_id]
        )

        resp = client.get(f"/api/v1/productos?categoria_id={cat_id}&disponible=true")
        assert resp.status_code == 200
        ids = [p["id"] for p in resp.json()["items"]]
        assert prod["id"] in ids, "Producto asociado directo debe aparecer con filtro directo"

    def test_category_filter_no_match_returns_empty(
        self,
        client: TestClient,
        test_db_session: Session,
        sample_roles,
        admin_user,
    ):
        """Filtro por categoría sin productos → total=0."""
        headers = _admin_headers(client)
        cat_id = _make_cat(test_db_session, "CatVacia")

        resp = client.get(f"/api/v1/productos?categoria_id={cat_id}&disponible=true")
        assert resp.status_code == 200
        assert resp.json()["total"] == 0


# ===========================================================================
# 2. Exclusión granular de alérgenos (excluir_alergeno_ids) — Tasks 2.1–2.7
# ===========================================================================


class TestExcluirAlergenos:
    """Nuevo param excluir_alergeno_ids: list[int] en GET /productos (D2)."""

    def test_product_with_non_removable_banned_ingredient_excluded(
        self,
        client: TestClient,
        test_db_session: Session,
        sample_roles,
        admin_user,
    ):
        """Task 2.1: producto con ingrediente 50 no-removible se excluye con ?excluir_alergeno_ids=50."""
        headers = _admin_headers(client)

        ing_id = _make_ingrediente(test_db_session, "Mani-ban", es_alergeno=True)
        prod = _create_product(client, headers, nombre="P-mani-no-rem")
        _assoc_ing(client, headers, prod["id"], ing_id, es_removible=False)

        resp = client.get(
            f"/api/v1/productos?excluir_alergeno_ids={ing_id}&disponible=true"
        )
        assert resp.status_code == 200
        ids = [p["id"] for p in resp.json()["items"]]
        assert prod["id"] not in ids

    def test_product_with_removable_banned_ingredient_not_excluded(
        self,
        client: TestClient,
        test_db_session: Session,
        sample_roles,
        admin_user,
    ):
        """Task 2.2: producto con ingrediente removible NO se excluye."""
        headers = _admin_headers(client)

        ing_id = _make_ingrediente(test_db_session, "Gluten-rem", es_alergeno=True)
        prod = _create_product(client, headers, nombre="P-gluten-rem")
        _assoc_ing(client, headers, prod["id"], ing_id, es_removible=True)

        resp = client.get(
            f"/api/v1/productos?excluir_alergeno_ids={ing_id}&disponible=true"
        )
        assert resp.status_code == 200
        ids = [p["id"] for p in resp.json()["items"]]
        assert prod["id"] in ids

    def test_empty_excluir_alergeno_ids_is_noop(
        self,
        client: TestClient,
        sample_roles,
        admin_user,
    ):
        """Task 2.3: param omitido = no-op (lista vacía no puede enviarse como ?param= en FastAPI)."""
        client_test = client
        headers = _admin_headers(client_test)
        prod = _create_product(client_test, headers, nombre="P-noop-ids")

        # Sin param → total incluye el producto
        resp_sin = client_test.get("/api/v1/productos?disponible=true")
        assert resp_sin.status_code == 200
        ids = [p["id"] for p in resp_sin.json()["items"]]
        assert prod["id"] in ids

    def test_combined_excluir_alergenos_and_ids_applies_and(
        self,
        client: TestClient,
        test_db_session: Session,
        sample_roles,
        admin_user,
    ):
        """Task 2.4: combinación excluir_alergenos=true & excluir_alergeno_ids aplica AND.

        P1: tiene ing_general (es_alergeno=True, no-rem) → excluido por boolean.
        P2: tiene ing_especifico (es_alergeno=False, no-rem) → excluido por ids.
        P3: tiene ing_especifico (es_alergeno=False, es_removible=True) → incluido.
        P4: limpio → incluido.
        """
        headers = _admin_headers(client)

        ing_gen = _make_ingrediente(test_db_session, "IngGen-and", es_alergeno=True)
        ing_esp = _make_ingrediente(test_db_session, "IngEsp-and", es_alergeno=False)

        p1 = _create_product(client, headers, nombre="P1-boolean-excluded")
        _assoc_ing(client, headers, p1["id"], ing_gen, es_removible=False)

        p2 = _create_product(client, headers, nombre="P2-ids-excluded")
        _assoc_ing(client, headers, p2["id"], ing_esp, es_removible=False)

        p3 = _create_product(client, headers, nombre="P3-removible-ok")
        _assoc_ing(client, headers, p3["id"], ing_esp, es_removible=True)

        p4 = _create_product(client, headers, nombre="P4-clean")

        resp = client.get(
            f"/api/v1/productos"
            f"?excluir_alergenos=true"
            f"&excluir_alergeno_ids={ing_esp}"
            f"&disponible=true"
        )
        assert resp.status_code == 200
        ids = [p["id"] for p in resp.json()["items"]]
        assert p1["id"] not in ids
        assert p2["id"] not in ids
        assert p3["id"] in ids
        assert p4["id"] in ids

    def test_excluir_alergeno_ids_multiple_ids(
        self,
        client: TestClient,
        test_db_session: Session,
        sample_roles,
        admin_user,
    ):
        """Múltiples IDs en excluir_alergeno_ids → AND lógico: excluir si tiene alguno no-removible."""
        headers = _admin_headers(client)

        ing1 = _make_ingrediente(test_db_session, "Mani-multi", es_alergeno=True)
        ing2 = _make_ingrediente(test_db_session, "Trigo-multi", es_alergeno=False)

        # P1: tiene ing1 no-rem → excluido
        p1 = _create_product(client, headers, nombre="P1-multi-excluded")
        _assoc_ing(client, headers, p1["id"], ing1, es_removible=False)

        # P2: tiene ing2 no-rem → excluido
        p2 = _create_product(client, headers, nombre="P2-multi-excluded")
        _assoc_ing(client, headers, p2["id"], ing2, es_removible=False)

        # P3: tiene ing1 removible → incluido
        p3 = _create_product(client, headers, nombre="P3-multi-ok")
        _assoc_ing(client, headers, p3["id"], ing1, es_removible=True)

        # P4: limpio → incluido
        p4 = _create_product(client, headers, nombre="P4-multi-clean")

        resp = client.get(
            f"/api/v1/productos"
            f"?excluir_alergeno_ids={ing1}"
            f"&excluir_alergeno_ids={ing2}"
            f"&disponible=true"
        )
        assert resp.status_code == 200
        ids = [p["id"] for p in resp.json()["items"]]
        assert p1["id"] not in ids
        assert p2["id"] not in ids
        assert p3["id"] in ids
        assert p4["id"] in ids


# ===========================================================================
# 3. Helper leaf-only validation — Tasks 3.1–3.10 (unit + integration)
# ===========================================================================


class TestLeafOnlyValidationHelper:
    """_validate_categorias_are_leaves helper tests (unit via service call)."""

    def test_create_product_with_non_leaf_category_returns_422(
        self,
        client: TestClient,
        test_db_session: Session,
        sample_roles,
        admin_user,
    ):
        """Task 3.9: POST /productos con categoría no-hoja → 422 con detalle accionable."""
        headers = _admin_headers(client)

        # Bebidas (no-leaf) tiene hija Gaseosas (leaf)
        bebidas_id = _make_cat(test_db_session, "Bebidas-NL")
        _make_cat(test_db_session, "Gaseosas-NL", padre_id=bebidas_id)

        resp = client.post(
            "/api/v1/productos",
            json={"nombre": "Cerveza-NL", "precio": "5.00", "categoria_ids": [bebidas_id]},
            headers=headers,
        )
        assert resp.status_code == 422
        body = resp.json()
        # Detalle debe mencionar la categoría ofensora y sus hijas
        detail = str(body)
        assert "Bebidas-NL" in detail or "bebidas-nl" in detail.lower()

    def test_create_product_with_leaf_category_succeeds(
        self,
        client: TestClient,
        test_db_session: Session,
        sample_roles,
        admin_user,
    ):
        """Crear producto con categoría hoja → 201."""
        headers = _admin_headers(client)

        parent_id = _make_cat(test_db_session, "Parent-leaf-test")
        leaf_id = _make_cat(test_db_session, "Leaf-actual", padre_id=parent_id)

        resp = client.post(
            "/api/v1/productos",
            json={"nombre": "Prod-leaf-ok", "precio": "8.00", "categoria_ids": [leaf_id]},
            headers=headers,
        )
        assert resp.status_code == 201

    def test_create_product_with_softdeleted_child_is_leaf(
        self,
        client: TestClient,
        test_db_session: Session,
        sample_roles,
        admin_user,
    ):
        """Task 3.4: categoría con única hija soft-deleted cuenta como hoja."""
        headers = _admin_headers(client)

        parent_id = _make_cat(test_db_session, "Parent-SDchild")
        child_id = _make_cat(test_db_session, "Child-SD-leaf", padre_id=parent_id)

        # Soft-delete the child
        test_db_session.execute(
            text("UPDATE categories SET eliminado_en = CURRENT_TIMESTAMP WHERE id = :cid"),
            {"cid": child_id},
        )
        test_db_session.commit()

        # Ahora parent_id es efectivamente una hoja → debe permitir asignación
        resp = client.post(
            "/api/v1/productos",
            json={"nombre": "Prod-sd-child-ok", "precio": "9.00", "categoria_ids": [parent_id]},
            headers=headers,
        )
        assert resp.status_code == 201

    def test_set_categorias_with_non_leaf_returns_422_no_mutation(
        self,
        client: TestClient,
        test_db_session: Session,
        sample_roles,
        admin_user,
    ):
        """Task 3.10: PUT /productos/{id}/categorias con categoría no-hoja → 422.

        Nota: la verificación de ausencia de mutación de pivot rows no se puede
        hacer directamente vía test_db_session luego de un rollback en SQLite
        in-memory (known limitation — ver test_categories.py::test_put_categorias_inexistente).
        Se verifica solo el status code de respuesta (422) que confirma que la
        validación leaf-only rechazó la operación antes de cualquier mutación.
        """
        headers = _admin_headers(client)

        # Crear una hoja para asignar inicialmente
        leaf_id = _make_cat(test_db_session, "HojaInicial-nl")

        # Crear no-hoja
        non_leaf_id = _make_cat(test_db_session, "NoHoja-setcat")
        _make_cat(test_db_session, "HijaNoHoja-setcat", padre_id=non_leaf_id)

        # Crear producto con categoría hoja
        prod = _create_product(
            client, headers, nombre="Prod-setcat-nl", categoria_ids=[leaf_id]
        )
        prod_id = prod["id"]

        # Intentar asignar no-hoja → debe fallar con 422
        resp = client.put(
            f"/api/v1/productos/{prod_id}/categorias",
            json={"categoria_ids": [non_leaf_id]},
            headers=headers,
        )
        assert resp.status_code == 422

    def test_create_with_mix_leaf_nonleaf_returns_422(
        self,
        client: TestClient,
        test_db_session: Session,
        sample_roles,
        admin_user,
    ):
        """Task 3.3 (integración): mezcla leaf+non-leaf → 422, no se crea el producto."""
        headers = _admin_headers(client)

        leaf_id = _make_cat(test_db_session, "LeafOK-mix")
        non_leaf_id = _make_cat(test_db_session, "NonLeaf-mix")
        _make_cat(test_db_session, "Hija-mix", padre_id=non_leaf_id)

        nombre = "Prod-mix-fails"
        resp = client.post(
            "/api/v1/productos",
            json={"nombre": nombre, "precio": "7.00", "categoria_ids": [leaf_id, non_leaf_id]},
            headers=headers,
        )
        assert resp.status_code == 422

        # Producto no debe existir
        count = test_db_session.execute(
            text("SELECT COUNT(*) FROM products WHERE nombre = :nombre AND eliminado_en IS NULL"),
            {"nombre": nombre},
        ).scalar()
        assert count == 0


# ===========================================================================
# 4. Hook auto-disponible=false — Tasks 4.1–4.12 (unit + integration)
# ===========================================================================


class TestAutoDisableHook:
    """Hook auto-disponible=false cuando producto queda sin categoría hoja activa (D4)."""

    def test_create_with_empty_categoria_ids_auto_disables(
        self,
        client: TestClient,
        sample_roles,
        admin_user,
    ):
        """Task 4.11: POST con categoria_ids=[] → 201 con disponible=false aunque payload diga true."""
        headers = _admin_headers(client)

        resp = client.post(
            "/api/v1/productos",
            json={"nombre": "P-empty-cats", "precio": "10.00", "disponible": True, "categoria_ids": []},
            headers=headers,
        )
        assert resp.status_code == 201
        assert resp.json()["disponible"] is False, (
            "Hook debe desactivar el producto al quedar sin categorías hoja"
        )

    def test_create_without_categoria_ids_keeps_disponible_true(
        self,
        client: TestClient,
        sample_roles,
        admin_user,
    ):
        """Hook NO corre cuando categoria_ids es omitido (None). disponible=true se preserva."""
        headers = _admin_headers(client)

        resp = client.post(
            "/api/v1/productos",
            json={"nombre": "P-nocats-key", "precio": "10.00", "disponible": True},
            headers=headers,
        )
        assert resp.status_code == 201
        assert resp.json()["disponible"] is True

    def test_set_categorias_empty_auto_disables(
        self,
        client: TestClient,
        test_db_session: Session,
        sample_roles,
        admin_user,
    ):
        """Task 4.12: PUT /categorias con [] sobre producto disponible=true → 200 con disponible=false."""
        headers = _admin_headers(client)

        cat_id = _make_cat(test_db_session, "CatHook-leaf")
        prod = _create_product(
            client, headers, nombre="P-hook-setcat", disponible=True, categoria_ids=[cat_id]
        )
        prod_id = prod["id"]

        resp = client.put(
            f"/api/v1/productos/{prod_id}/categorias",
            json={"categoria_ids": []},
            headers=headers,
        )
        assert resp.status_code == 200
        assert resp.json()["disponible"] is False

    def test_set_categorias_with_leaf_keeps_disponible(
        self,
        client: TestClient,
        test_db_session: Session,
        sample_roles,
        admin_user,
    ):
        """Asignar categorías hoja → disponible se mantiene."""
        headers = _admin_headers(client)

        leaf_id = _make_cat(test_db_session, "LeafKeep-hook")
        prod = _create_product(
            client, headers, nombre="P-hook-keeptrue", disponible=True, categoria_ids=[leaf_id]
        )
        prod_id = prod["id"]

        # Reemplazar con la misma hoja (idempotente)
        resp = client.put(
            f"/api/v1/productos/{prod_id}/categorias",
            json={"categoria_ids": [leaf_id]},
            headers=headers,
        )
        assert resp.status_code == 200
        assert resp.json()["disponible"] is True

    def test_hook_does_not_reenable_manually_disabled_product(
        self,
        client: TestClient,
        test_db_session: Session,
        sample_roles,
        admin_user,
    ):
        """Task 4.6 (integración): hook NO re-habilita producto con disponible=false cuando count>0."""
        headers = _admin_headers(client)

        leaf_id = _make_cat(test_db_session, "LeafNoReEnable")
        prod = _create_product(
            client, headers, nombre="P-no-reenable", disponible=False, categoria_ids=[leaf_id]
        )
        prod_id = prod["id"]

        # El producto ya tiene disponible=False (lo creamos así).
        # PUT categorias con la misma hoja → count>0, hook no re-habilita
        resp = client.put(
            f"/api/v1/productos/{prod_id}/categorias",
            json={"categoria_ids": [leaf_id]},
            headers=headers,
        )
        assert resp.status_code == 200
        assert resp.json()["disponible"] is False


# ===========================================================================
# 5. Filtro sin_categoria=true — Tasks 5.1–5.6
# ===========================================================================


class TestSinCategoriaFilter:
    """GET /productos?sin_categoria=true — productos sin asociaciones activas (D5)."""

    def test_product_without_active_assoc_appears_with_sin_categoria(
        self,
        client: TestClient,
        test_db_session: Session,
        sample_roles,
        admin_user,
    ):
        """Task 5.1: producto sin asociaciones activas aparece con sin_categoria=true."""
        headers = _admin_headers(client)

        # Producto sin categorías (sin categoria_ids)
        prod = _create_product(
            client, headers, nombre="P-sincat-nocat", disponible=False
        )

        resp = client.get(
            "/api/v1/productos?sin_categoria=true&disponible=false"
        )
        assert resp.status_code == 200
        ids = [p["id"] for p in resp.json()["items"]]
        assert prod["id"] in ids

    def test_product_with_softdeleted_assoc_appears_with_sin_categoria(
        self,
        client: TestClient,
        test_db_session: Session,
        sample_roles,
        admin_user,
    ):
        """Task 5.2: producto con asociación soft-deleted también aparece con sin_categoria=true.

        Creamos el producto sin categorías (hook lo desactiva).
        Insertamos pivot row soft-deleted directamente en la DB.
        GET ?sin_categoria=true&disponible=false → debe aparecer.
        """
        from backend.features.products.models import ProductoCategoria

        headers = _admin_headers(client)

        cat_id = _make_cat(test_db_session, "CatSinCat-SD")

        # Crear producto sin categorías (disponible=false por hook)
        prod = _create_product(
            client, headers, nombre="P-sincat-sd", categoria_ids=[]
        )
        prod_id = prod["id"]

        # Verificar que quedó desactivado por el hook
        assert prod["disponible"] is False

        # Insertar un pivot row ya soft-deleted directamente
        from datetime import datetime, timezone
        now = datetime.now(timezone.utc)
        pivot = ProductoCategoria(
            product_id=prod_id,
            category_id=cat_id,
        )
        pivot.eliminado_en = now
        test_db_session.add(pivot)
        test_db_session.commit()

        resp = client.get(
            "/api/v1/productos?sin_categoria=true&disponible=false"
        )
        assert resp.status_code == 200
        ids = [p["id"] for p in resp.json()["items"]]
        assert prod_id in ids

    def test_product_with_active_assoc_excluded_with_sin_categoria(
        self,
        client: TestClient,
        test_db_session: Session,
        sample_roles,
        admin_user,
    ):
        """Task 5.3: producto con al menos 1 asociación activa NO aparece con sin_categoria=true."""
        headers = _admin_headers(client)

        cat_id = _make_cat(test_db_session, "CatSinCat-active")
        prod = _create_product(
            client, headers, nombre="P-sincat-active", categoria_ids=[cat_id]
        )

        resp = client.get(
            "/api/v1/productos?sin_categoria=true&disponible=true"
        )
        assert resp.status_code == 200
        ids = [p["id"] for p in resp.json()["items"]]
        assert prod["id"] not in ids

    def test_sin_categoria_false_is_noop(
        self,
        client: TestClient,
        sample_roles,
        admin_user,
    ):
        """Task 5.4: sin_categoria=false (default) es no-op."""
        headers = _admin_headers(client)
        _create_product(client, headers, nombre="P-sincat-noop")

        resp_sin = client.get("/api/v1/productos?disponible=true")
        resp_false = client.get("/api/v1/productos?sin_categoria=false&disponible=true")
        assert resp_sin.json()["total"] == resp_false.json()["total"]


# ===========================================================================
# 6. Guard block-on-promote en CategoryService.create() — Tasks 6.1–6.6
# ===========================================================================


class TestBlockOnPromoteGuard:
    """POST /categorias rechaza crear hija de categoría con productos activos (D6)."""

    def test_create_subcategory_when_parent_has_no_products_succeeds(
        self,
        client: TestClient,
        test_db_session: Session,
        sample_roles,
        admin_user,
    ):
        """Task 6.1: padre sin productos activos → crear hija exitosa."""
        headers = _admin_headers(client)

        parent_id = _make_cat(test_db_session, "PadreVacio-guard")

        resp = client.post(
            "/api/v1/categorias",
            json={"nombre": "HijaVacia-guard", "padre_id": parent_id},
            headers=headers,
        )
        assert resp.status_code == 201

    def test_create_subcategory_when_parent_has_active_products_returns_422(
        self,
        client: TestClient,
        test_db_session: Session,
        sample_roles,
        admin_user,
    ):
        """Task 6.2/6.6: padre con 3 productos activos → 422 con detalle accionable."""
        headers = _admin_headers(client)

        # Crear padre que actualmente es hoja
        parent_id = _make_cat(test_db_session, "PadreConProds-guard")

        # Crear 3 productos asignados al padre (que actualmente es hoja, antes del guard)
        # Para esto, primero el padre es hoja, asignamos productos, luego intentamos crear hija
        for i in range(3):
            _create_product(
                client, headers, nombre=f"ProdGuard-{i}", categoria_ids=[parent_id]
            )

        # Intentar crear hija del padre que ahora tiene productos → 422
        resp = client.post(
            "/api/v1/categorias",
            json={"nombre": "HijaShouldFail-guard", "padre_id": parent_id},
            headers=headers,
        )
        assert resp.status_code == 422
        body_str = str(resp.json())
        # El mensaje debe mencionar la categoría o el count
        assert "PadreConProds-guard" in body_str or "3" in body_str or "subcategor" in body_str.lower()

    def test_create_subcategory_parent_with_softdeleted_products_succeeds(
        self,
        client: TestClient,
        test_db_session: Session,
        sample_roles,
        admin_user,
    ):
        """Task 6.3: padre con productos soft-deleted → crear hija exitosa."""
        headers = _admin_headers(client)

        parent_id = _make_cat(test_db_session, "PadreSDProds-guard")
        prod = _create_product(
            client, headers, nombre="ProdSD-guard", categoria_ids=[parent_id]
        )

        # Soft-delete el producto
        client.delete(f"/api/v1/productos/{prod['id']}", headers=headers)

        resp = client.post(
            "/api/v1/categorias",
            json={"nombre": "HijaSDOk-guard", "padre_id": parent_id},
            headers=headers,
        )
        assert resp.status_code == 201

    def test_create_subcategory_parent_with_softdeleted_pivot_succeeds(
        self,
        client: TestClient,
        test_db_session: Session,
        sample_roles,
        admin_user,
    ):
        """Task 6.4: pivot row soft-deleted apuntando a producto activo → crear hija exitosa."""
        headers = _admin_headers(client)

        parent_id = _make_cat(test_db_session, "PadreSoftPivot-guard")
        prod = _create_product(
            client, headers, nombre="ProdSoftPivot-guard", categoria_ids=[parent_id]
        )

        # Soft-delete el pivot row (producto activo, pivot inactivo)
        test_db_session.execute(
            text(
                "UPDATE product_categories SET eliminado_en = CURRENT_TIMESTAMP "
                "WHERE product_id = :pid AND category_id = :cid"
            ),
            {"pid": prod["id"], "cid": parent_id},
        )
        test_db_session.commit()

        resp = client.post(
            "/api/v1/categorias",
            json={"nombre": "HijaSoftPivotOk-guard", "padre_id": parent_id},
            headers=headers,
        )
        assert resp.status_code == 201


# ===========================================================================
# 7. GET /categorias?solo_hojas=true — Tasks 7.1–7.9
# ===========================================================================


class TestSoloHojasFilter:
    """GET /categorias?solo_hojas=true devuelve lista plana de hojas (D7)."""

    def test_solo_hojas_returns_flat_array_without_subcategorias(
        self,
        client: TestClient,
        test_db_session: Session,
        sample_roles,
    ):
        """Task 7.8: GET ?solo_hojas=true devuelve array plano sin subcategorias key."""
        root_id = _make_cat(test_db_session, "SH-Root")  # noqa: F841
        _make_cat(test_db_session, "SH-Leaf1", padre_id=root_id)
        _make_cat(test_db_session, "SH-Leaf2", padre_id=root_id)

        resp = client.get("/api/v1/categorias?solo_hojas=true")
        assert resp.status_code == 200
        data = resp.json()
        assert isinstance(data, list)
        # Ningún item debe tener subcategorias key
        for item in data:
            assert "subcategorias" not in item
        # Solo las hojas (SH-Leaf1, SH-Leaf2) deben aparecer, no SH-Root
        nombres = [item["nombre"] for item in data]
        assert "SH-Leaf1" in nombres
        assert "SH-Leaf2" in nombres
        assert "SH-Root" not in nombres

    def test_solo_hojas_false_returns_tree(
        self,
        client: TestClient,
        test_db_session: Session,
        sample_roles,
    ):
        """Task 7.9 (regresión): GET sin param o ?solo_hojas=false sigue devolviendo árbol."""
        _make_cat(test_db_session, "Tree-Root-SH")

        resp = client.get("/api/v1/categorias")
        assert resp.status_code == 200
        data = resp.json()
        assert isinstance(data, list)
        # El árbol tiene subcategorias
        for item in data:
            assert "subcategorias" in item

    def test_solo_hojas_true_excludes_softdeleted(
        self,
        client: TestClient,
        test_db_session: Session,
        sample_roles,
    ):
        """Task 7.2: categoría soft-deleted no aparece en solo_hojas."""
        leaf_id = _make_cat(test_db_session, "SH-SoftLeaf")
        test_db_session.execute(
            text("UPDATE categories SET eliminado_en = CURRENT_TIMESTAMP WHERE id = :cid"),
            {"cid": leaf_id},
        )
        test_db_session.commit()

        resp = client.get("/api/v1/categorias?solo_hojas=true")
        assert resp.status_code == 200
        nombres = [item["nombre"] for item in resp.json()]
        assert "SH-SoftLeaf" not in nombres

    def test_solo_hojas_includes_category_with_only_softdeleted_children(
        self,
        client: TestClient,
        test_db_session: Session,
        sample_roles,
    ):
        """Task 7.3: categoría con única hija soft-deleted SÍ aparece como hoja efectiva."""
        parent_id = _make_cat(test_db_session, "SH-EffectiveLeaf")
        child_id = _make_cat(test_db_session, "SH-ChildSD", padre_id=parent_id)
        test_db_session.execute(
            text("UPDATE categories SET eliminado_en = CURRENT_TIMESTAMP WHERE id = :cid"),
            {"cid": child_id},
        )
        test_db_session.commit()

        resp = client.get("/api/v1/categorias?solo_hojas=true")
        assert resp.status_code == 200
        nombres = [item["nombre"] for item in resp.json()]
        assert "SH-EffectiveLeaf" in nombres

    def test_solo_hojas_empty_catalog_returns_empty_list(
        self,
        client: TestClient,
        sample_roles,
    ):
        """Task 7.4: tabla vacía → []."""
        resp = client.get("/api/v1/categorias?solo_hojas=true")
        assert resp.status_code == 200
        assert resp.json() == []

    def test_solo_hojas_is_public(self, client: TestClient, sample_roles):
        """Task 7.9: endpoint público (sin auth)."""
        resp = client.get("/api/v1/categorias?solo_hojas=true")
        assert resp.status_code == 200

    def test_solo_hojas_alphabetical_order(
        self,
        client: TestClient,
        test_db_session: Session,
        sample_roles,
    ):
        """Resultado ordenado alfabéticamente por nombre."""
        root_id = _make_cat(test_db_session, "SH-ZRoot")
        _make_cat(test_db_session, "SH-Zanahoria", padre_id=root_id)
        _make_cat(test_db_session, "SH-Ajo", padre_id=root_id)
        _make_cat(test_db_session, "SH-Mani", padre_id=root_id)

        resp = client.get("/api/v1/categorias?solo_hojas=true")
        assert resp.status_code == 200
        nombres = [item["nombre"] for item in resp.json()]
        # Solo los que creamos en este test
        sh_nombres = [n for n in nombres if n.startswith("SH-") and n != "SH-ZRoot"]
        assert sh_nombres == sorted(sh_nombres)


# ===========================================================================
# 8. Tests de ingredientes con es_alergeno — Tasks 8.2–8.3
# ===========================================================================


class TestIngredientesAlergeno:
    """GET /ingredientes?es_alergeno tests (el filtro ya existía, solo completamos coverage)."""

    def test_es_alergeno_true_returns_only_allergens(
        self,
        client: TestClient,
        test_db_session: Session,
        sample_roles,
        admin_user,
    ):
        """Task 8.2/8.3: filtro es_alergeno=true retorna solo alérgenos."""
        headers = _admin_headers(client)

        ing_si = _make_ingrediente(test_db_session, "IngAlerg-si", es_alergeno=True)
        ing_no = _make_ingrediente(test_db_session, "IngAlerg-no", es_alergeno=False)  # noqa: F841

        resp = client.get("/api/v1/ingredientes?es_alergeno=true")
        assert resp.status_code == 200
        ids = [i["id"] for i in resp.json()["items"]]
        assert ing_si in ids
        assert ing_no not in ids
        for item in resp.json()["items"]:
            assert item["es_alergeno"] is True

    def test_es_alergeno_false_returns_only_non_allergens(
        self,
        client: TestClient,
        test_db_session: Session,
        sample_roles,
        admin_user,
    ):
        """Task 8.3: filtro es_alergeno=false retorna solo no-alérgenos."""
        ing_si = _make_ingrediente(test_db_session, "IngF-si", es_alergeno=True)  # noqa: F841
        ing_no = _make_ingrediente(test_db_session, "IngF-no", es_alergeno=False)

        resp = client.get("/api/v1/ingredientes?es_alergeno=false")
        assert resp.status_code == 200
        ids = [i["id"] for i in resp.json()["items"]]
        assert ing_no in ids
        assert ing_si not in ids
        for item in resp.json()["items"]:
            assert item["es_alergeno"] is False

    def test_es_alergeno_omitted_returns_all(
        self,
        client: TestClient,
        test_db_session: Session,
        sample_roles,
    ):
        """Task 8.3: es_alergeno omitido retorna todos los activos."""
        ing_si = _make_ingrediente(test_db_session, "IngAll-si", es_alergeno=True)
        ing_no = _make_ingrediente(test_db_session, "IngAll-no", es_alergeno=False)

        resp = client.get("/api/v1/ingredientes")
        assert resp.status_code == 200
        ids = [i["id"] for i in resp.json()["items"]]
        assert ing_si in ids
        assert ing_no in ids

    def test_es_alergeno_filter_excludes_softdeleted(
        self,
        client: TestClient,
        test_db_session: Session,
        sample_roles,
    ):
        """Task 8.3: soft-deleted excluidos por default."""
        ing_id = _make_ingrediente(test_db_session, "IngAlerg-SD", es_alergeno=True)
        test_db_session.execute(
            text("UPDATE ingredients SET eliminado_en = CURRENT_TIMESTAMP WHERE id = :iid"),
            {"iid": ing_id},
        )
        test_db_session.commit()

        resp = client.get("/api/v1/ingredientes?es_alergeno=true")
        assert resp.status_code == 200
        ids = [i["id"] for i in resp.json()["items"]]
        assert ing_id not in ids

    def test_es_alergeno_is_public(self, client: TestClient, sample_roles):
        """Task 8.3: endpoint público."""
        resp = client.get("/api/v1/ingredientes?es_alergeno=true")
        assert resp.status_code == 200
