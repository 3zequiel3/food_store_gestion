"""
ProductRepository — data access for the products domain.

Extends BaseRepository[Producto] with specialised methods:
- find_by_nombre: reserved for future uniqueness checks (no UNIQUE constraint).
- list_paginated_with_filters: public catalog query with combinable filters.
  New in catalog-filters change: categoria_id uses recursive CTE (D1),
  excluir_alergeno_ids list filter (D2), sin_categoria boolean filter (D5).
- get_with_associations: eager-loads categorias + ingredientes for detail view.
- list_ingredientes: returns (Ingrediente, es_removible) pairs from pivot.
- replace_categorias: bulk replace with soft-delete + reactivation logic.
- add_ingrediente: insert / reactivate pivot row with es_removible flag.
- remove_ingrediente: soft-delete pivot row.
- count_leaf_active_categories: count active leaf-category associations (D4).

Rules:
- NO commit calls here — the router decides when to commit (D6).
- Use literal(...) from sqlalchemy, NOT func.literal(...) — historical bug.
- Use func.lower() + .like() for case-insensitive search (SQLite compat, D10).
"""

from __future__ import annotations

from datetime import datetime, timezone

from sqlalchemy import and_, exists, func, literal, select
from sqlalchemy.orm import Session, selectinload

from features.catalog.models import Categoria, Ingrediente
from features.products.models import (
    Producto,
    ProductoCategoria,
    ProductoIngrediente,
)
from shared.exceptions import ConflictError
from shared.repository import BaseRepository


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
        excluir_alergeno_ids: list[int] | None = None,
        sin_categoria: bool = False,
        incluir_eliminados: bool = False,
    ) -> tuple[list[Producto], int]:
        """Return (items, total) for a paginated, filtered product listing.

        Filter logic (all applied with AND):
        1. incluir_eliminados — if False (default), only active products
           (eliminado_en IS NULL) are included; if True, all products are
           included regardless of soft-delete status. Only ADMIN may set this
           to True — the service enforces the role check.
        2. categoria_id  — Recursive CTE that walks descendants (D1).
           The anchor starts at categoria_id and the recursive part follows
           padre_id links, filtering eliminado_en IS NULL on both sides.
           Products are then INNER JOINed via active product_categories rows.
        3. search        — LOWER(nombre) LIKE LOWER('%term%') for SQLite compat.
        4. disponible    — exact boolean match.
        5. excluir_alergenos — NOT EXISTS subquery: excludes products with at
           least one non-removable allergen ingredient (RN-CA08).
        6. excluir_alergeno_ids — NOT EXISTS subquery filtered by ingredient ID
           list; es_removible=False required (D2). Empty/None = no-op.
        7. sin_categoria — NOT EXISTS on product_categories; true = only
           products with zero active category associations (D5).

        Args:
            skip: Row offset (page - 1) * limit.
            limit: Max rows to return.
            categoria_id: If not None, only products in this category or any
                active descendant (resolved via recursive CTE).
            search: If not None / empty, case-insensitive substring match.
            disponible: If not None, filter by exact value.
            excluir_alergenos: If True, exclude products with non-removable
                allergens per RN-CA08.
            excluir_alergeno_ids: If non-empty, exclude products that have at
                least one active non-removable ingredient in this list.
            sin_categoria: If True, return only products with zero active
                category associations.
            incluir_eliminados: If True, include soft-deleted products.
                The service MUST verify ADMIN role before setting this True.

        Returns:
            Tuple of (items, total_matching_count).
        """
        if incluir_eliminados:
            # Skip soft-delete filter — include all products
            base = select(Producto)
        else:
            base = self._get_base_query()  # already filters eliminado_en IS NULL

        # 1. Category filter — recursive CTE for descendant matching (D1)
        if categoria_id is not None:
            cat = Categoria.__table__

            # Anchor: the requested category itself (must be active)
            anchor = (
                select(cat.c.id)
                .where(cat.c.id == categoria_id)
                .where(cat.c.eliminado_en.is_(None))
                .cte("category_subtree", recursive=True)
            )

            # Recursive part: walk down through padre_id, skipping soft-deleted
            parent_alias = anchor.alias("cs")
            child_alias = cat.alias("c")
            recursive = (
                select(child_alias.c.id)
                .join(parent_alias, child_alias.c.padre_id == parent_alias.c.id)
                .where(child_alias.c.eliminado_en.is_(None))
            )

            cte = anchor.union_all(recursive)

            # INNER JOIN to product_categories restricted to the CTE subtree
            base = base.join(
                ProductoCategoria,
                and_(
                    ProductoCategoria.product_id == Producto.id,
                    ProductoCategoria.eliminado_en.is_(None),
                    ProductoCategoria.category_id.in_(select(cte.c.id)),
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

        # 4. Allergen exclusion (boolean) — NOT EXISTS subquery
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

        # 5. Allergen exclusion by specific IDs (D2) — NOT EXISTS subquery
        if excluir_alergeno_ids:
            pi2 = ProductoIngrediente.__table__.alias("pi2")
            ban_subq = (
                select(pi2.c.product_id)
                .where(
                    pi2.c.product_id == Producto.id,
                    pi2.c.eliminado_en.is_(None),
                    pi2.c.es_removible.is_(False),
                    pi2.c.ingredient_id.in_(excluir_alergeno_ids),
                )
            )
            base = base.where(~exists(ban_subq))

        # 6. Sin-categoria filter (D5) — NOT EXISTS on product_categories
        if sin_categoria:
            pc = ProductoCategoria.__table__.alias("pc_sc")
            no_cat_subq = (
                select(pc.c.product_id)
                .where(
                    pc.c.product_id == Producto.id,
                    pc.c.eliminado_en.is_(None),
                )
            )
            base = base.where(~exists(no_cat_subq))

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

    # ── Leaf-category count for auto-disable hook ────────────────────────

    def count_leaf_active_categories(self, product_id: int) -> int:
        """Count active leaf-category associations for a product.

        A "leaf" category has zero non-deleted children.
        Uses a NOT EXISTS antijoin against the categories self-ref (D4).

        Args:
            product_id: Product primary key.

        Returns:
            Count of active leaf-category associations (>= 0).
        """
        cat = Categoria.__table__
        cat_inner = cat.alias("child")

        # Subquery: categories associated with the product via active pivot rows
        assoc_subq = (
            select(ProductoCategoria.category_id)
            .where(
                ProductoCategoria.product_id == product_id,
                ProductoCategoria.eliminado_en.is_(None),
            )
        )

        # Count categories in the set that have zero active children
        # (i.e., NOT EXISTS a non-deleted child with padre_id == category.id)
        leaf_count_q = (
            select(func.count())
            .select_from(cat)
            .where(
                cat.c.id.in_(assoc_subq),
                cat.c.eliminado_en.is_(None),
                ~exists(
                    select(literal(1))
                    .select_from(cat_inner)
                    .where(
                        cat_inner.c.padre_id == cat.c.id,
                        cat_inner.c.eliminado_en.is_(None),
                    )
                ),
            )
        )
        return self.session.execute(leaf_count_q).scalar() or 0

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
