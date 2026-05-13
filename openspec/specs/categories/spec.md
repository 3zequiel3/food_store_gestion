## Purpose

This capability provides a hierarchical category (catalog) system for organizing products. Categories can be nested to arbitrary depth with parent-child relationships, support unique naming per level, and include comprehensive guards against cycles and unsafe deletions.

## Requirements

### Requirement: Hierarchical category model
The system SHALL persist categories in the existing `categories` table (created in migration `20260428_0001_initial_schema`) with self-referential parent FK enabling arbitrary-depth trees. The ORM class `Categoria` defined in `backend/features/catalog/models.py` SHALL be the single source of truth — the new `categories` module MUST import it, not redefine it. (RN-CA01)

#### Scenario: Categoria has self-referential parent FK
- **WHEN** the `categories` table schema is introspected
- **THEN** column `padre_id` exists, is `Integer NULL`, and is a foreign key to `categories.id` with `ON DELETE SET NULL`

#### Scenario: Categoria ORM is reused, not redefined
- **WHEN** `backend.features.categories.repository` is imported
- **THEN** it imports `Categoria` from `backend.features.catalog.models` and does NOT declare a new SQLAlchemy class with `__tablename__ = "categories"`

#### Scenario: Categoria supports tree relationships
- **WHEN** a `Categoria` instance is loaded from the database
- **THEN** it exposes a `padre: Optional[Categoria]` attribute and a `hijos: list[Categoria]` collection populated via the self-referential relationship

### Requirement: Create category endpoint
The system SHALL expose `POST /api/v1/categorias` protected by `require_role("ADMIN", "STOCK")` that accepts `CategoriaCreate({nombre: str, padre_id: int | None})`. On success it SHALL return 201 with `CategoriaRead`. The `nombre` field SHALL be trimmed and validated with `min_length=1, max_length=100`. (US-007)

#### Scenario: Successful category creation as ADMIN
- **WHEN** a user with role `ADMIN` posts `{"nombre": "Bebidas", "padre_id": null}`
- **THEN** the response is 201 with body `{"id": <int>, "nombre": "Bebidas", "padre_id": null, "creado_en": <iso>, "actualizado_en": <iso>}` and a row exists in `categories`

#### Scenario: Successful subcategory creation as STOCK
- **GIVEN** a category `id=5` with name "Bebidas" exists
- **WHEN** a user with role `STOCK` posts `{"nombre": "Gaseosas", "padre_id": 5}`
- **THEN** the response is 201 with `padre_id: 5`

#### Scenario: Unauthenticated request rejected
- **WHEN** an anonymous client posts to `/api/v1/categorias`
- **THEN** the response is 401 (RFC 7807)

#### Scenario: CLIENT role forbidden
- **WHEN** a user with role `CLIENT` posts a valid create payload
- **THEN** the response is 403 (RFC 7807) with `title: "Forbidden"`

#### Scenario: Empty nombre rejected
- **WHEN** a payload with `nombre: ""` is posted
- **THEN** the response is 422 (RFC 7807) with `errors[]` listing the `nombre` field

#### Scenario: Nombre longer than 100 chars rejected
- **WHEN** a payload with `nombre` of 101 characters is posted
- **THEN** the response is 422 (RFC 7807)

#### Scenario: padre_id pointing to non-existent category rejected
- **WHEN** a payload with `padre_id: 99999` (no such id) is posted
- **THEN** the response is 422 with `BusinessRuleError` detail "Categoría padre no encontrada"

