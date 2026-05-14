"""
IngredientRepository — data access for the ingredients table.

Extends BaseRepository[Ingrediente] with two specialised methods:
- find_by_nombre: name uniqueness check (includes soft-deleted rows).
- list_paginated: paged listing with optional es_alergeno filter.

All other operations (create, read, update, delete, list_all) are
inherited from BaseRepository without overrides.

Important: find_by_nombre does NOT filter by eliminado_en — the DB
constraint uq_ingredients_nombre covers the entire table regardless of
soft-delete status, so the service must replicate that check.
"""

from __future__ import annotations

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from features.catalog.models import Ingrediente
from shared.repository import BaseRepository


class IngredientRepository(BaseRepository[Ingrediente]):
    """Repository for Ingrediente with pagination and uniqueness support."""

    def __init__(self, session: Session) -> None:
        super().__init__(session, Ingrediente)

    # ── Uniqueness check ──────────────────────────────────────────────────

    def find_by_nombre(self, nombre: str) -> Ingrediente | None:
        """Find any ingredient by name, including soft-deleted rows.

        This method intentionally does NOT filter by eliminado_en because
        the database constraint uq_ingredients_nombre is on the full table.
        The service uses the result to raise ConflictError before any INSERT
        reaches the DB, preventing IntegrityError from leaking as 500.

        Args:
            nombre: Exact name to search for.

        Returns:
            The matching Ingrediente (active or soft-deleted), or None.
        """
        query = select(Ingrediente).where(Ingrediente.nombre == nombre)
        return self.session.execute(query).scalar_one_or_none()

    # ── Paginated listing ─────────────────────────────────────────────────

    def list_paginated(
        self,
        *,
        skip: int,
        limit: int,
        es_alergeno: bool | None = None,
        es_removible: bool | None = None,
        incluir_eliminados: bool = False,
    ) -> tuple[list[Ingrediente], int]:
        """Return (items, total) for a paginated list of ingredients.

        By default only non-deleted ingredients are returned (eliminado_en IS
        NULL). When ``incluir_eliminados`` is True, soft-deleted ingredients
        are also included. The service MUST verify ADMIN role before setting
        this flag (RN-CA10, D1).

        Optionally filters by es_alergeno and/or es_removible when provided.

        Args:
            skip: Number of rows to skip (offset), computed by the service
                as ``(page - 1) * limit``.
            limit: Maximum number of rows to return.
            es_alergeno: When not None, restrict to ingredients matching
                this allergen flag.
            es_removible: When not None, restrict to ingredients matching
                this removable flag.
            incluir_eliminados: When True, include soft-deleted ingredients.
                The service is responsible for enforcing ADMIN-only access.

        Returns:
            Tuple of (items_list, total_count) where total_count reflects
            the filtered count across all pages.
        """
        if incluir_eliminados:
            base = select(Ingrediente)
        else:
            base = self._get_base_query()  # already filters eliminado_en IS NULL

        if es_alergeno is not None:
            base = base.where(Ingrediente.es_alergeno == es_alergeno)

        if es_removible is not None:
            base = base.where(Ingrediente.es_removible == es_removible)

        # Separate count query reusing the same filters
        count_query = select(func.count()).select_from(base.subquery())
        total = self.session.execute(count_query).scalar() or 0

        # Paginated items ordered alphabetically by name
        items_query = base.order_by(Ingrediente.nombre).offset(skip).limit(limit)
        items = self.session.execute(items_query).scalars().all()

        return list(items), total
