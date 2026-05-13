## MODIFIED Requirements

### Requirement: Create product endpoint
The system SHALL expose `POST /api/v1/productos` protected by `require_role("ADMIN", "STOCK")` that accepts `ProductoCreate({nombre: str, descripcion: str | None, precio: Decimal, stock_cantidad: int = 0, disponible: bool = True, imagen_url: str | None, categoria_ids: list[int] | None = None})`. On success it SHALL return 201 with `ProductoRead`. The `nombre` field SHALL be validated `min_length=1, max_length=255`; `imagen_url` validated `max_length=500`. If `categoria_ids` is provided, the service SHALL validate that every id exists in the `categories` table (active rows only) before creating any associations; on failure SHALL raise `BusinessRuleError`. Additionally, if any id in `categoria_ids` references a category that has at least one non-deleted child (i.e. is NOT a leaf), the service SHALL raise `BusinessRuleError` (422) with a detail message listing the offending category name and the names of its active children, and SHALL NOT create the product. If `categoria_ids` is provided and the resulting set has zero active leaf categories (empty list or every id was already invalid), the post-mutation auto-disable hook SHALL set `disponible=false` on the newly created product. (US-015, US-016, RN-CA04, RN-CA05, RN-CA06)

#### Scenario: Successful product creation as ADMIN
- **WHEN** a user with role `ADMIN` posts `{"nombre": "Hamburguesa Clásica", "precio": 12.50, "stock_cantidad": 30}`
- **THEN** the response is 201 with body containing `id`, `nombre: "Hamburguesa Clásica"`, `precio: 12.50`, `stock_cantidad: 30`, `disponible: true`

#### Scenario: Successful product creation as STOCK with leaf categorias
- **GIVEN** active leaf categories with ids 1 and 2 exist (neither has active children)
- **WHEN** a user with role `STOCK` posts `{"nombre": "Pizza", "precio": 18.00, "categoria_ids": [1, 2]}`
- **THEN** the response is 201 AND rows exist in `product_categories` with `(product_id=<new>, category_id=1)` and `(product_id=<new>, category_id=2)` AND `disponible: true`

#### Scenario: Empty categoria_ids list creates product with no categories and auto-disables it
- **WHEN** a payload with `categoria_ids: []` is posted
- **THEN** the response is 201 AND no rows exist in `product_categories` for that product AND `disponible: false` (auto-disable hook)

#### Scenario: categoria_ids omitted leaves product without categories and disponible respects payload
- **WHEN** a payload omits the `categoria_ids` key entirely with `disponible: true`
- **THEN** the response is 201 AND no rows exist in `product_categories` for that product AND `disponible: true` (the auto-disable hook only runs after explicit category-set operations, not when categories are simply not provided)

#### Scenario: categoria_ids with non-existent id rejected
- **GIVEN** there is no active category with id 99999
- **WHEN** a payload with `categoria_ids: [1, 99999]` is posted
- **THEN** the response is 422 (`BusinessRuleError`) with detail referencing the missing categoria id AND no product is created

#### Scenario: categoria_ids with non-leaf category rejected
- **GIVEN** category 5 ("Bebidas") has active children with ids 6 ("Gaseosas") and 7 ("Alcohólicas")
- **WHEN** a user with role `ADMIN` posts `{"nombre": "Cerveza", "precio": 5.00, "categoria_ids": [5]}`
- **THEN** the response is 422 (`BusinessRuleError`) with detail mentioning "Bebidas" is not a leaf and listing "Gaseosas" and "Alcohólicas" as its active children AND no product is created

#### Scenario: Mix of leaf and non-leaf categoria_ids rejected
- **GIVEN** category 6 is a leaf and category 5 has active children
- **WHEN** a payload with `categoria_ids: [5, 6]` is posted
- **THEN** the response is 422 (`BusinessRuleError`) AND no product is created (atomicity preserved)

#### Scenario: Unauthenticated POST rejected
- **WHEN** an anonymous client posts to `/api/v1/productos`
- **THEN** the response is 401 (RFC 7807)

#### Scenario: CLIENT role forbidden on POST
- **WHEN** a user with role `CLIENT` posts a valid create payload
- **THEN** the response is 403 (RFC 7807) with `title: "Forbidden"`

