"""
ProductRepository — data access for the products domain.

Extends BaseRepository[Producto] with specialised methods:
- find_by_nombre: reserved for future uniqueness checks (no UNIQUE constraint).
- list_paginated_with_filters: public catalog query with 4 combinable filters.
- get_with_associations: eager-loads categorias + ingredientes for detail view.
- list_ingredientes: returns (Ingrediente, es_removible) pairs from pivot.
- replace_categorias: bulk replace with soft-delete + reactivation logic.
- add_ingrediente: insert / reactivate pivot row with es_removible flag.
- remove_ingrediente: soft-delete pivot row.

Rules:
- NO commit calls here — the router decides when to commit (D6).
- Use literal(...) from sqlalchemy, NOT func.literal(...) — historical bug.
- Use func.lower() + .like() for case-insensitive search (SQLite compat, D10).
"""

from __future__ import annotations

from datetime import datetime, timezone

from sqlalchemy import and_, exists, func, select
from sqlalchemy.orm import Session, selectinload

from backend.features.catalog.models import Categoria, Ingrediente
from backend.features.products.models import (
    Producto,
    ProductoCategoria,
    ProductoIngrediente,
)
from backend.shared.exceptions import ConflictError
from backend.shared.repository import BaseRepository


class ProductRepository(BaseRepository[Producto]):
    """Repository for Producto with catalog query and M:N pivot support."""

    def __init__(self, session: Session) -> None:
        super().__init__(session, Producto)

    # ── Uniqueness check (reserved for future use) ────────────────────────

    def find_by_nombre(self, nombre: str) -> Producto | None:
        """Find an active product by exact nombre match.

        Reserved for future use — there is no UNIQUE constraint on
        products.nombre so this does NOT validate uniqueness. The service
        does NOT invoke this method in the current create/update flow.

        Args:
            nombre: Exact name to match.

        Returns:
            Active Producto or None.
        """
        query = self._get_base_query().where(Producto.nombre == nombre)
        return self.session.execute(query).scalar_one_or_none()

    # ── Paginated catalog listing with filters ────────────────────────────

    def list_paginated_with_filters(
        self,
        *,
        skip: int,
        limit: int,
        categoria_id: int | None = None,
        search: str | None = None,
        disponible: bool | None = None,
        excluir_alergenos: bool = False,
    ) -> tuple[list[Producto], int]:
        """Return (items, total) for a paginated, filtered product listing.

        Filter logic (all applied with AND):
        1. categoria_id  — INNER JOIN on product_categories pivot.
        2. search        — LOWER(nombre) LIKE LOWER('%term%') for SQLite compat.
        3. disponible    — exact boolean match.
        4. excluir_alergenos — NOT EXISTS subquery: excludes products with at
           least one non-removable allergen ingredient.

        Args:
            skip: Row offset (page - 1) * limit.
            limit: Max rows to return.
            categoria_id: If not None, only products in this category.
            search: If not None / empty, case-insensitive substring match.
            disponible: If not None, filter by exact value.
            excluir_alergenos: If True, exclude products with non-removable
                allergens per RN-CA08.

        Returns:
            Tuple of (items, total_matching_count).
        """
        base = self._get_base_query()  # already filters eliminado_en IS NULL

        # 1. Category filter — INNER JOIN on active pivot rows only
        if categoria_id is not None:
            base = base.join(
                ProductoCategoria,
                and_(
                    ProductoCategoria.product_id == Producto.id,
                    ProductoCategoria.eliminado_en.is_(None),
                    ProductoCategoria.category_id == categoria_id,
                ),
            )

        # 2. Search filter — LOWER + LIKE (no ILIKE — SQLite incompatible)
        if search is not None:
            stripped = search.strip()
            if stripped:
                pattern = f"%{stripped}%"
                base = base.where(
                    func.lower(Producto.nombre).like(func.lower(pattern))
                )

        # 3. Availability filter
        if disponible is not None:
            base = base.where(Producto.disponible == disponible)

        # 4. Allergen exclusion — NOT EXISTS subquery
        if excluir_alergenos:
            pi = ProductoIngrediente.__table__.alias("pi")
            ing = Ingrediente.__table__.alias("i")
            allergen_subq = (
                select(pi.c.product_id)
                .join(ing, pi.c.ingredient_id == ing.c.id)
                .where(
                    pi.c.product_id == Producto.id,
                    pi.c.eliminado_en.is_(None),
                    ing.c.eliminado_en.is_(None),
                    ing.c.es_alergeno.is_(True),
                    pi.c.es_removible.is_(False),
                )
            )
            base = base.where(~exists(allergen_subq))

        # Count query
        count_query = select(func.count()).select_from(base.subquery())
        total: int = self.session.execute(count_query).scalar() or 0

        # Items query
        items_query = (
            base.order_by(Producto.nombre).offset(skip).limit(limit)
        )
        items = list(self.session.execute(items_query).scalars().all())

        return items, total

    # ── Detail with eager-loaded associations ─────────────────────────────

    def get_with_associations(self, id: int) -> Producto | None:
        """Fetch a product with eagerly loaded categorias and ingredientes.

        Uses selectinload to avoid N+1. Note: the M:N relationship does NOT
        expose es_removible from the pivot — use list_ingredientes for that.

        Args:
            id: Product primary key.

        Returns:
            Producto with .categorias populated, or None.
        """
        query = (
            self._get_base_query()
            .where(Producto.id == id)
            .options(
                selectinload(Producto.categorias),
                selectinload(Producto.ingredientes),
            )
        )
        return self.session.execute(query).scalar_one_or_none()

    # ── Ingredient associations with es_removible flag ────────────────────

    def list_ingredientes(
        self, producto_id: int
    ) -> list[tuple[Ingrediente, bool]]:
        """Return (Ingrediente, es_removible) pairs for a product.

        Filters both pivot and ingredient soft-deletes.

        Args:
            producto_id: Product primary key.

        Returns:
            List of (Ingrediente, es_removible bool) tuples.
        """
        query = (
            select(Ingrediente, ProductoIngrediente.es_removible)
            .join(
                ProductoIngrediente,
                ProductoIngrediente.ingredient_id == Ingrediente.id,
            )
            .where(
                ProductoIngrediente.product_id == producto_id,
                ProductoIngrediente.eliminado_en.is_(None),
                Ingrediente.eliminado_en.is_(None),
            )
        )
        result = self.session.execute(query).all()
        return [(row[0], row[1]) for row in result]

    # ── M:N category bulk replace ─────────────────────────────────────────

    def replace_categorias(
        self, producto_id: int, categoria_ids: list[int]
    ) -> None:
        """Replace all category associations for a product atomically.

        Algorithm:
        1. Load all existing pivot rows (active + soft-deleted).
        2. Soft-delete active rows whose category_id is NOT in the new set.
        3. For each category_id in the new set:
           - Already active → no-op.
           - Soft-deleted → reactivate.
           - Absent → INSERT.

        Callers must validate that every id in categoria_ids exists in the
        categories table BEFORE calling this method. This method assumes
        valid input and does NOT commit.

        Args:
            producto_id: Product primary key.
            categoria_ids: Full desired set of category IDs (may be empty).
        """
        now = datetime.now(timezone.utc)

        # Load all rows regardless of soft-delete status
        existing: list[ProductoCategoria] = list(
            self.session.execute(
                select(ProductoCategoria).where(
                    ProductoCategoria.product_id == producto_id
                )
            )
            .scalars()
            .all()
        )

        existing_by_cat: dict[int, ProductoCategoria] = {
            row.category_id: row for row in existing
        }
        new_ids_set = set(categoria_ids)

        # Step 2: soft-delete active rows not in the new set
        for row in existing:
            if row.category_id not in new_ids_set and row.eliminado_en is None:
                row.eliminado_en = now
                row.actualizado_en = now

        # Step 3: upsert each requested category
        for cat_id in categoria_ids:
            if cat_id in existing_by_cat:
                row = existing_by_cat[cat_id]
                if row.eliminado_en is not None:
                    # Reactivate soft-deleted row
                    row.eliminado_en = None
                    row.actualizado_en = now
                # Already active → no-op
            else:
                # New association
                new_row = ProductoCategoria(
                    product_id=producto_id, category_id=cat_id
                )
                self.session.add(new_row)

        self.session.flush()

    # ── M:N ingredient add (with soft-delete reactivation) ───────────────

    def add_ingrediente(
        self,
        producto_id: int,
        ingrediente_id: int,
        es_removible: bool,
    ) -> ProductoIngrediente:
        """Associate an ingredient with a product.

        - Active pivot row → raise ConflictError (409).
        - Soft-deleted row → reactivate with new es_removible value.
        - No row → INSERT.

        Args:
            producto_id: Product primary key.
            ingrediente_id: Ingredient primary key.
            es_removible: Whether the ingredient can be removed on order.

        Returns:
            The ProductoIngrediente pivot row (new or reactivated).

        Raises:
            ConflictError: If the association already exists and is active.
        """
        existing: ProductoIngrediente | None = self.session.execute(
            select(ProductoIngrediente).where(
                ProductoIngrediente.product_id == producto_id,
                ProductoIngrediente.ingredient_id == ingrediente_id,
            )
        ).scalar_one_or_none()

        if existing is not None:
            if existing.eliminado_en is None:
                raise ConflictError("El ingrediente ya está asociado al producto")
            # Reactivate soft-deleted row
            existing.eliminado_en = None
            existing.es_removible = es_removible
            existing.actualizado_en = datetime.now(timezone.utc)
            self.session.flush()
            return existing

        # New association
        pi = ProductoIngrediente(
            product_id=producto_id,
            ingredient_id=ingrediente_id,
            es_removible=es_removible,
        )
        self.session.add(pi)
        self.session.flush()
        return pi

    # ── M:N ingredient remove (soft delete on pivot) ─────────────────────

    def remove_ingrediente(
        self, producto_id: int, ingrediente_id: int
    ) -> bool:
        """Soft-delete an active ingredient association.

        Args:
            producto_id: Product primary key.
            ingrediente_id: Ingredient primary key.

        Returns:
            True if the pivot row was soft-deleted.
            False if no active association exists (router returns 404).
        """
        row: ProductoIngrediente | None = self.session.execute(
            select(ProductoIngrediente).where(
                ProductoIngrediente.product_id == producto_id,
                ProductoIngrediente.ingredient_id == ingrediente_id,
                ProductoIngrediente.eliminado_en.is_(None),
            )
        ).scalar_one_or_none()

        if row is None:
            return False

        row.eliminado_en = datetime.now(timezone.utc)
        self.session.flush()
        return True
