## MODIFIED Requirements

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

### Requirement: Create category endpoint
The system SHALL expose `POST /api/v1/categorias` protected by `require_role("ADMIN", "STOCK")` that accepts `CategoriaCreate({nombre: str, padre_id: int | None})`. On success it SHALL return 201 with `CategoriaRead`. The `nombre` field SHALL be trimmed and validated with `min_length=1, max_length=100`. Additionally, when `padre_id` is not null, the service SHALL verify that the parent category has zero active product associations (`SELECT COUNT(*) FROM product_categories pc JOIN products p ON p.id = pc.product_id WHERE pc.category_id = :padre_id AND pc.eliminado_en IS NULL AND p.eliminado_en IS NULL`). If the count is greater than zero, the service SHALL raise `BusinessRuleError` (422) with detail message in Spanish (Rioplatense) including the count of affected products, e.g. "No se puede subcategorizar 'Bebidas' — tiene 5 productos asignados. Reasigná los productos a una subcategoría antes de crear hijas." (US-007)

#### Scenario: Successful root category creation as ADMIN
- **WHEN** a user with role `ADMIN` posts `{"nombre": "Bebidas", "padre_id": null}`
- **THEN** the response is 201 with body `{"id": <int>, "nombre": "Bebidas", "padre_id": null, ...}`

#### Scenario: Successful subcategory creation when parent has no products
- **GIVEN** a root category `id=5` ("Bebidas") with zero active product associations
- **WHEN** a user with role `STOCK` posts `{"nombre": "Gaseosas", "padre_id": 5}`
- **THEN** the response is 201 with `padre_id: 5`

#### Scenario: Subcategory creation rejected when parent has active products
- **GIVEN** a leaf category `id=5` ("Bebidas") with 3 active product associations
- **WHEN** a user with role `ADMIN` posts `{"nombre": "Gaseosas", "padre_id": 5}`
- **THEN** the response is 422 (`BusinessRuleError`) with detail mentioning "Bebidas", "3 productos", and the word "subcategoría" or "subcategorizar" AND no new row exists in `categories`

#### Scenario: Subcategory allowed when parent's products are soft-deleted
- **GIVEN** category `id=5` has 2 product associations but both products have `eliminado_en` set
- **WHEN** a user with role `ADMIN` posts `{"nombre": "Gaseosas", "padre_id": 5}`
- **THEN** the response is 201 (soft-deleted products do not count toward the guard)

#### Scenario: Subcategory allowed when association rows are soft-deleted but products are active
- **GIVEN** category `id=5` has 1 pivot row with `eliminado_en IS NOT NULL` pointing to an active product, and no other pivot rows
- **WHEN** a user with role `ADMIN` posts `{"nombre": "Gaseosas", "padre_id": 5}`
- **THEN** the response is 201 (the inactive pivot row does not block subcategorization)

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
- **THEN** the response is 422 with `BusinessRuleError` detail referencing the missing parent id

## ADDED Requirements

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