#### Scenario: Empty nombre rejected
- **WHEN** a payload with `nombre: ""` is posted
- **THEN** the response is 422 (RFC 7807)

#### Scenario: Nombre longer than 255 rejected
- **WHEN** a payload with `nombre` of 256 characters is posted
- **THEN** the response is 422 (RFC 7807)

### Requirement: List products endpoint with combined filters
The system SHALL expose `GET /api/v1/productos` (public, no authentication required) that returns a paginated `PaginatedProductos({items: list[ProductoRead], total: int, page: int, limit: int})`. The endpoint SHALL accept query params `page: int >= 1` (default 1), `limit: int in [1, 100]` (default 20), `categoria_id: int | None`, `search: str | None`, `disponible: bool | None`, `excluir_alergenos: bool = False`, `excluir_alergeno_ids: list[int] = []`, `sin_categoria: bool = False`. When `disponible` is omitted, the default is `true` (RN-CA08 — public catalog hides unavailable products). Soft-deleted products (`eliminado_en IS NOT NULL`) SHALL always be excluded.

The `search` filter SHALL be case-insensitive substring match on `nombre`.

The `categoria_id` filter SHALL match products associated (via active `product_categories` rows) to the given category OR any of its active descendant categories, resolved via a recursive Common Table Expression that starts from the given id and walks down through `categories.padre_id`. Both anchor and recursive parts of the CTE SHALL filter `categories.eliminado_en IS NULL`.

The `excluir_alergenos` filter (boolean) SHALL exclude products that have at least one non-removable allergenic ingredient (active `product_ingredients` row joined with `ingredients.es_alergeno = true` and `pi.es_removible = false`).

The `excluir_alergeno_ids` filter (list of ingredient ids) SHALL exclude products that have at least one active `product_ingredients` row whose `ingredient_id` is in the list AND whose `es_removible = false`, regardless of the ingredient's `es_alergeno` flag. When the list is empty (default), the filter is a no-op.

When both `excluir_alergenos=true` and `excluir_alergeno_ids=[...]` are provided, both filters SHALL be applied with AND semantics (a product is included only if it passes both exclusion criteria).

The `sin_categoria` filter (boolean) SHALL, when `true`, restrict the result to products that have ZERO active `product_categories` rows. When `false` (default), the filter is a no-op. (US-018, US-023, RN-CA08, RN-CA09)

#### Scenario: Default list excludes unavailable
- **GIVEN** 3 products with `disponible=true` and 2 with `disponible=false`, all active
- **WHEN** `GET /api/v1/productos` is called (no query params)
- **THEN** the response is 200 with `total: 3` AND no item has `disponible: false`

#### Scenario: Default pagination returns first 20
- **GIVEN** 25 active available products exist
- **WHEN** `GET /api/v1/productos` is called
- **THEN** the response has `items.length == 20`, `total == 25`, `page == 1`, `limit == 20`

#### Scenario: Filter by categoria_id matches descendant products
- **GIVEN** category 1 ("Bebidas") has child category 2 ("Gaseosas") which has child category 3 ("Sin Azúcar"); product P1 is associated only with category 3
- **WHEN** `GET /api/v1/productos?categoria_id=1` is called
- **THEN** the response includes P1 (because P1 is in a descendant of category 1)

#### Scenario: Filter by categoria_id direct association still works
- **GIVEN** product P2 is associated directly with category 5 (a leaf)
- **WHEN** `GET /api/v1/productos?categoria_id=5` is called
- **THEN** the response includes P2

#### Scenario: Filter by categoria_id excludes products of sibling subtree
- **GIVEN** category 10 has child 11; category 20 has child 21; product P is only in category 21
- **WHEN** `GET /api/v1/productos?categoria_id=10` is called
- **THEN** the response excludes P

#### Scenario: Filter by categoria_id with soft-deleted descendant skipped
- **GIVEN** category 1 has child 2 (active) and child 3 (soft-deleted); product P is only in category 3
- **WHEN** `GET /api/v1/productos?categoria_id=1` is called
- **THEN** the response excludes P (the recursive CTE skips soft-deleted nodes)