### Requirement: Unique name per level
The system SHALL reject creating or editing a category whose `(nombre, padre_id)` pair already exists among non-deleted siblings (`eliminado_en IS NULL`). This validation lives in the service layer (NOT a database UNIQUE constraint) because PostgreSQL treats `NULL` values as distinct, which would allow duplicate root-level names. (US-007 acceptance #2)

#### Scenario: Duplicate root-level name rejected
- **GIVEN** a non-deleted category with `(nombre="Bebidas", padre_id=NULL)` exists
- **WHEN** a payload `{"nombre": "Bebidas", "padre_id": null}` is posted
- **THEN** the response is 409 (RFC 7807) with `title: "Conflict"` and detail "Ya existe una categoría con ese nombre en este nivel"

#### Scenario: Duplicate sibling name rejected
- **GIVEN** category `id=5` is parent of `(nombre="Coca", padre_id=5)`
- **WHEN** a payload `{"nombre": "Coca", "padre_id": 5}` is posted
- **THEN** the response is 409

#### Scenario: Same name allowed at different levels
- **GIVEN** a root category `(nombre="Promos", padre_id=NULL)` exists
- **WHEN** a payload `{"nombre": "Promos", "padre_id": 5}` is posted (subcategory of "Bebidas")
- **THEN** the response is 201

#### Scenario: Soft-deleted name does not block creation
- **GIVEN** a category `(nombre="Postres", padre_id=NULL)` was soft-deleted (`eliminado_en` set)
- **WHEN** a payload `{"nombre": "Postres", "padre_id": null}` is posted
- **THEN** the response is 201

### Requirement: List category tree endpoint
The system SHALL expose `GET /api/v1/categorias` (public, no authentication required) that supports two response modes governed by the query param `solo_hojas: bool = False`.

When `solo_hojas` is `false` (default), the endpoint SHALL return the full tree of non-deleted categories as a nested JSON array of `CategoriaTreeNode({id: int, nombre: str, padre_id: int | None, subcategorias: list[CategoriaTreeNode]})`. The tree SHALL be built using a recursive Common Table Expression (CTE) starting from root nodes (`padre_id IS NULL`). Soft-deleted categories (`eliminado_en IS NOT NULL`) SHALL be excluded.

When `solo_hojas` is `true`, the endpoint SHALL return a flat JSON array of `CategoriaRead({id: int, nombre: str, padre_id: int | None, creado_en, actualizado_en})` containing only **leaf** categories — i.e. active categories (`eliminado_en IS NULL`) that have zero non-deleted children. The result SHALL be sorted alphabetically by `nombre` (ascending, case-insensitive). The flat mode SHALL NOT nest under `subcategorias`. (US-008, RN-CA09)

#### Scenario: Tree mode returns nested structure
- **GIVEN** categories: `Bebidas (id=1, padre=NULL)`, `Gaseosas (id=2, padre=1)`, `Coca (id=3, padre=2)`, `Postres (id=4, padre=NULL)`
- **WHEN** `GET /api/v1/categorias` is called (no params)
- **THEN** the response is 200 with body equivalent to:
  ```json
  [
    {"id": 1, "nombre": "Bebidas", "padre_id": null, "subcategorias": [
      {"id": 2, "nombre": "Gaseosas", "padre_id": 1, "subcategorias": [
        {"id": 3, "nombre": "Coca", "padre_id": 2, "subcategorias": []}
      ]}
    ]},
    {"id": 4, "nombre": "Postres", "padre_id": null, "subcategorias": []}
  ]
  ```

#### Scenario: solo_hojas=true returns flat leaves only
- **GIVEN** categories: `Bebidas (id=1, raíz, tiene hijas)`, `Gaseosas (id=2, hija de 1, sin hijas)`, `Coca (id=3, hija de 2, sin hijas)`, `Postres (id=4, raíz, sin hijas)`
- **WHEN** `GET /api/v1/categorias?solo_hojas=true` is called
- **THEN** the response is 200 with a flat array `[Coca, Postres]` (sorted alphabetically); items 1 and 2 are excluded because they have active children; the items SHALL NOT contain a `subcategorias` key

#### Scenario: solo_hojas excludes categories whose only children are soft-deleted parents-of-leaves promoted to leaf
- **GIVEN** category `Bebidas (id=1)` had child `Gaseosas (id=2)` which is soft-deleted; `Bebidas` now has zero active children
- **WHEN** `GET /api/v1/categorias?solo_hojas=true` is called
- **THEN** the response includes `Bebidas` (it is now effectively a leaf because the only child is soft-deleted)

#### Scenario: solo_hojas with empty catalog returns empty list
- **GIVEN** the `categories` table has no non-deleted rows
- **WHEN** `GET /api/v1/categorias?solo_hojas=true` is called
- **THEN** the response is 200 with body `[]`

#### Scenario: Empty catalog returns empty list (tree mode)
- **GIVEN** the `categories` table has no non-deleted rows
- **WHEN** `GET /api/v1/categorias` is called
- **THEN** the response is 200 with body `[]`

#### Scenario: Soft-deleted categories excluded
- **GIVEN** category `id=2` is soft-deleted but its non-deleted child `id=3` references it
- **WHEN** `GET /api/v1/categorias` is called
- **THEN** the response excludes `id=2` and treats `id=3` as if it were detached (still listed if its `eliminado_en IS NULL`, with `padre_id=2` preserved but no parent path)

#### Scenario: Endpoint is public regardless of mode
- **WHEN** an anonymous client calls `GET /api/v1/categorias` or `GET /api/v1/categorias?solo_hojas=true`
- **THEN** the response is 200 (no auth required)

### Requirement: Update category endpoint
The system SHALL expose `PUT /api/v1/categorias/{id}` protected by `require_role("ADMIN", "STOCK")` that accepts `CategoriaUpdate({nombre: str | None, padre_id: int | None | UNSET})` (partial update). On success it SHALL return 200 with `CategoriaRead`. The endpoint SHALL re-validate uniqueness per level (using the new `(nombre, padre_id)` tuple) and SHALL reject any change that would create a cycle. (US-009)

#### Scenario: Successful name update
- **WHEN** a user with role `ADMIN` PUTs `/api/v1/categorias/5` with `{"nombre": "Bebidas Frías"}`
- **THEN** the response is 200 with `nombre: "Bebidas Frías"`

#### Scenario: Successful parent reassignment
- **GIVEN** category `id=10` with `padre_id=5`
- **WHEN** PUT `/api/v1/categorias/10` with `{"padre_id": 7}`
- **THEN** the response is 200 with `padre_id: 7`

#### Scenario: Promote subcategory to root
- **GIVEN** category `id=10` with `padre_id=5`
- **WHEN** PUT `/api/v1/categorias/10` with `{"padre_id": null}`
- **THEN** the response is 200 with `padre_id: null`

#### Scenario: Non-existent category returns 404
- **WHEN** PUT `/api/v1/categorias/99999` with any payload
- **THEN** the response is 404 (RFC 7807)

#### Scenario: Soft-deleted category cannot be updated
- **GIVEN** category `id=5` has `eliminado_en` set
- **WHEN** PUT `/api/v1/categorias/5` with any payload
- **THEN** the response is 404 (the repository excludes soft-deleted rows from the base query)

### Requirement: Cycle prevention on parent change
The system SHALL prevent any update that would create a cycle in the category tree, including a category being its own parent. The validation SHALL be performed by the repository method `would_create_cycle(categoria_id: int, new_padre_id: int | None) -> bool` using a recursive CTE that walks UP from `new_padre_id` and checks whether `categoria_id` appears in the ancestor chain. If it does, the service SHALL raise `BusinessRuleError`. (US-009 acceptance #2 + #3, RN-CA02)

#### Scenario: Self-parent rejected
- **WHEN** PUT `/api/v1/categorias/5` with `{"padre_id": 5}`
- **THEN** the response is 422 (`BusinessRuleError`) with detail "Una categoría no puede ser padre de sí misma"

#### Scenario: Direct cycle rejected (A → B → A)
- **GIVEN** category `A (id=1, padre=NULL)` and `B (id=2, padre=1)`
- **WHEN** PUT `/api/v1/categorias/1` with `{"padre_id": 2}`
- **THEN** the response is 422 (`BusinessRuleError`) with detail "El cambio de padre crearía un ciclo en la jerarquía"

#### Scenario: Indirect cycle rejected (A → B → C → A)
- **GIVEN** A (id=1, padre=NULL), B (id=2, padre=1), C (id=3, padre=2)
- **WHEN** PUT `/api/v1/categorias/1` with `{"padre_id": 3}`
- **THEN** the response is 422

#### Scenario: Setting padre to NULL never creates a cycle
- **GIVEN** A (id=1, padre=2), B (id=2, padre=NULL)
- **WHEN** PUT `/api/v1/categorias/1` with `{"padre_id": null}`
- **THEN** the response is 200 (root-promotion is always safe)

### Requirement: Soft delete category endpoint
The system SHALL expose `DELETE /api/v1/categorias/{id}` protected by `require_role("ADMIN", "STOCK")` that performs a soft delete by setting `eliminado_en = now()`. The endpoint MUST NEVER perform a hard delete. On success it SHALL return 204 with empty body. (US-010, RN-CA09)

#### Scenario: Successful soft delete
- **GIVEN** category `id=5` with no children and no associated products
- **WHEN** a user with role `ADMIN` calls `DELETE /api/v1/categorias/5`
- **THEN** the response is 204 AND the row in `categories` has `eliminado_en IS NOT NULL` (NOT physically removed)

#### Scenario: Hard delete never happens
- **WHEN** any DELETE request succeeds
- **THEN** the row count of `categories` (including soft-deleted) is unchanged

#### Scenario: Already-deleted category returns 404
- **GIVEN** category `id=5` was previously soft-deleted
- **WHEN** `DELETE /api/v1/categorias/5` is called again
- **THEN** the response is 404

#### Scenario: Non-existent category returns 404
- **WHEN** `DELETE /api/v1/categorias/99999` is called
- **THEN** the response is 404

### Requirement: Delete guard for active subcategories
The system SHALL reject deletion of a category that has at least one non-deleted child (`SELECT 1 FROM categories WHERE padre_id = :id AND eliminado_en IS NULL`). The service MUST raise `BusinessRuleError` and the response MUST be 422 with detail "No se puede eliminar la categoría: tiene subcategorías activas. Reasignelas o eliminelas primero". (US-010 acceptance #3)

#### Scenario: Delete with active children rejected
- **GIVEN** category `id=1` (Bebidas) has non-deleted child `id=2` (Gaseosas)
- **WHEN** `DELETE /api/v1/categorias/1` is called
- **THEN** the response is 422 (`BusinessRuleError`) AND the row `id=1` still has `eliminado_en IS NULL`

#### Scenario: Delete works after children are soft-deleted
- **GIVEN** category `id=1` had child `id=2`, but `id=2` is now soft-deleted
- **WHEN** `DELETE /api/v1/categorias/1` is called
- **THEN** the response is 204

### Requirement: Delete guard for active products
The system SHALL reject deletion of a category that has at least one associated non-deleted product. The check SHALL join `product_categories` with `products` filtering `products.eliminado_en IS NULL`. The service MUST raise `BusinessRuleError` and the response MUST be 422 with detail "No se puede eliminar la categoría: tiene productos activos asociados. Reasigne los productos primero". (US-010 acceptance #2, RN-CA03)

#### Scenario: Delete with active products rejected
- **GIVEN** category `id=5` has a row in `product_categories` with `product_id=10` AND `products.id=10` has `eliminado_en IS NULL`
- **WHEN** `DELETE /api/v1/categorias/5` is called
- **THEN** the response is 422 (`BusinessRuleError`)

#### Scenario: Delete works when associated products are soft-deleted
- **GIVEN** category `id=5` is associated to `product_id=10` but `products.id=10` has `eliminado_en` set
- **WHEN** `DELETE /api/v1/categorias/5` is called (and no other guards trigger)
- **THEN** the response is 204

### Requirement: Recursive CTE for tree retrieval
The system SHALL implement `CategoryRepository.get_tree_cte()` using a SQL recursive CTE (PostgreSQL `WITH RECURSIVE`) that returns a flat list of `(id, nombre, padre_id, depth, path)` tuples for all non-deleted categories. The service SHALL nest the result into `CategoriaTreeNode` instances in Python (a single O(n) pass building a parent-to-children map). The CTE anchor SHALL select root nodes (`padre_id IS NULL AND eliminado_en IS NULL`); the recursive part SHALL join `categories` on `parent.id = child.padre_id` filtering `child.eliminado_en IS NULL`. (US-008 technical note + rúbrica)

#### Scenario: Repository exposes get_tree_cte
- **WHEN** `CategoryRepository` is introspected
- **THEN** it has a method `get_tree_cte() -> list[CategoriaFlatRow]` that executes a recursive CTE

#### Scenario: CTE excludes soft-deleted nodes
- **GIVEN** the `categories` table has 5 rows, 2 with `eliminado_en IS NOT NULL`
- **WHEN** `get_tree_cte()` is called
- **THEN** the result contains exactly 3 entries

### Requirement: Soft delete is the only delete mode
The system SHALL never expose a hard-delete endpoint for categories. The repository's `delete()` method SHALL set `eliminado_en` to the current UTC timestamp. (RN-CA09)

#### Scenario: No DELETE endpoint performs hard delete
- **WHEN** the OpenAPI schema for `/api/v1/categorias` is introspected
- **THEN** there is no endpoint that triggers `session.delete()` against `Categoria`

#### Scenario: Soft-deleted row is invisible to default queries
- **GIVEN** category `id=5` has `eliminado_en` set
- **WHEN** `repository.read(5)` is called
- **THEN** it returns `None` (filtered out by the soft-delete filter)

### Requirement: API versioned prefix and naming
The system SHALL mount the categories router under `/api/v1/categorias` with tag `categories`. All endpoints SHALL use the Spanish path segment `categorias` (matching `docs/Integrador.txt` §5 and US-007/008/009/010). (Integrador.txt §5)

#### Scenario: Endpoints respond under /api/v1/categorias
- **WHEN** a client calls `GET /api/v1/categorias`
- **THEN** the response is 200 (when fully wired)

#### Scenario: Endpoints do not respond at /categories or /api/categorias
- **WHEN** a client calls `GET /api/v1/categories` (English) or `GET /api/categorias` (no version)
- **THEN** the response is 404

### Requirement: Errors use RFC 7807 Problem Details
All error responses from category endpoints SHALL conform to RFC 7807 (`{type, title, status, detail, instance}`) via the existing exception handlers registered in `backend/main.py` (see `error-handling/spec.md`). Domain exceptions raised by the service (`NotFoundError`, `ConflictError`, `BusinessRuleError`, `ValidationError`, `ForbiddenError`, `UnauthorizedError`) SHALL be the only error path — no raw `HTTPException` from the router.

#### Scenario: NotFoundError yields RFC 7807 404
- **WHEN** a category endpoint raises `NotFoundError`
- **THEN** the response is 404 with body `{type, title: "Not Found", status: 404, detail, instance}`

#### Scenario: ConflictError yields RFC 7807 409
- **WHEN** the service raises `ConflictError` (duplicate name per level)
- **THEN** the response is 409 with `title: "Conflict"`

#### Scenario: BusinessRuleError yields RFC 7807 422
- **WHEN** the service raises `BusinessRuleError` (cycle, active children, active products)
- **THEN** the response is 422 with `title` matching the business-rule handler

### Requirement: Repository helper list_leaf_categories
The system SHALL provide `CategoryRepository.list_leaf_categories() -> list[Categoria]` that returns all active categories (`eliminado_en IS NULL`) that have zero non-deleted children. The query SHALL use a single SQL statement with a NOT EXISTS antijoin against `categories` self-referencing on `padre_id`. The result SHALL be ordered alphabetically by `nombre` ascending. The repository method SHALL NOT commit, flush, or otherwise mutate the session.

#### Scenario: Returns only leaves
- **GIVEN** categories: `Bebidas (id=1, padre=NULL, tiene hijas)`, `Gaseosas (id=2, padre=1, sin hijas)`, `Postres (id=3, padre=NULL, sin hijas)`
- **WHEN** `list_leaf_categories()` is called
- **THEN** the result contains `Gaseosas` and `Postres`, ordered alphabetically (Gaseosas first), and excludes `Bebidas`

#### Scenario: Soft-deleted categories are excluded from results
- **GIVEN** category `id=4` is a leaf but soft-deleted
- **WHEN** `list_leaf_categories()` is called
- **THEN** category 4 is not in the result

#### Scenario: A category whose only children are soft-deleted counts as a leaf
- **GIVEN** category `id=1` ("Bebidas") had child `id=2` ("Gaseosas") which is now soft-deleted
- **WHEN** `list_leaf_categories()` is called
- **THEN** `Bebidas` is included in the result (it has no active children anymore)

#### Scenario: Empty table returns empty list
- **GIVEN** the `categories` table has no non-deleted rows
- **WHEN** `list_leaf_categories()` is called
- **THEN** the result is `[]`
