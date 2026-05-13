"""
Unit tests for catalog-filters-and-leaf-categories-backend.

Covers:
- ProductService._validate_categorias_are_leaves (tasks 3.1–3.6)
- ProductRepository.count_leaf_active_categories (tasks 4.1–4.3)
- ProductService._auto_disable_if_no_leaf_categoria (tasks 4.4–4.6)
- CategoryRepository.list_leaf_categories (tasks 7.1–7.4)
- CategoryService.list_leaves (implied by 7.6)

Uses SQLite in-memory via test_db_session fixture (autouse via conftest).
"""

from __future__ import annotations

import logging
from datetime import datetime, timezone

import pytest
from sqlalchemy.orm import Session


# ===========================================================================
# Helpers to create test data directly (repo-level, no API)
# ===========================================================================


def _make_cat(session: Session, nombre: str, padre_id: int | None = None) -> int:
    """Insert Categoria, return id."""
    from backend.features.catalog.models import Categoria

    cat = Categoria(nombre=nombre, padre_id=padre_id)
    session.add(cat)
    session.flush()
    return cat.id


def _make_producto(session: Session, nombre: str = "Prod", disponible: bool = True) -> int:
    """Insert Producto, return id."""
    from decimal import Decimal
    from backend.features.products.models import Producto

    p = Producto(nombre=nombre, precio=Decimal("10.00"), disponible=disponible)
    session.add(p)
    session.flush()
    return p.id


def _assoc_cat(session: Session, product_id: int, category_id: int) -> None:
    """Insert active ProductoCategoria pivot row."""
    from backend.features.products.models import ProductoCategoria

    pc = ProductoCategoria(product_id=product_id, category_id=category_id)
    session.add(pc)
    session.flush()


def _softdelete_cat(session: Session, category_id: int) -> None:
    """Soft-delete a Categoria."""
    from sqlalchemy import text
    session.execute(
        text("UPDATE categories SET eliminado_en = CURRENT_TIMESTAMP WHERE id = :cid"),
        {"cid": category_id},
    )
    session.flush()


def _softdelete_pivot(session: Session, product_id: int, category_id: int) -> None:
    """Soft-delete a ProductoCategoria pivot row."""
    from sqlalchemy import text
    session.execute(
        text(
            "UPDATE product_categories SET eliminado_en = CURRENT_TIMESTAMP "
            "WHERE product_id = :pid AND category_id = :cid"
        ),
        {"pid": product_id, "cid": category_id},
    )
    session.flush()


# ===========================================================================
# 3.x _validate_categorias_are_leaves (unit via ProductService internals)
# ===========================================================================