#### Scenario: Filter by search case-insensitive
- **GIVEN** products with names "Pizza Margherita", "Pizza Napolitana", "Hamburguesa"
- **WHEN** `GET /api/v1/productos?search=PIZZA` is called
- **THEN** the response includes both pizzas and excludes the hamburger

#### Scenario: Filter disponible=false explicit
- **GIVEN** 3 disponible=true and 2 disponible=false products
- **WHEN** `GET /api/v1/productos?disponible=false` is called
- **THEN** the response has only the 2 unavailable products

#### Scenario: excluir_alergenos hides products with non-removable allergens
- **GIVEN** product P1 has ingredient I (es_alergeno=true) with `es_removible=false`; product P2 has ingredient I with `es_removible=true`; product P3 has no allergens
- **WHEN** `GET /api/v1/productos?excluir_alergenos=true` is called
- **THEN** the response includes P2 and P3, excludes P1

#### Scenario: excluir_alergeno_ids hides products that contain a banned ingredient as non-removable
- **GIVEN** ingredient id 50 ("maní"), ingredient id 51 ("gluten"); product P1 has ingredient 50 with `es_removible=false`; product P2 has ingredient 50 with `es_removible=true`; product P3 has only ingredient 51 (es_removible=false); product P4 has neither
- **WHEN** `GET /api/v1/productos?excluir_alergeno_ids=50` is called
- **THEN** the response includes P2, P3, P4, excludes P1

#### Scenario: excluir_alergeno_ids with multiple ids
- **GIVEN** the same setup as above
- **WHEN** `GET /api/v1/productos?excluir_alergeno_ids=50&excluir_alergeno_ids=51` is called
- **THEN** the response includes P2 and P4 only

#### Scenario: excluir_alergeno_ids empty is no-op
- **WHEN** `GET /api/v1/productos?excluir_alergeno_ids=` is called with no values (or the param omitted)
- **THEN** the response is 200 and the filter behaves as if no exclusion list was provided

#### Scenario: excluir_alergenos and excluir_alergeno_ids combined with AND
- **GIVEN** product P1 has only a non-flagged ingredient 50 (es_alergeno=false) non-removable; product P2 has flagged ingredient 60 (es_alergeno=true) non-removable; product P3 has both 50 (es_removible=false) and 60 (es_removible=false)
- **WHEN** `GET /api/v1/productos?excluir_alergenos=true&excluir_alergeno_ids=50` is called
- **THEN** the response excludes P2 (boolean filter) and excludes P1 and P3 (list filter on id 50); only products that pass BOTH are returned

#### Scenario: sin_categoria=true returns only products without any active category
- **GIVEN** product P1 has 2 active category associations; product P2 has 1 association soft-deleted, 0 active; product P3 has no rows in product_categories
- **WHEN** `GET /api/v1/productos?sin_categoria=true&disponible=false` is called (override default to include unavailable)
- **THEN** the response includes P2 and P3, excludes P1

#### Scenario: sin_categoria=false is no-op
- **WHEN** `GET /api/v1/productos?sin_categoria=false` is called
- **THEN** the response is identical to calling without the param

#### Scenario: Combined filters AND together (recursive category + allergen ids + sin_categoria)
- **WHEN** `GET /api/v1/productos?categoria_id=1&excluir_alergeno_ids=50&sin_categoria=false&disponible=true` is called
- **THEN** the response includes only products that are: associated with category 1 or any active descendant AND have no non-removable ingredient 50 AND are available

#### Scenario: Empty result when filters match nothing
- **WHEN** filters yield no matching products
- **THEN** the response is 200 with `items: []`, `total: 0`

#### Scenario: Soft-deleted products excluded
- **GIVEN** product P1 is soft-deleted (`eliminado_en` set), P2 is active
- **WHEN** `GET /api/v1/productos` is called
- **THEN** P1 is excluded from items regardless of any other filter

#### Scenario: limit above 100 rejected
- **WHEN** `GET /api/v1/productos?limit=200` is called
- **THEN** the response is 422

#### Scenario: page=0 rejected
- **WHEN** `GET /api/v1/productos?page=0` is called
- **THEN** the response is 422

