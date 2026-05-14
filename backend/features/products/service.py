"""
ProductService — business logic for product CRUD and M:N associations.

Orchestrates:
- Validations (nombre not empty, FK existence for categorías e ingredientes).
- Leaf-only validation for category assignment (_validate_categorias_are_leaves, D3).
- Auto-disable hook when product has zero active leaf categories (_auto_disable_if_no_leaf_categoria, D4).
- Soft delete without cascades (D11 in design.md).
- M:N bulk replace for categories (replace semantics).
- M:N individual add/remove for ingredients (with es_removible flag).
- Partial updates via model_dump(exclude_unset=True).
- Image CRUD operations (upload, URL, delete, reorder, set primary).

Rules:
- Each public method opens its own UnitOfWork context. Commit is performed
  by ``__exit__`` on clean exit. The router never calls uow.commit().
- Import order: Router → Service → UoW → Repository → Model.
- set_categorias validates ALL ids before touching pivot rows (atomicity).
- set_categorias returns the full ProductoDetail (producto, categorias, ingredientes)
  within the same with-block, eliminating the double-read pattern.
"""

from __future__ import annotations

import logging
from typing import Optional

from sqlalchemy import select
from sqlalchemy.orm import Session

from features.catalog.models import Categoria, Ingrediente
from features.categories.repository import CategoryRepository
from features.ingredients.repository import IngredientRepository
from features.products.models import Producto, ProductoImagen, ProductoIngrediente
from features.products.repository import ProductRepository
from features.products.schemas import ProductoCreate, ProductoUpdate
from features.users.models import Usuario
from shared.exceptions import BusinessRuleError, NotFoundError
from shared.unit_of_work import UnitOfWork

logger = logging.getLogger(__name__)