class TestValidateCategoriasAreLeaves:
    """Unit tests for ProductService._validate_categorias_are_leaves."""

    def test_leaf_category_does_not_raise(self, test_db_session: Session):
        """Task 3.1: categoría sin hijas activas → no raisea."""
        from backend.features.products.service import ProductService
        from backend.features.products.repository import ProductRepository

        leaf_id = _make_cat(test_db_session, "Leaf-unit-ok")
        test_db_session.commit()

        svc = ProductService()
        # No debe lanzar excepción
        svc._validate_categorias_are_leaves([leaf_id], test_db_session)

    def test_non_leaf_category_raises_business_rule_error(self, test_db_session: Session):
        """Task 3.2: categoría con hija activa raisea BusinessRuleError con nombre y hijas."""
        from backend.features.products.service import ProductService
        from backend.shared.exceptions import BusinessRuleError

        parent_id = _make_cat(test_db_session, "NonLeaf-unit")
        _make_cat(test_db_session, "HijaNL-unit", padre_id=parent_id)
        test_db_session.commit()

        svc = ProductService()
        with pytest.raises(BusinessRuleError) as exc_info:
            svc._validate_categorias_are_leaves([parent_id], test_db_session)

        error_msg = str(exc_info.value.detail)
        assert "NonLeaf-unit" in error_msg
        assert "HijaNL-unit" in error_msg

    def test_multiple_non_leaf_all_reported(self, test_db_session: Session):
        """Task 3.3: mezcla de leaf + non-leaf → error reporta TODAS las non-leaf."""
        from backend.features.products.service import ProductService
        from backend.shared.exceptions import BusinessRuleError

        leaf_id = _make_cat(test_db_session, "Leaf-multi-ok")
        nl1_id = _make_cat(test_db_session, "NonLeaf1-multi")
        nl2_id = _make_cat(test_db_session, "NonLeaf2-multi")
        _make_cat(test_db_session, "Hija1-multi", padre_id=nl1_id)
        _make_cat(test_db_session, "Hija2-multi", padre_id=nl2_id)
        test_db_session.commit()

        svc = ProductService()
        with pytest.raises(BusinessRuleError) as exc_info:
            svc._validate_categorias_are_leaves([leaf_id, nl1_id, nl2_id], test_db_session)

        error_msg = str(exc_info.value.detail)
        assert "NonLeaf1-multi" in error_msg
        assert "NonLeaf2-multi" in error_msg

    def test_softdeleted_child_does_not_block(self, test_db_session: Session):
        """Task 3.4: hija soft-deleted no bloquea el leaf-check (categoría es hoja efectiva)."""
        from backend.features.products.service import ProductService

        parent_id = _make_cat(test_db_session, "Parent-SDchild-unit")
        child_id = _make_cat(test_db_session, "Child-SD-unit", padre_id=parent_id)
        _softdelete_cat(test_db_session, child_id)
        test_db_session.commit()

        svc = ProductService()
        # No debe lanzar
        svc._validate_categorias_are_leaves([parent_id], test_db_session)

    def test_empty_list_is_noop(self, test_db_session: Session):
        """Task 3.5: lista vacía → no dispara query ni raisea."""
        from backend.features.products.service import ProductService

        svc = ProductService()
        # No debe lanzar excepción
        svc._validate_categorias_are_leaves([], test_db_session)


# ===========================================================================
# 4.x count_leaf_active_categories + _auto_disable_if_no_leaf_categoria
# ===========================================================================


class TestCountLeafActiveCategories:
    """Unit tests for ProductRepository.count_leaf_active_categories."""

    def test_count_zero_when_no_associations(self, test_db_session: Session):
        """Task 4.1: count=0 cuando el producto no tiene asociaciones activas."""
        from backend.features.products.repository import ProductRepository

        prod_id = _make_producto(test_db_session, "ProdNoAssoc-count")
        test_db_session.commit()

        repo = ProductRepository(test_db_session)
        assert repo.count_leaf_active_categories(prod_id) == 0

    def test_count_one_when_associated_with_leaf(self, test_db_session: Session):
        """Task 4.2: count=1 cuando tiene 1 asociación a categoría hoja activa."""
        from backend.features.products.repository import ProductRepository

        prod_id = _make_producto(test_db_session, "ProdLeaf-count")
        leaf_id = _make_cat(test_db_session, "LeafCount-unit")
        _assoc_cat(test_db_session, prod_id, leaf_id)
        test_db_session.commit()

        repo = ProductRepository(test_db_session)
        assert repo.count_leaf_active_categories(prod_id) == 1

    def test_count_zero_when_associated_category_has_children(
        self, test_db_session: Session
    ):
        """count=0 cuando la única asociación es a una no-hoja."""
        from backend.features.products.repository import ProductRepository

        prod_id = _make_producto(test_db_session, "ProdNonLeaf-count")
        parent_id = _make_cat(test_db_session, "ParentNonLeaf-count")
        _make_cat(test_db_session, "ChildNL-count", padre_id=parent_id)
        _assoc_cat(test_db_session, prod_id, parent_id)
        test_db_session.commit()

        repo = ProductRepository(test_db_session)
        assert repo.count_leaf_active_categories(prod_id) == 0

    def test_count_zero_when_only_softdeleted_pivot(self, test_db_session: Session):
        """Task 4.3: count=0 cuando la única asociación tiene pivot soft-deleted."""
        from backend.features.products.repository import ProductRepository

        prod_id = _make_producto(test_db_session, "ProdSDPivot-count")
        leaf_id = _make_cat(test_db_session, "LeafSDPivot-count")
        _assoc_cat(test_db_session, prod_id, leaf_id)
        _softdelete_pivot(test_db_session, prod_id, leaf_id)
        test_db_session.commit()

        repo = ProductRepository(test_db_session)
        assert repo.count_leaf_active_categories(prod_id) == 0