#### Scenario: List endpoint is public
- **WHEN** an anonymous client calls `GET /api/v1/productos`
- **THEN** the response is 200 (no auth required)

### Requirement: Set categorias endpoint (bulk replace)
The system SHALL expose `PUT /api/v1/productos/{id}/categorias` protected by `require_role("ADMIN", "STOCK")` that accepts `SetCategorias({categoria_ids: list[int]})` and **replaces** the entire set of category associations for the product. The service SHALL validate every id in `categoria_ids` exists as an active row in `categories` BEFORE modifying any pivot rows; on failure SHALL raise `BusinessRuleError` (422) without partial changes. Additionally, the service SHALL validate that every id in `categoria_ids` references a leaf category (no active children); on failure SHALL raise `BusinessRuleError` (422) listing the offending category name and the names of its active children, without modifying any pivot rows. After the pivot replace succeeds, the service SHALL invoke the auto-disable hook: if the resulting count of active leaf categories for the product is zero, the service SHALL set `disponible=false` on the product. On success it SHALL return 200 with the updated `ProductoDetail`. Empty list `[]` is valid and removes all associations (which triggers auto-disable). (US-016, RN-CA06)

#### Scenario: Replace with new set of leaf categories
- **GIVEN** product 5 is associated with leaf categories [1, 2]; categories 2 and 3 are leaves
- **WHEN** PUT `/api/v1/productos/5/categorias` with `{"categoria_ids": [2, 3]}`
- **THEN** the response is 200 AND the product is now associated with [2, 3] only AND `disponible` is unchanged from before

#### Scenario: Empty list removes all associations and auto-disables
- **GIVEN** product 5 is associated with categories [1, 2] AND `disponible: true`
- **WHEN** PUT `/api/v1/productos/5/categorias` with `{"categoria_ids": []}`
- **THEN** the response is 200 AND the product has no category associations AND `disponible: false`

#### Scenario: Replace with non-leaf categoria_id rejected
- **GIVEN** product 5 is associated with category 6 (a leaf); category 1 has active children [2, 3]
- **WHEN** PUT `/api/v1/productos/5/categorias` with `{"categoria_ids": [1]}`
- **THEN** the response is 422 (`BusinessRuleError`) with detail mentioning category 1's children AND the product is still associated only with category 6 (no rows changed)

#### Scenario: Non-existent categoria_id rejected, no partial changes
- **GIVEN** product 5 is associated with category 1; category 99999 does not exist
- **WHEN** PUT `/api/v1/productos/5/categorias` with `{"categoria_ids": [1, 99999]}`
- **THEN** the response is 422 (`BusinessRuleError`) AND product 5 is still associated only with category 1 (no rows added or removed)

#### Scenario: Soft-deleted associations are reactivated
- **GIVEN** product 5 had a row `(product_id=5, category_id=2)` that was soft-deleted; category 2 is a leaf
- **WHEN** PUT `/api/v1/productos/5/categorias` with `{"categoria_ids": [2]}`
- **THEN** the response is 200 AND the existing pivot row has `eliminado_en` set back to `NULL` (no duplicate row inserted)

#### Scenario: Non-existent product returns 404
- **WHEN** PUT `/api/v1/productos/99999/categorias` is called
- **THEN** the response is 404

#### Scenario: CLIENT role forbidden
- **WHEN** a user with role `CLIENT` calls the endpoint
- **THEN** the response is 403

## ADDED Requirements

### Requirement: Leaf-only validation helper for product category assignment
The system SHALL provide a service-level helper `ProductService._validate_categorias_are_leaves(categoria_ids: list[int], session)` that, given a list of category ids known to exist and be active, verifies each id points to a leaf category (no active children). The helper SHALL execute a single bulk query against `categories` filtering `padre_id IN :ids AND eliminado_en IS NULL`; if any rows are returned, the helper SHALL raise `BusinessRuleError` whose `detail` includes the offending category name(s) and the names of their active children in Spanish (Rioplatense), suitable for direct display in admin UI error toasts. The helper SHALL be invoked from both `ProductService.create()` (when `payload.categoria_ids` is non-empty) and `ProductService.set_categorias()` before any mutation of `product_categories`. The helper SHALL NOT commit, flush, or otherwise mutate the session.