class ProductService:
    """Business logic for the product domain."""

    def __init__(self) -> None:
        pass

    def _register_repos(
        self, uow: UnitOfWork
    ) -> tuple[ProductRepository, CategoryRepository, IngredientRepository]:
        """Register and return the three repositories for this domain."""
        uow.register_repository("productos", ProductRepository(uow.session))
        uow.register_repository("categorias", CategoryRepository(uow.session))
        uow.register_repository("ingredientes", IngredientRepository(uow.session))
        return uow.productos, uow.categorias, uow.ingredientes  # type: ignore[return-value]

    # ── Leaf-only validation helper (D3) ─────────────────────────────────

    def _validate_categorias_are_leaves(
        self, categoria_ids: list[int], session: Session
    ) -> None:
        """Verify every category id in the list refers to a leaf category.

        A leaf category has zero non-deleted children. Uses a single bulk
        query: SELECT padre_id, nombre FROM categories WHERE padre_id IN :ids
        AND eliminado_en IS NULL. If any rows are returned, at least one of the
        requested categories is not a leaf → raises BusinessRuleError with an
        actionable message in Rioplatense Spanish.

        This method DOES NOT commit, flush, or otherwise mutate the session.

        Args:
            categoria_ids: IDs already validated to exist and be active.
            session: Active SQLAlchemy session (same UoW as the caller).

        Raises:
            BusinessRuleError: If any id references a non-leaf category.
        """
        if not categoria_ids:
            return

        # Single bulk query: find children of any of the requested categories
        rows = session.execute(
            select(Categoria.padre_id, Categoria.nombre)
            .where(Categoria.padre_id.in_(categoria_ids))
            .where(Categoria.eliminado_en.is_(None))
        ).all()

        if not rows:
            return

        # Group children by their offending parent id
        children_by_parent: dict[int, list[str]] = {}
        for padre_id, child_nombre in rows:
            children_by_parent.setdefault(padre_id, []).append(child_nombre)

        # Fetch offending parent names for the error message
        offender_ids = list(children_by_parent.keys())
        parent_rows = session.execute(
            select(Categoria.id, Categoria.nombre).where(Categoria.id.in_(offender_ids))
        ).all()
        parent_names: dict[int, str] = {row.id: row.nombre for row in parent_rows}

        # Build actionable error message in Rioplatense Spanish
        parts: list[str] = []
        for parent_id, child_names in children_by_parent.items():
            p_name = parent_names.get(parent_id, str(parent_id))
            hijas = ", ".join(f"'{h}'" for h in sorted(child_names))
            parts.append(
                f"La categoría '{p_name}' no es hoja — "
                f"tiene hijas activas: {hijas}. "
                f"Asigná el producto a una de ellas."
            )

        raise BusinessRuleError(" | ".join(parts))

    # ── Auto-disable hook (D4) ────────────────────────────────────────────

    def _auto_disable_if_no_leaf_categoria(
        self, product_id: int, session: Session
    ) -> None:
        """Disable product if it has zero active leaf-category associations.

        Invoked after any operation that mutates the category set of a product.
        If count_leaf_active_categories == 0 → sets disponible=False on the
        product within the same transaction and emits an INFO log.

        This method DOES NOT commit or flush the session (the caller's UoW
        handles that). It does call repo.update() which may flush internally.

        Args:
            product_id: Product primary key.
            session: Active SQLAlchemy session (same UoW as the caller).
        """
        repo = ProductRepository(session)
        count = repo.count_leaf_active_categories(product_id)
        if count == 0:
            repo.update(product_id, disponible=False)
            logger.info(
                "Producto %s desactivado: sin categoría hoja activa", product_id
            )

    # ── Create ────────────────────────────────────────────────────────────

    def create(self, payload: ProductoCreate) -> Producto:
        """Create a new product with required categories and optional ingredients.

        Validates:
        - nombre is not blank after strip.
        - categoria_ids is required and non-empty (BusinessRuleError if empty).
        - Each id in categoria_ids exists in the categories table (active rows).
        - Each id in categoria_ids references a leaf category (D3).
        - If ingrediente_ids provided, each must exist as an active ingredient.

        After creating category associations, invokes the auto-disable hook
        if categoria_ids was explicitly provided (D4): if the resulting count
        of active leaf categories is zero, sets disponible=False.

        Args:
            payload: Creation data.

        Returns:
            Newly created Producto.

        Raises:
            BusinessRuleError: If nombre is blank, categoria_ids is empty,
                any categoria_id is missing, or any categoria_id is not a leaf.
        """
        with UnitOfWork() as uow:
            repo, cat_repo, ing_repo = self._register_repos(uow)

            nombre = payload.nombre.strip()
            if not nombre:
                raise BusinessRuleError("El nombre del producto no puede estar vacío")

            # categoria_ids is now REQUIRED
            if not payload.categoria_ids:
                raise BusinessRuleError("El producto debe tener al menos una categoría")

            # Validate categoria_ids existence
            for cat_id in payload.categoria_ids:
                if cat_repo.read(cat_id) is None:
                    raise BusinessRuleError(f"Categoría {cat_id} no encontrada")
            # Leaf-only validation (D3)
            self._validate_categorias_are_leaves(payload.categoria_ids, uow.session)

            # Validate ingrediente_ids if provided
            if payload.ingrediente_ids:
                for ing_data in payload.ingrediente_ids:
                    ing_id = ing_data.get("ingrediente_id")
                    if ing_repo.read(ing_id) is None:
                        raise BusinessRuleError(f"Ingrediente {ing_id} no encontrado")

            producto = repo.create(
                nombre=nombre,
                descripcion=payload.descripcion,
                precio=payload.precio,
                stock_cantidad=payload.stock_cantidad,
                disponible=payload.disponible,
                imagen_url=payload.imagen_url,
            )

            # Associate categories
            repo.replace_categorias(producto.id, payload.categoria_ids)
            # Auto-disable hook (D4)
            self._auto_disable_if_no_leaf_categoria(producto.id, uow.session)

            # Associate ingredients if provided
            if payload.ingrediente_ids:
                for ing_data in payload.ingrediente_ids:
                    repo.add_ingrediente(
                        producto.id,
                        ing_data["ingrediente_id"],
                    )

            # Refresh to reflect possible disponible change
            uow.session.flush()
            uow.session.refresh(producto)

            return producto

    # ── Read ──────────────────────────────────────────────────────────────

    def get_by_id(self, producto_id: int) -> Producto:
        """Fetch a single active product by ID.

        Args:
            producto_id: Product primary key.

        Returns:
            Producto entity.

        Raises:
            NotFoundError: If not found or soft-deleted.
        """
        with UnitOfWork() as uow:
            repo, _, _ = self._register_repos(uow)

            current = repo.read(producto_id)
            if current is None:
                raise NotFoundError("Producto no encontrado")
            return current

    def get_detail(
        self, producto_id: int
    ) -> tuple[Producto, list[Categoria], list[Ingrediente]]:
        """Fetch product with full associations for the detail endpoint.

        Args:
            producto_id: Product primary key.

        Returns:
            (Producto, active_categorias, [Ingrediente, ...]).

        Raises:
            NotFoundError: If not found or soft-deleted.
        """
        with UnitOfWork() as uow:
            repo, _, _ = self._register_repos(uow)

            producto = repo.get_with_associations(producto_id)
            if producto is None:
                raise NotFoundError("Producto no encontrado")

            # Defensively filter soft-deleted categories from the eager-loaded rel
            categorias: list[Categoria] = [
                c for c in producto.categorias if c.eliminado_en is None
            ]
            ingredientes_with_flag = repo.list_ingredientes(producto_id)
            return producto, categorias, ingredientes_with_flag

    # ── List (paginated + filtered) ───────────────────────────────────────

    def list_paginated(
        self,
        *,
        page: int,
        limit: int,
        categoria_id: int | None,
        search: str | None,
        disponible: bool | None,
        excluir_alergenos: bool,
        excluir_alergeno_ids: list[int] | None = None,
        sin_categoria: bool = False,
        current_user: Optional[Usuario] = None,
        incluir_eliminados: bool = False,
    ) -> tuple[list[Producto], int]:
        """Return paginated filtered products.

        The default value for disponible (True) is applied in the router
        before calling this method (RN-CA08). The service is filter-agnostic.

        The ``incluir_eliminados`` flag is only honoured when the requesting
        user has the ADMIN role (RN-CA10, D1). For any other role or
        unauthenticated requests the flag is silently forced to False,
        preventing information disclosure.

        Args:
            page: 1-based page number.
            limit: Items per page.
            categoria_id: Optional category filter (recursive CTE, D1).
            search: Optional substring search (case-insensitive).
            disponible: Optional availability filter (None = no filter).
            excluir_alergenos: Exclude products with non-removable allergens.
            excluir_alergeno_ids: Exclude products with specific non-removable
                ingredients by ID list (D2). None/empty = no-op.
            sin_categoria: If True, return only products without active
                category associations (D5).
            current_user: Authenticated user, or None for public requests.
            incluir_eliminados: Show soft-deleted products (ADMIN only).

        Returns:
            (items, total_count).
        """
        # RN-CA10 / D1: only ADMIN may see soft-deleted products
        if incluir_eliminados and current_user is not None:
            roles = {r.codigo for r in current_user.roles}
            if "ADMIN" not in roles:
                incluir_eliminados = False
        elif incluir_eliminados and current_user is None:
            incluir_eliminados = False

        with UnitOfWork() as uow:
            repo, _, _ = self._register_repos(uow)

            skip = (page - 1) * limit
            return repo.list_paginated_with_filters(
                skip=skip,
                limit=limit,
                categoria_id=categoria_id,
                search=search,
                disponible=disponible,
                excluir_alergenos=excluir_alergenos,
                excluir_alergeno_ids=excluir_alergeno_ids or [],
                sin_categoria=sin_categoria,
                incluir_eliminados=incluir_eliminados,
            )

    def list_with_images(
        self,
        *,
        page: int,
        limit: int,
        categoria_id: int | None = None,
        search: str | None = None,
        disponible: bool | None = None,
        excluir_alergenos: bool = False,
        excluir_alergeno_ids: list[int] | None = None,
        sin_categoria: bool = False,
        current_user=None,
        incluir_eliminados: bool = False,
    ) -> tuple[list[Producto], int, dict[int, list]]:
        """Return paginated products with their images in 2 queries (no N+1)."""
        items, total = self.list_paginated(
            page=page,
            limit=limit,
            categoria_id=categoria_id,
            search=search,
            disponible=disponible,
            excluir_alergenos=excluir_alergenos,
            excluir_alergeno_ids=excluir_alergeno_ids,
            sin_categoria=sin_categoria,
            current_user=current_user,
            incluir_eliminados=incluir_eliminados,
        )
        if not items:
            return items, total, {}

        with UnitOfWork() as uow:
            repo, _, _ = self._register_repos(uow)
            images_by_pid = repo.list_imagenes_by_product_ids([p.id for p in items])
            return items, total, images_by_pid

    # ── Update ────────────────────────────────────────────────────────────

    def update(self, producto_id: int, payload: ProductoUpdate) -> Producto:
        """Partially update a product.

        Uses model_dump(exclude_unset=True) so omitted fields are preserved.

        Args:
            producto_id: Product primary key.
            payload: Fields to update.

        Returns:
            Updated Producto.

        Raises:
            NotFoundError: If not found or soft-deleted.
            BusinessRuleError: If nombre is blank after strip.
        """
        with UnitOfWork() as uow:
            repo, _, _ = self._register_repos(uow)

            current = repo.read(producto_id)
            if current is None:
                raise NotFoundError("Producto no encontrado")

            data = payload.model_dump(exclude_unset=True)

            if "nombre" in data:
                nombre = data["nombre"].strip()
                if not nombre:
                    raise BusinessRuleError(
                        "El nombre del producto no puede estar vacío"
                    )
                data["nombre"] = nombre

            updated = repo.update(producto_id, **data)
            # repo.update returns None only if the entity vanished between read
            # and update (should not happen in single-threaded tests)
            assert updated is not None, "Unexpected None from repo.update"
            return updated

    # ── Patch: disponibilidad ─────────────────────────────────────────────

    def set_disponibilidad(self, producto_id: int, disponible: bool) -> Producto:
        """Toggle product availability.

        Args:
            producto_id: Product primary key.
            disponible: New availability value.

        Returns:
            Updated Producto.

        Raises:
            NotFoundError: If not found or soft-deleted.
        """
        with UnitOfWork() as uow:
            repo, _, _ = self._register_repos(uow)

            current = repo.read(producto_id)
            if current is None:
                raise NotFoundError("Producto no encontrado")
            updated = repo.update(producto_id, disponible=disponible)
            assert updated is not None
            return updated

    # ── Patch: stock ──────────────────────────────────────────────────────

    def set_stock(self, producto_id: int, stock_cantidad: int) -> Producto:
        """Set absolute stock value.

        Pydantic already validates stock_cantidad >= 0, but we add a
        defensive guard here per D5.

        Args:
            producto_id: Product primary key.
            stock_cantidad: New stock value (must be >= 0).

        Returns:
            Updated Producto.

        Raises:
            BusinessRuleError: If stock_cantidad < 0.
            NotFoundError: If not found or soft-deleted.
        """
        with UnitOfWork() as uow:
            repo, _, _ = self._register_repos(uow)

            if stock_cantidad < 0:
                raise BusinessRuleError("El stock no puede ser negativo")
            current = repo.read(producto_id)
            if current is None:
                raise NotFoundError("Producto no encontrado")
            updated = repo.update(producto_id, stock_cantidad=stock_cantidad)
            assert updated is not None
            return updated

    # ── Delete (soft) ─────────────────────────────────────────────────────

    def delete(self, producto_id: int) -> None:
        """Soft-delete a product.

        No guards on pivot rows — soft-deleted products stop appearing in the
        catalog naturally (BaseRepository._get_base_query filters eliminado_en
        IS NULL). Pivot rows remain untouched (D11).

        Args:
            producto_id: Product primary key.

        Raises:
            NotFoundError: If not found or already soft-deleted.
        """
        with UnitOfWork() as uow:
            repo, _, _ = self._register_repos(uow)

            current = repo.read(producto_id)
            if current is None:
                raise NotFoundError("Producto no encontrado")
            repo.delete(producto_id)

    # ── M:N categories ────────────────────────────────────────────────────

    def set_categorias(
        self, producto_id: int, categoria_ids: list[int]
    ) -> tuple[Producto, list[Categoria], list[Ingrediente]]:
        """Replace the full category set for a product.

        Validates ALL ids before touching pivot rows — if any id is invalid,
        raises BusinessRuleError without making partial changes.

        After validating existence, validates that every id is a leaf category
        (D3). After the pivot replace, invokes the auto-disable hook (D4).

        Returns the full product detail (with hydrated associations) within
        the same transaction, eliminating the double-read pattern.

        Args:
            producto_id: Product primary key.
            categoria_ids: Full desired set of category IDs (may be empty).

        Returns:
            (Producto, active_categorias, [Ingrediente, ...]).

        Raises:
            NotFoundError: If the product is not found.
            BusinessRuleError: If any category id does not exist or is not a leaf.
        """
        with UnitOfWork() as uow:
            repo, cat_repo, _ = self._register_repos(uow)

            current = repo.read(producto_id)
            if current is None:
                raise NotFoundError("Producto no encontrado")

            # Validate ALL before any pivot mutation (atomicity)
            for cat_id in categoria_ids:
                if cat_repo.read(cat_id) is None:
                    raise BusinessRuleError(f"Categoría {cat_id} no encontrada")

            # Leaf-only validation (D3) — after existence check, before pivot mutation
            self._validate_categorias_are_leaves(categoria_ids, uow.session)

            repo.replace_categorias(producto_id, categoria_ids)

            # Auto-disable hook (D4)
            self._auto_disable_if_no_leaf_categoria(producto_id, uow.session)

            # Reload with fresh associations within the same transaction
            uow.session.flush()
            producto = repo.get_with_associations(producto_id)
            assert producto is not None

            categorias: list[Categoria] = [
                c for c in producto.categorias if c.eliminado_en is None
            ]
            ingredientes_with_flag = repo.list_ingredientes(producto_id)
            return producto, categorias, ingredientes_with_flag

    # ── M:N ingredients ───────────────────────────────────────────────────

    def add_ingrediente(
        self,
        producto_id: int,
        ingrediente_id: int,
    ) -> tuple[ProductoIngrediente, list[Ingrediente]]:
        """Associate an ingredient with a product.

        Returns the pivot row and the updated ingredient list for response
        building, within the same transaction.

        ``es_removible`` was removed from the signature — it is now a
        global property on ``Ingrediente``.

        Args:
            producto_id: Product primary key.
            ingrediente_id: Ingredient primary key.

        Returns:
            (ProductoIngrediente pivot row, [Ingrediente, ...]).

        Raises:
            NotFoundError: If the product is not found.
            BusinessRuleError: If the ingredient does not exist.
            ConflictError: If the association is already active (from repo).
        """
        with UnitOfWork() as uow:
            repo, _, ing_repo = self._register_repos(uow)

            producto = repo.read(producto_id)
            if producto is None:
                raise NotFoundError("Producto no encontrado")

            ingrediente = ing_repo.read(ingrediente_id)
            if ingrediente is None:
                raise BusinessRuleError(f"Ingrediente {ingrediente_id} no encontrado")

            pi = repo.add_ingrediente(producto_id, ingrediente_id)
            # Flush so list_ingredientes sees the new row
            uow.session.flush()
            result = repo.list_ingredientes(producto_id)
            return pi, result

    def remove_ingrediente(self, producto_id: int, ingrediente_id: int) -> None:
        """Remove (soft-delete) an ingredient association.

        Args:
            producto_id: Product primary key.
            ingrediente_id: Ingredient primary key.

        Raises:
            NotFoundError: If the product is not found or the association
                does not exist / is already soft-deleted.
        """
        with UnitOfWork() as uow:
            repo, _, _ = self._register_repos(uow)

            producto = repo.read(producto_id)
            if producto is None:
                raise NotFoundError("Producto no encontrado")

            removed = repo.remove_ingrediente(producto_id, ingrediente_id)
            if not removed:
                raise NotFoundError("Asociación de ingrediente no encontrada")

    def list_ingredientes(self, producto_id: int) -> list[Ingrediente]:
        """Return Ingrediente objects for a product.

        ``es_removible`` is now an attribute of ``Ingrediente`` itself.

        Args:
            producto_id: Product primary key.

        Returns:
            List of Ingrediente entities.

        Raises:
            NotFoundError: If the product is not found.
        """
        with UnitOfWork() as uow:
            repo, _, _ = self._register_repos(uow)

            producto = repo.read(producto_id)
            if producto is None:
                raise NotFoundError("Producto no encontrado")
            return repo.list_ingredientes(producto_id)

    # ── Image management ──────────────────────────────────────────────────

    def add_imagen_from_url(self, producto_id: int, url: str) -> ProductoImagen:
        """Add an image by URL for a product."""
        # Validate URL format
        if not url.startswith(("http://", "https://")):
            raise BusinessRuleError("URL debe comenzar con http:// o https://")

        with UnitOfWork() as uow:
            repo, _, _ = self._register_repos(uow)

            producto = repo.read(producto_id)
            if producto is None:
                raise NotFoundError("Producto no encontrado")

            existing = repo.list_imagenes(producto_id)
            orden = len(existing)
            es_primaria = not any(img.es_primaria for img in existing)

            img = repo.add_imagen(producto_id, url)
            img.orden = orden
            img.es_primaria = es_primaria
            uow.session.flush()
            uow.session.refresh(img)
            return img

    def delete_imagen(self, producto_id: int, imagen_id: int) -> None:
        """Soft-delete an image. If primary, reassign to next by orden."""
        with UnitOfWork() as uow:
            repo, _, _ = self._register_repos(uow)

            producto = repo.read(producto_id)
            if producto is None:
                raise NotFoundError("Producto no encontrado")

            images = repo.list_imagenes(producto_id)
            target = next((img for img in images if img.id == imagen_id), None)
            if target is None:
                raise NotFoundError("Imagen no encontrada")

        with UnitOfWork() as uow:
            repo, _, _ = self._register_repos(uow)

            was_primary = target.es_primaria
            repo.delete_imagen(imagen_id)

            if was_primary:
                remaining = repo.list_imagenes(producto_id)
                if remaining:
                    repo.set_all_non_primaria(producto_id)
                    repo.set_primaria(remaining[0].id)

    def set_imagen_orden(
        self, producto_id: int, imagen_id: int, new_orden: int
    ) -> ProductoImagen:
        """Update the display order of an image."""
        with UnitOfWork() as uow:
            repo, _, _ = self._register_repos(uow)

            producto = repo.read(producto_id)
            if producto is None:
                raise NotFoundError("Producto no encontrado")

            images = repo.list_imagenes(producto_id)
            target = next((img for img in images if img.id == imagen_id), None)
            if target is None:
                raise NotFoundError("Imagen no encontrada")

            target.orden = new_orden
            uow.session.flush()
            uow.session.refresh(target)
            return target

    def set_imagen_primaria(self, producto_id: int, imagen_id: int) -> ProductoImagen:
        """Set an image as primary, unsetting all others."""
        with UnitOfWork() as uow:
            repo, _, _ = self._register_repos(uow)

            producto = repo.read(producto_id)
            if producto is None:
                raise NotFoundError("Producto no encontrado")

            images = repo.list_imagenes(producto_id)
            target = next((img for img in images if img.id == imagen_id), None)
            if target is None:
                raise NotFoundError("Imagen no encontrada")

            repo.set_all_non_primaria(producto_id)
            repo.set_primaria(imagen_id)
            uow.session.refresh(target)
            return target
