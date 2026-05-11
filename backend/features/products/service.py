"""
ProductService — business logic for product CRUD and M:N associations.

Orchestrates:
- Validations (nombre not empty, FK existence for categorías e ingredientes).
- Soft delete without cascades (D11 in design.md).
- M:N bulk replace for categories (replace semantics).
- M:N individual add/remove for ingredients (with es_removible flag).
- Partial updates via model_dump(exclude_unset=True).

Rules:
- Each public method opens its own UnitOfWork context. Commit is performed
  by ``__exit__`` on clean exit. The router never calls uow.commit().
- Import order: Router → Service → UoW → Repository → Model.
- set_categorias validates ALL ids before touching pivot rows (atomicity).
- set_categorias returns the full ProductoDetail (producto, categorias, ingredientes)
  within the same with-block, eliminating the double-read pattern.
"""

from __future__ import annotations

from backend.features.catalog.models import Categoria, Ingrediente
from backend.features.categories.repository import CategoryRepository
from backend.features.ingredients.repository import IngredientRepository
from backend.features.products.models import Producto, ProductoIngrediente
from backend.features.products.repository import ProductRepository
from backend.features.products.schemas import ProductoCreate, ProductoUpdate
from backend.shared.exceptions import BusinessRuleError, NotFoundError
from backend.shared.unit_of_work import UnitOfWork


class ProductService:
    """Business logic for the product domain."""

    def __init__(self) -> None:
        pass

    def _register_repos(self, uow: UnitOfWork) -> tuple[ProductRepository, CategoryRepository, IngredientRepository]:
        """Register and return the three repositories for this domain."""
        uow.register_repository("productos", ProductRepository(uow.session))
        uow.register_repository("categorias", CategoryRepository(uow.session))
        uow.register_repository("ingredientes", IngredientRepository(uow.session))
        return uow.productos, uow.categorias, uow.ingredientes  # type: ignore[return-value]

    # ── Create ────────────────────────────────────────────────────────────

    def create(self, payload: ProductoCreate) -> Producto:
        """Create a new product, optionally associating categories.

        Validates:
        - nombre is not blank after strip.
        - Each id in categoria_ids exists in the categories table.

        Args:
            payload: Creation data.

        Returns:
            Newly created Producto.

        Raises:
            BusinessRuleError: If nombre is blank or any categoria_id is
                missing.
        """
        with UnitOfWork() as uow:
            repo, cat_repo, _ = self._register_repos(uow)

            nombre = payload.nombre.strip()
            if not nombre:
                raise BusinessRuleError(
                    "El nombre del producto no puede estar vacío"
                )

            # Validate categoria_ids before touching the DB
            if payload.categoria_ids is not None:
                for cat_id in payload.categoria_ids:
                    if cat_repo.read(cat_id) is None:
                        raise BusinessRuleError(
                            f"Categoría {cat_id} no encontrada"
                        )

            producto = repo.create(
                nombre=nombre,
                descripcion=payload.descripcion,
                precio=payload.precio,
                stock_cantidad=payload.stock_cantidad,
                disponible=payload.disponible,
                imagen_url=payload.imagen_url,
            )

            if payload.categoria_ids is not None:
                repo.replace_categorias(producto.id, payload.categoria_ids)

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
    ) -> tuple[Producto, list[Categoria], list[tuple[Ingrediente, bool]]]:
        """Fetch product with full associations for the detail endpoint.

        Args:
            producto_id: Product primary key.

        Returns:
            (Producto, active_categorias, [(Ingrediente, es_removible)]).

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
    ) -> tuple[list[Producto], int]:
        """Return paginated filtered products.

        The default value for disponible (True) is applied in the router
        before calling this method (RN-CA08). The service is filter-agnostic.

        Args:
            page: 1-based page number.
            limit: Items per page.
            categoria_id: Optional category filter.
            search: Optional substring search (case-insensitive).
            disponible: Optional availability filter (None = no filter).
            excluir_alergenos: Exclude products with non-removable allergens.

        Returns:
            (items, total_count).
        """
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
            )

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
    ) -> tuple[Producto, list[Categoria], list[tuple[Ingrediente, bool]]]:
        """Replace the full category set for a product.

        Validates ALL ids before touching pivot rows — if any id is invalid,
        raises BusinessRuleError without making partial changes.

        Returns the full product detail (with hydrated associations) within
        the same transaction, eliminating the double-read pattern.

        Args:
            producto_id: Product primary key.
            categoria_ids: Full desired set of category IDs (may be empty).

        Returns:
            (Producto, active_categorias, [(Ingrediente, es_removible)]).

        Raises:
            NotFoundError: If the product is not found.
            BusinessRuleError: If any category id does not exist.
        """
        with UnitOfWork() as uow:
            repo, cat_repo, _ = self._register_repos(uow)

            current = repo.read(producto_id)
            if current is None:
                raise NotFoundError("Producto no encontrado")

            # Validate ALL before any pivot mutation
            for cat_id in categoria_ids:
                if cat_repo.read(cat_id) is None:
                    raise BusinessRuleError(f"Categoría {cat_id} no encontrada")

            repo.replace_categorias(producto_id, categoria_ids)

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
        es_removible: bool,
    ) -> tuple[ProductoIngrediente, list[tuple[Ingrediente, bool]]]:
        """Associate an ingredient with a product.

        Returns the pivot row and the updated ingredient list for response
        building, within the same transaction.

        Args:
            producto_id: Product primary key.
            ingrediente_id: Ingredient primary key.
            es_removible: Whether the customer can remove it on order.

        Returns:
            (ProductoIngrediente pivot row, [(Ingrediente, es_removible)]).

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
                raise BusinessRuleError(
                    f"Ingrediente {ingrediente_id} no encontrado"
                )

            pi = repo.add_ingrediente(producto_id, ingrediente_id, es_removible)
            # Flush so list_ingredientes sees the new row
            uow.session.flush()
            result = repo.list_ingredientes(producto_id)
            return pi, result

    def remove_ingrediente(
        self, producto_id: int, ingrediente_id: int
    ) -> None:
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

    def list_ingredientes(
        self, producto_id: int
    ) -> list[tuple[Ingrediente, bool]]:
        """Return (Ingrediente, es_removible) pairs for a product.

        Args:
            producto_id: Product primary key.

        Returns:
            List of (Ingrediente, es_removible bool) tuples.

        Raises:
            NotFoundError: If the product is not found.
        """
        with UnitOfWork() as uow:
            repo, _, _ = self._register_repos(uow)

            producto = repo.read(producto_id)
            if producto is None:
                raise NotFoundError("Producto no encontrado")
            return repo.list_ingredientes(producto_id)