class TestAutoDisableHookUnit:
    """Unit tests for ProductService._auto_disable_if_no_leaf_categoria."""

    def test_hook_disables_product_with_count_zero(
        self, test_db_session: Session, caplog
    ):
        """Task 4.4: count=0 → setea disponible=false y emite log INFO con template exacto.

        Nota: el logger 'backend' tiene propagate=False en logging_config.py, por lo que
        caplog (que intercepta via root logger) no captura esos records directamente.
        Verificamos el estado del producto (la mutación real) y el log vía temporalmente
        habilitando propagation en el logger.
        """
        from backend.features.products.service import ProductService

        prod_id = _make_producto(test_db_session, "HookDisable-unit", disponible=True)
        test_db_session.commit()

        # Temporalmente habilitar propagation para que caplog pueda interceptar
        backend_logger = logging.getLogger("backend")
        original_propagate = backend_logger.propagate
        backend_logger.propagate = True

        svc = ProductService()
        try:
            with caplog.at_level(logging.INFO):
                svc._auto_disable_if_no_leaf_categoria(prod_id, test_db_session)
        finally:
            backend_logger.propagate = original_propagate

        # Verificar que el producto se desactivó
        from backend.features.products.models import Producto
        test_db_session.expire_all()
        prod = test_db_session.get(Producto, prod_id)
        assert prod is not None
        assert prod.disponible is False

        # Verificar log — usar getMessage() que aplica % formatting
        expected_msg = f"Producto {prod_id} desactivado: sin categoría hoja activa"
        assert any(
            expected_msg in record.getMessage() for record in caplog.records
        ), f"Log esperado no encontrado. Records: {[r.getMessage() for r in caplog.records]}"

    def test_hook_noop_with_active_leaf_category(
        self, test_db_session: Session, caplog
    ):
        """Task 4.5: hook con count>0 → no muta ni loguea."""
        from backend.features.products.service import ProductService

        prod_id = _make_producto(test_db_session, "HookNoop-unit", disponible=True)
        leaf_id = _make_cat(test_db_session, "LeafHookNoop")
        _assoc_cat(test_db_session, prod_id, leaf_id)
        test_db_session.commit()

        # Habilitar propagation para caplog
        backend_logger = logging.getLogger("backend")
        original_propagate = backend_logger.propagate
        backend_logger.propagate = True

        svc = ProductService()
        try:
            with caplog.at_level(logging.INFO):
                svc._auto_disable_if_no_leaf_categoria(prod_id, test_db_session)
        finally:
            backend_logger.propagate = original_propagate

        from backend.features.products.models import Producto
        test_db_session.expire_all()
        prod = test_db_session.get(Producto, prod_id)
        assert prod is not None
        assert prod.disponible is True

        # No debe haber log de desactivación
        disable_logs = [
            r for r in caplog.records
            if "desactivado" in r.getMessage()
        ]
        assert len(disable_logs) == 0

    def test_hook_does_not_reenable_product(
        self, test_db_session: Session, caplog
    ):
        """Task 4.6: hook NO re-habilita producto con disponible=false cuando count>0."""
        from backend.features.products.service import ProductService

        prod_id = _make_producto(test_db_session, "HookNoReEnable-unit", disponible=False)
        leaf_id = _make_cat(test_db_session, "LeafNoReEnable-unit")
        _assoc_cat(test_db_session, prod_id, leaf_id)
        test_db_session.commit()

        svc = ProductService()
        svc._auto_disable_if_no_leaf_categoria(prod_id, test_db_session)

        from backend.features.products.models import Producto
        test_db_session.expire_all()
        prod = test_db_session.get(Producto, prod_id)
        assert prod is not None
        assert prod.disponible is False  # Sigue desactivado, no re-habilitado


