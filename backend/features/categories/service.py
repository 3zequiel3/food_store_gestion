"""
CategoryService — business logic for hierarchical category CRUD.

Orchestrates validation rules via UnitOfWork + CategoryRepository:
- Name uniqueness within a level (prevent duplicate siblings).
- Parent existence validation.
- Cycle detection before reparenting (CTE-based).
- Guard checks before soft delete (active children / products).

The service NEVER calls ``uow.commit()`` — that is the router's
responsibility (see D6 in design.md).
"""

from __future__ import annotations

from backend.features.categories.repository import CategoryRepository
from backend.features.categories.schemas import (
    CategoriaCreate,
    CategoriaTreeNode,
    CategoriaUpdate,
    CategoryFlatRow,
)
from backend.shared.exceptions import BusinessRuleError, ConflictError, NotFoundError
from backend.shared.unit_of_work import UnitOfWork


class CategoryService:
    """Business logic for the category domain."""

    def __init__(self, uow: UnitOfWork) -> None:
        uow.register_repository("categorias", CategoryRepository(uow.session))
        self.repo: CategoryRepository = uow.categorias  # type: ignore[assignment]
        self.uow = uow

    # ── Create ────────────────────────────────────────────────────────────

    def create(self, payload: CategoriaCreate) -> Categoria:
        """Create a new category.

        Validates:
        - Nombre is not blank.
        - Parent exists (if provided).
        - No duplicate name at the same level.

        Args:
            payload: Creation data.

        Returns:
            The newly created Categoria entity.

        Raises:
            BusinessRuleError: If parent does not exist.
            ConflictError: If a sibling with the same name exists.
        """
        nombre = payload.nombre.strip()
        if not nombre:
            raise BusinessRuleError("El nombre de la categoría no puede estar vacío")

        padre_id = payload.padre_id

        if padre_id is not None:
            parent = self.repo.read(padre_id)
            if parent is None:
                raise BusinessRuleError(
                    f"La categoría padre con ID {padre_id} no existe"
                )

        # Uniqueness check at the target level
        existing = self.repo.find_by_nombre_y_padre(nombre, padre_id)
        if existing is not None:
            raise ConflictError(
                "Ya existe una categoría con ese nombre en este nivel"
            )

        return self.repo.create(nombre=nombre, padre_id=padre_id)

    # ── Update ────────────────────────────────────────────────────────────

    def update(self, categoria_id: int, payload: CategoriaUpdate) -> Categoria:
        """Update an existing category.

        Handles partial updates via ``model_dump(exclude_unset=True)`` so that
        omitting ``padre_id`` preserves the current parent while sending
        ``padre_id: null`` promotes to root.

        Validates:
        - Category exists (not soft-deleted).
        - New parent exists (if changing parent).
        - Reparenting does not create a cycle.
        - No duplicate name at the target level.

        Args:
            categoria_id: ID of the category to update.
            payload: Fields to update.

        Returns:
            The updated Categoria entity.

        Raises:
            NotFoundError: If category does not exist.
            BusinessRuleError: If reparenting creates a cycle, or parent missing.
            ConflictError: If a sibling with the same name exists.
        """
        current = self.repo.read(categoria_id)
        if current is None:
            raise NotFoundError("Categoría no encontrada")

        data = payload.model_dump(exclude_unset=True)

        # ── Validate parent_id change ─────────────────────────────────────
        if "padre_id" in data and data["padre_id"] != current.padre_id:
            new_padre_id = data["padre_id"]

            if new_padre_id is not None:
                parent = self.repo.read(new_padre_id)
                if parent is None:
                    raise BusinessRuleError(
                        f"La categoría padre con ID {new_padre_id} no existe"
                    )

            # Cycle detection
            if self.repo.would_create_cycle(categoria_id, new_padre_id):
                raise BusinessRuleError(
                    "El cambio de padre crearía un ciclo en la jerarquía"
                )

        # ── Uniqueness check ──────────────────────────────────────────────
        effective_nombre = data.get("nombre", current.nombre)
        effective_padre_id = data.get("padre_id", current.padre_id)

        sibling = self.repo.find_by_nombre_y_padre(
            effective_nombre.strip(), effective_padre_id
        )
        if sibling is not None and sibling.id != categoria_id:
            raise ConflictError(
                "Ya existe una categoría con ese nombre en este nivel"
            )

        # ── Apply update ──────────────────────────────────────────────────
        return self.repo.update(categoria_id, **data)

    # ── Delete (soft) ─────────────────────────────────────────────────────

    def delete(self, categoria_id: int) -> None:
        """Soft-delete a category.

        Guards:
        - Category exists (not already soft-deleted).
        - No active children (US-010 #3).
        - No active products associated (US-010 #2).

        Args:
            categoria_id: ID of the category to soft-delete.

        Raises:
            NotFoundError: If category does not exist.
            BusinessRuleError: If category has active children or products.
        """
        current = self.repo.read(categoria_id)
        if current is None:
            raise NotFoundError("Categoría no encontrada")

        if self.repo.has_active_children(categoria_id):
            raise BusinessRuleError(
                "No se puede eliminar la categoría: tiene subcategorías activas. "
                "Reasignelas o eliminelas primero"
            )

        if self.repo.has_active_products(categoria_id):
            raise BusinessRuleError(
                "No se puede eliminar la categoría: tiene productos activos "
                "asociados. Reasigne los productos primero"
            )

        self.repo.delete(categoria_id)

    # ── Tree (read-only) ──────────────────────────────────────────────────

    def get_tree(self) -> list[CategoriaTreeNode]:
        """Build the nested category tree from flat CTE results.

        1. Fetch flat rows via ``get_tree_cte()``.
        2. Build an id→node map.
        3. Nest children under their parent.
        4. Return root-level nodes.

        Returns:
            List of root CategoriaTreeNode with nested subcategorias.
        """
        flat: list[CategoryFlatRow] = self.repo.get_tree_cte()

        node_map: dict[int, CategoriaTreeNode] = {}
        for row in flat:
            node_map[row.id] = CategoriaTreeNode(
                id=row.id,
                nombre=row.nombre,
                padre_id=row.padre_id,
            )

        roots: list[CategoriaTreeNode] = []
        for node in node_map.values():
            if node.padre_id is None or node.padre_id not in node_map:
                roots.append(node)
            else:
                parent = node_map[node.padre_id]
                parent.subcategorias.append(node)

        return roots