#### Scenario: All categories are leaves passes silently
- **GIVEN** categories 6 and 7 exist, active, with no active children
- **WHEN** the helper is invoked with `[6, 7]`
- **THEN** no exception is raised AND no rows in `categories` are read beyond the existence check

#### Scenario: One non-leaf category raises with actionable message
- **GIVEN** category 5 ("Bebidas") has active child 6 ("Gaseosas")
- **WHEN** the helper is invoked with `[5]`
- **THEN** the helper raises `BusinessRuleError` whose detail contains the substring "Bebidas" AND the substring "Gaseosas"

#### Scenario: Multiple non-leaf categories all reported
- **GIVEN** category 1 has child 11, category 2 has child 22, category 3 has no children
- **WHEN** the helper is invoked with `[1, 2, 3]`
- **THEN** the helper raises `BusinessRuleError` whose detail mentions both category 1 and category 2 (and their children) but not category 3

#### Scenario: Soft-deleted children do not block
- **GIVEN** category 5 has child 6 which is soft-deleted (eliminado_en IS NOT NULL)
- **WHEN** the helper is invoked with `[5]`
- **THEN** no exception is raised (category 5 is effectively a leaf because its only child is soft-deleted)

#### Scenario: Empty list is a no-op
- **WHEN** the helper is invoked with `[]`
- **THEN** no exception is raised AND no DB query is issued

### Requirement: Auto-disable product when no active leaf category remains
The system SHALL provide a service-level hook `ProductService._auto_disable_if_no_leaf_categoria(product_id: int, session)` that, after any operation in `ProductService` that mutates the set of category associations of a product (`create()` when `categoria_ids` is provided, and `set_categorias()`), counts the active leaf-category associations of the product. If the count is zero, the hook SHALL set `disponible=false` on the product within the same UnitOfWork (no separate transaction) and SHALL emit a log entry at INFO level using the message template "Producto {id} desactivado: sin categoría hoja activa". If the count is greater than zero, the hook SHALL be a no-op (no log, no mutation).

"Active leaf-category association" means: a row in `product_categories` with `eliminado_en IS NULL`, pointing to a row in `categories` with `eliminado_en IS NULL` that has zero non-deleted children.

The hook SHALL NOT re-enable a product whose `disponible` is already `true` after a category change (re-enabling is the admin's explicit responsibility via `PATCH /productos/{id}/disponibilidad`).

#### Scenario: Product with one active leaf category stays as-is
- **GIVEN** product 5 has `disponible: true` and is associated with leaf category 6
- **WHEN** `set_categorias(5, [6])` is called (idempotent replace)
- **THEN** `disponible` remains `true` AND no log line is emitted

#### Scenario: Product with empty category set is auto-disabled
- **GIVEN** product 5 has `disponible: true` and is associated with leaf category 6
- **WHEN** `set_categorias(5, [])` is called
- **THEN** `disponible` is `false` AND a log entry "Producto 5 desactivado: sin categoría hoja activa" is emitted at INFO level

#### Scenario: Product with all associated categories soft-deleted is auto-disabled
- **GIVEN** product 5 has `disponible: true` and is associated with category 6; category 6 is then soft-deleted out of band (via admin); the next call replaces categorias with `[]`
- **WHEN** `set_categorias(5, [])` is called
- **THEN** `disponible` is `false`

#### Scenario: Hook does not re-enable
- **GIVEN** product 5 has `disponible: false` (previously disabled manually) and has leaf category 6 associated
- **WHEN** `set_categorias(5, [6, 7])` is called (both 6 and 7 are leaves)
- **THEN** `disponible` remains `false` (hook does not re-enable)

#### Scenario: Creation with categoria_ids=[] auto-disables
- **GIVEN** a user with role `ADMIN`
- **WHEN** POST `/api/v1/productos` is called with `{"nombre": "X", "precio": 10, "categoria_ids": [], "disponible": true}`
- **THEN** the response is 201 with `disponible: false` AND the log line is emitted
