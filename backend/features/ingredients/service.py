"""
IngredientService — business logic for ingredient CRUD.

Orchestrates validation rules via UnitOfWork + IngredientRepository:
- Name uniqueness (includes soft-deleted rows — constraint is table-wide).
- Partial updates using model_dump(exclude_unset=True) to preserve
  es_alergeno when the client only sends nombre, and vice-versa.
- Soft delete without guards (D4 in design.md — US-014 is satisfied by
  the soft delete itself).

Each public method opens its own UnitOfWork context. Commit is performed
by ``__exit__`` on clean exit. The router never calls uow.commit().
"""

from __future__ import annotations

from backend.features.catalog.models import Ingrediente
from backend.features.ingredients.repository import IngredientRepository
from backend.features.ingredients.schemas import IngredienteCreate, IngredienteUpdate
from backend.shared.exceptions import BusinessRuleError, ConflictError, NotFoundError
from backend.shared.unit_of_work import UnitOfWork


class IngredientService:
    """Business logic for the ingredient domain."""

    def __init__(self) -> None:
        pass

    # ── Create ────────────────────────────────────────────────────────────

    def create(self, payload: IngredienteCreate) -> Ingrediente:
        """Create a new ingredient.

        Validates:
        - Nombre is not blank after strip.
        - No existing ingredient (active or soft-deleted) has the same name,
          matching the DB UNIQUE constraint uq_ingredients_nombre.

        Args:
            payload: Creation data.

        Returns:
            The newly created Ingrediente entity.

        Raises:
            BusinessRuleError: If nombre is blank after strip.
            ConflictError: If any ingredient (active or deleted) with that
                name already exists.
        """
        with UnitOfWork() as uow:
            uow.register_repository("ingredientes", IngredientRepository(uow.session))
            repo: IngredientRepository = uow.ingredientes  # type: ignore[assignment]

            nombre = payload.nombre.strip()
            if not nombre:
                raise BusinessRuleError("El nombre del ingrediente no puede estar vacío")

            existing = repo.find_by_nombre(nombre)
            if existing is not None:
                raise ConflictError("Ya existe un ingrediente con ese nombre")

            return repo.create(nombre=nombre, es_alergeno=payload.es_alergeno)

    # ── Read ──────────────────────────────────────────────────────────────

    def get_by_id(self, ingrediente_id: int) -> Ingrediente:
        """Fetch a single active ingredient by ID.

        Args:
            ingrediente_id: Primary key of the ingredient.

        Returns:
            The Ingrediente entity.

        Raises:
            NotFoundError: If the ingredient does not exist or is
                soft-deleted (BaseRepository.read filters eliminado_en).
        """
        with UnitOfWork() as uow:
            uow.register_repository("ingredientes", IngredientRepository(uow.session))
            repo: IngredientRepository = uow.ingredientes  # type: ignore[assignment]

            current = repo.read(ingrediente_id)
            if current is None:
                raise NotFoundError("Ingrediente no encontrado")
            return current

    # ── List ──────────────────────────────────────────────────────────────

    def list_paginated(
        self,
        *,
        page: int,
        limit: int,
        es_alergeno: bool | None,
    ) -> tuple[list[Ingrediente], int]:
        """Return a paginated list of active ingredients.

        Args:
            page: 1-based page number (converted to skip internally).
            limit: Maximum items per page.
            es_alergeno: Optional filter; None means no filter.

        Returns:
            Tuple of (items, total) where total is the filtered count
            across all pages.
        """
        with UnitOfWork() as uow:
            uow.register_repository("ingredientes", IngredientRepository(uow.session))
            repo: IngredientRepository = uow.ingredientes  # type: ignore[assignment]

            skip = (page - 1) * limit
            return repo.list_paginated(skip=skip, limit=limit, es_alergeno=es_alergeno)

    # ── Update ────────────────────────────────────────────────────────────

    def update(self, ingrediente_id: int, payload: IngredienteUpdate) -> Ingrediente:
        """Partially update an existing ingredient.

        Uses ``model_dump(exclude_unset=True)`` to preserve ``es_alergeno``
        when the client only sends ``nombre``, and vice-versa. Without
        exclude_unset, ``es_alergeno`` would silently overwrite to its
        Pydantic default (None) when omitted from the request.

        Validates:
        - Ingredient exists (not soft-deleted).
        - If nombre changes, no other ingredient (active or deleted) has
          the same name.
        - Trimmed nombre is not blank.

        Args:
            ingrediente_id: ID of the ingredient to update.
            payload: Fields to update (omitted fields are preserved).

        Returns:
            The updated Ingrediente entity.

        Raises:
            NotFoundError: If the ingredient does not exist.
            BusinessRuleError: If the trimmed nombre is blank.
            ConflictError: If another ingredient with the new name exists.
        """
        with UnitOfWork() as uow:
            uow.register_repository("ingredientes", IngredientRepository(uow.session))
            repo: IngredientRepository = uow.ingredientes  # type: ignore[assignment]

            current = repo.read(ingrediente_id)
            if current is None:
                raise NotFoundError("Ingrediente no encontrado")

            data = payload.model_dump(exclude_unset=True)

            if "nombre" in data:
                nombre = data["nombre"].strip()
                if not nombre:
                    raise BusinessRuleError(
                        "El nombre del ingrediente no puede estar vacío"
                    )
                data["nombre"] = nombre

                # Only check uniqueness if the name actually changed
                if nombre != current.nombre:
                    existing = repo.find_by_nombre(nombre)
                    if existing is not None and existing.id != ingrediente_id:
                        raise ConflictError("Ya existe un ingrediente con ese nombre")

            return repo.update(ingrediente_id, **data)

    # ── Delete (soft) ─────────────────────────────────────────────────────

    def delete(self, ingrediente_id: int) -> None:
        """Soft-delete an ingredient.

        No guards are applied (D4 in design.md): US-014 says the ingredient
        should "remain in existing products but stop appearing for new
        associations", which the soft delete achieves naturally — the
        BaseRepository list filters excludes it from future lookups while
        product_ingredients rows remain intact.

        Args:
            ingrediente_id: ID of the ingredient to soft-delete.

        Raises:
            NotFoundError: If the ingredient does not exist or is already
                soft-deleted.
        """
        with UnitOfWork() as uow:
            uow.register_repository("ingredientes", IngredientRepository(uow.session))
            repo: IngredientRepository = uow.ingredientes  # type: ignore[assignment]

            current = repo.read(ingrediente_id)
            if current is None:
                raise NotFoundError("Ingrediente no encontrado")

            repo.delete(ingrediente_id)
