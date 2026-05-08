"""
CategoryRepository — data access for the hierarchical category tree.

Extends BaseRepository[Categoria] with specialised methods:
- get_tree_cte: recursive CTE returning flat rows for Python-side nesting.
- would_create_cycle: CTE-based cycle detection before reparenting.
- find_by_nombre_y_padre: name uniqueness check within a level.
- has_active_children / has_active_products: guards for soft delete.
"""

from __future__ import annotations

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from backend.features.catalog.models import Categoria
from backend.features.products.models import Producto, ProductoCategoria
from backend.shared.repository import BaseRepository

from .schemas import CategoryFlatRow


class CategoryRepository(BaseRepository[Categoria]):
    """Repository for Categoria with hierarchical query support."""

    def __init__(self, session: Session) -> None:
        super().__init__(session, Categoria)

    # ── Uniqueness check ──────────────────────────────────────────────────

    def find_by_nombre_y_padre(
        self, nombre: str, padre_id: int | None
    ) -> Categoria | None:
        """Find an active category by name and parent level.

        Args:
            nombre: Category name to search for.
            padre_id: Parent ID (None = root level).

        Returns:
            The matching category or None.
        """
        query = self._get_base_query().where(Categoria.nombre == nombre)

        if padre_id is None:
            query = query.where(Categoria.padre_id.is_(None))
        else:
            query = query.where(Categoria.padre_id == padre_id)

        return self.session.execute(query).scalar_one_or_none()

    # ── Guard checks for delete ───────────────────────────────────────────

    def has_active_children(self, categoria_id: int) -> bool:
        """Check if a category has non-deleted subcategories.

        Args:
            categoria_id: Category ID to check.

        Returns:
            True if at least one active child exists.
        """
        query = (
            select(func.count())
            .select_from(Categoria)
            .where(
                Categoria.padre_id == categoria_id,
                Categoria.eliminado_en.is_(None),
            )
        )
        count = self.session.execute(query).scalar() or 0
        return count > 0

    def has_active_products(self, categoria_id: int) -> bool:
        """Check if any active product is associated with this category.

        Joins product_categories → products and filters by
        products.eliminado_en IS NULL.

        Args:
            categoria_id: Category ID to check.

        Returns:
            True if at least one active product is associated.
        """
        query = (
            select(func.count())
            .select_from(ProductoCategoria)
            .join(
                Producto,
                Producto.id == ProductoCategoria.product_id,
            )
            .where(
                ProductoCategoria.category_id == categoria_id,
                Producto.eliminado_en.is_(None),
            )
        )
        count = self.session.execute(query).scalar() or 0
        return count > 0

    # ── Cycle detection ───────────────────────────────────────────────────

    def would_create_cycle(
        self, categoria_id: int, new_padre_id: int | None
    ) -> bool:
        """Check if setting ``new_padre_id`` would create a cycle.

        Walks up the parent chain from ``new_padre_id`` using a recursive
        CTE. If ``categoria_id`` is found in the ancestors → cycle.

        Special cases:
        - ``new_padre_id is None`` → root promotion, never a cycle → False.
        - ``new_padre_id == categoria_id`` → self-parent → True.

        Args:
            categoria_id: The category being moved.
            new_padre_id: The proposed new parent.

        Returns:
            True if reparenting would create a cycle.
        """
        if new_padre_id is None:
            return False
        if new_padre_id == categoria_id:
            return True

        cat = Categoria.__table__

        # Anchor: start from the proposed new parent
        anchor = (
            select(cat.c.id, cat.c.padre_id)
            .where(cat.c.id == new_padre_id)
            .where(cat.c.eliminado_en.is_(None))
            .cte("ancestors", recursive=True)
        )

        # Recursive part: walk up the chain
        parent_alias = anchor.alias("a")
        child_alias = cat.alias("c")
        recursive = (
            select(child_alias.c.id, child_alias.c.padre_id)
            .join(
                parent_alias,
                child_alias.c.id == parent_alias.c.padre_id,
            )
            .where(child_alias.c.eliminado_en.is_(None))
        )

        cte = anchor.union_all(recursive)

        result = self.session.execute(
            select(func.count()).select_from(cte).where(cte.c.id == categoria_id)
        ).scalar()
        return (result or 0) > 0

    # ── Recursive tree ────────────────────────────────────────────────────

    def get_tree_cte(self) -> list[CategoryFlatRow]:
        """Fetch the full category tree as flat rows via a recursive CTE.

        The anchor picks root categories (``padre_id IS NULL``, not deleted).
        The recursive part joins children by ``padre_id``.
        Results are ordered deterministically by depth then name.

        Returns:
            List of CategoryFlatRow tuples for Python-side nesting.
        """
        cat = Categoria.__table__

        # Anchor: root nodes (no parent), only non-deleted
        anchor = (
            select(
                cat.c.id,
                cat.c.nombre,
                cat.c.padre_id,
                func.literal(0).label("depth"),
            )
            .where(cat.c.padre_id.is_(None))
            .where(cat.c.eliminado_en.is_(None))
            .cte("category_tree", recursive=True)
        )

        # Recursive part: children join on parent.id = child.padre_id
        parent = anchor.alias("ct")
        child = cat.alias("c")
        recursive = (
            select(
                child.c.id,
                child.c.nombre,
                child.c.padre_id,
                (parent.c.depth + 1).label("depth"),
            )
            .join(child, child.c.padre_id == parent.c.id)
            .where(child.c.eliminado_en.is_(None))
        )

        cte = anchor.union_all(recursive)

        rows = self.session.execute(
            select(
                cte.c.id,
                cte.c.nombre,
                cte.c.padre_id,
                cte.c.depth,
            ).order_by(cte.c.depth, cte.c.nombre)
        ).all()

        return [CategoryFlatRow(id=r.id, nombre=r.nombre, padre_id=r.padre_id, depth=r.depth) for r in rows]