# ===========================================================================
# 7.x CategoryRepository.list_leaf_categories
# ===========================================================================


class TestListLeafCategories:
    """Unit tests for CategoryRepository.list_leaf_categories."""

    def test_returns_only_leaves(self, test_db_session: Session):
        """Task 7.1: devuelve categorías sin hijas activas."""
        from backend.features.categories.repository import CategoryRepository

        root_id = _make_cat(test_db_session, "LLF-Root")
        leaf1_id = _make_cat(test_db_session, "LLF-Leaf1", padre_id=root_id)  # noqa: F841
        leaf2_id = _make_cat(test_db_session, "LLF-Leaf2", padre_id=root_id)  # noqa: F841
        test_db_session.commit()

        repo = CategoryRepository(test_db_session)
        leaves = repo.list_leaf_categories()
        nombres = [c.nombre for c in leaves]

        assert "LLF-Leaf1" in nombres
        assert "LLF-Leaf2" in nombres
        assert "LLF-Root" not in nombres

    def test_softdeleted_not_returned(self, test_db_session: Session):
        """Task 7.2: categoría soft-deleted no aparece."""
        from backend.features.categories.repository import CategoryRepository

        leaf_id = _make_cat(test_db_session, "LLF-SDLeaf")
        _softdelete_cat(test_db_session, leaf_id)
        test_db_session.commit()

        repo = CategoryRepository(test_db_session)
        leaves = repo.list_leaf_categories()
        nombres = [c.nombre for c in leaves]
        assert "LLF-SDLeaf" not in nombres

    def test_category_with_only_softdeleted_child_is_leaf(
        self, test_db_session: Session
    ):
        """Task 7.3: categoría con única hija soft-deleted SÍ aparece."""
        from backend.features.categories.repository import CategoryRepository

        parent_id = _make_cat(test_db_session, "LLF-EffLeaf")
        child_id = _make_cat(test_db_session, "LLF-ChildSD-unit", padre_id=parent_id)
        _softdelete_cat(test_db_session, child_id)
        test_db_session.commit()

        repo = CategoryRepository(test_db_session)
        leaves = repo.list_leaf_categories()
        nombres = [c.nombre for c in leaves]
        assert "LLF-EffLeaf" in nombres

    def test_empty_table_returns_empty_list(self, test_db_session: Session):
        """Task 7.4: tabla vacía → []."""
        from backend.features.categories.repository import CategoryRepository

        repo = CategoryRepository(test_db_session)
        leaves = repo.list_leaf_categories()
        assert leaves == []

    def test_results_ordered_by_nombre(self, test_db_session: Session):
        """list_leaf_categories devuelve resultados ordenados alfabéticamente."""
        from backend.features.categories.repository import CategoryRepository

        root_id = _make_cat(test_db_session, "LLF-OrderRoot")
        _make_cat(test_db_session, "LLF-Zanahoria", padre_id=root_id)
        _make_cat(test_db_session, "LLF-Ajo", padre_id=root_id)
        _make_cat(test_db_session, "LLF-Mani", padre_id=root_id)
        test_db_session.commit()

        repo = CategoryRepository(test_db_session)
        leaves = repo.list_leaf_categories()
        # Filtrar solo los de este test
        our_leaves = [c for c in leaves if c.nombre.startswith("LLF-") and c.nombre != "LLF-OrderRoot"]
        nombres = [c.nombre for c in our_leaves]
        assert nombres == sorted(nombres)
