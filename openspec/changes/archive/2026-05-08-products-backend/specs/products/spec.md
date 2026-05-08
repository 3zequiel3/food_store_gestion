## ADDED Requirements

### Requirement: Producto entity model
The system SHALL persist products in the existing `products` table (created in migration `20260428_0001_initial_schema`, lines 313-338) with columns `id BIGSERIAL`, `nombre VARCHAR(255) NOT NULL` (indexed), `descripcion TEXT NULL`, `precio NUMERIC(10,2) NOT NULL` with `CHECK (precio > 0)` constraint `ck_products_precio_positivo`, `stock_cantidad INTEGER NOT NULL DEFAULT 0` with `CHECK (stock_cantidad >= 0)` constraint `ck_products_stock_no_negativo`, `disponible BOOLEAN NOT NULL DEFAULT true` (indexed), `imagen_url VARCHAR(500) NULL`, plus the standard `creado_en/actualizado_en/eliminado_en TIMESTAMPTZ` columns from `BaseModel`. The ORM class `Producto` defined in `backend/features/products/models.py` (lines 82-123) SHALL be the single source of truth — the new module rules MUST import it, not redefine it. (RN-CA04, RN-CA05, RN-CA09)

#### Scenario: Producto has precio and stock CHECK constraints
- **WHEN** the `products` table schema is introspected
- **THEN** there exists a CHECK constraint named `ck_products_precio_positivo` enforcing `precio > 0` AND a CHECK constraint named `ck_products_stock_no_negativo` enforcing `stock_cantidad >= 0`

#### Scenario: Producto inherits soft-delete from BaseModel
- **WHEN** a `Producto` instance is loaded from the database
- **THEN** it exposes attributes `id`, `nombre`, `descripcion`, `precio`, `stock_cantidad`, `disponible`, `imagen_url`, `creado_en`, `actualizado_en`, `eliminado_en` and `eliminado_en` is `None` for active rows

#### Scenario: Producto is reused, not redefined
- **WHEN** `backend.features.products.repository` is imported
- **THEN** it imports `Producto` from `backend.features.products.models` and does NOT declare a new SQLAlchemy class with `__tablename__ = "products"`

### Requirement: ProductoIngrediente pivot has es_removible flag
The system SHALL extend the existing pivot table `product_ingredients` (created in migration `20260428_0001`, lines 376-406) with a new column `es_removible BOOLEAN NOT NULL DEFAULT false` via a dedicated Alembic migration (`add_es_removible_to_product_ingredients`). The ORM class `ProductoIngrediente` in `backend/features/products/models.py` SHALL declare the column as `Mapped[bool] = mapped_column(Boolean, nullable=False, default=False, server_default=sa.false())` so that SQLAlchemy and the database stay aligned. The migration SHALL set `down_revision = '77bcb99d97db'`. (RN-CA07, ERD §3.2)

#### Scenario: Migration adds es_removible column
- **WHEN** `alembic upgrade head` is executed against a fresh database
- **THEN** the `product_ingredients` table contains the column `es_removible boolean NOT NULL DEFAULT false`

#### Scenario: Existing rows get default false on upgrade
- **GIVEN** the table `product_ingredients` had rows before the new migration
- **WHEN** `alembic upgrade head` is executed
- **THEN** those rows have `es_removible = false` (no NOT NULL violation)

#### Scenario: Downgrade removes the column
- **WHEN** `alembic downgrade -1` is executed
- **THEN** the column `es_removible` no longer exists in `product_ingredients`

#### Scenario: ORM model declares es_removible
- **WHEN** the class `ProductoIngrediente` is introspected
- **THEN** it has an attribute `es_removible: Mapped[bool]` and the SQLAlchemy column has `nullable=False`, `default=False`, and `server_default=sa.false()`

### Requirement: Decimal precision for precio in API schemas
The Pydantic schemas SHALL declare `precio` as `Decimal` (NOT `float`) with `max_digits=10, decimal_places=2` and configure `model_config = {"from_attributes": True}` on read schemas. This preserves NUMERIC(10,2) precision across the JSON boundary even though the SQLAlchemy ORM attribute is type-hinted `Mapped[float]` (a documented smell that is NOT modified in this change). (RN-CA04)

#### Scenario: POST preserves decimal precision
- **WHEN** a user with role `ADMIN` posts `{"nombre": "Pizza", "precio": 19.99, "stock_cantidad": 10}`
- **THEN** `GET /api/v1/productos/{id}` returns `precio: 19.99` (NOT `19.989999...` or `19.99000001`)

#### Scenario: precio = 0 rejected
- **WHEN** a payload with `precio: 0` is posted
- **THEN** the response is 422 (Pydantic Field constraint `gt=0`)

#### Scenario: precio negative rejected
- **WHEN** a payload with `precio: -1.50` is posted
- **THEN** the response is 422 (RFC 7807)

#### Scenario: precio with more than 2 decimals rejected
- **WHEN** a payload with `precio: 19.999` is posted
- **THEN** the response is 422 (Pydantic constraint `decimal_places=2`)

### Requirement: Create product endpoint
The system SHALL expose `POST /api/v1/productos` protected by `require_role("ADMIN", "STOCK")` that accepts `ProductoCreate({nombre: str, descripcion: str | None, precio: Decimal, stock_cantidad: int = 0, disponible: bool = True, imagen_url: str | None, categoria_ids: list[int] | None = None})`. On success it SHALL return 201 with `ProductoRead`. The `nombre` field SHALL be validated `min_length=1, max_length=255`; `imagen_url` validated `max_length=500`. If `categoria_ids` is provided, the service SHALL validate that every id exists in the `categories` table (active rows only) before creating any associations; on failure SHALL raise `BusinessRuleError`. (US-015, US-016, RN-CA04, RN-CA05, RN-CA06)

#### Scenario: Successful product creation as ADMIN
- **WHEN** a user with role `ADMIN` posts `{"nombre": "Hamburguesa Clásica", "precio": 12.50, "stock_cantidad": 30}`
- **THEN** the response is 201 with body containing `id`, `nombre: "Hamburguesa Clásica"`, `precio: 12.50`, `stock_cantidad: 30`, `disponible: true`

#### Scenario: Successful product creation as STOCK with categorias
- **GIVEN** active categories with ids 1 and 2 exist
- **WHEN** a user with role `STOCK` posts `{"nombre": "Pizza", "precio": 18.00, "categoria_ids": [1, 2]}`
- **THEN** the response is 201 AND rows exist in `product_categories` with `(product_id=<new>, category_id=1)` and `(product_id=<new>, category_id=2)`

#### Scenario: Empty categoria_ids list creates product with no categories
- **WHEN** a payload with `categoria_ids: []` is posted
- **THEN** the response is 201 AND no rows exist in `product_categories` for that product

#### Scenario: categoria_ids omitted leaves product without categories
- **WHEN** a payload omits the `categoria_ids` key entirely
- **THEN** the response is 201 AND no rows exist in `product_categories` for that product

#### Scenario: categoria_ids with non-existent id rejected
- **GIVEN** there is no active category with id 99999
- **WHEN** a payload with `categoria_ids: [1, 99999]` is posted
- **THEN** the response is 422 (`BusinessRuleError`) with detail referencing the missing categoria id AND no product is created

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
The system SHALL expose `GET /api/v1/productos` (public, no authentication required) that returns a paginated `PaginatedProductos({items: list[ProductoRead], total: int, page: int, limit: int})`. The endpoint SHALL accept query params `page: int >= 1` (default 1), `limit: int in [1, 100]` (default 20), `categoria_id: int | None`, `search: str | None`, `disponible: bool | None`, `excluir_alergenos: bool = False`. When `disponible` is omitted, the default is `true` (RN-CA08 — public catalog hides unavailable products). Soft-deleted products (`eliminado_en IS NOT NULL`) SHALL always be excluded. The `search` filter SHALL be case-insensitive substring match on `nombre` (`LOWER(nombre) LIKE LOWER('%pattern%')` for portability across PostgreSQL and SQLite). The `excluir_alergenos` filter SHALL exclude products that have at least one non-removable allergenic ingredient (i.e. an active row in `product_ingredients` joined with `ingredients.es_alergeno = true` and `pi.es_removible = false`). (US-018, US-023, RN-CA08, RN-CA09)

#### Scenario: Default list excludes unavailable
- **GIVEN** 3 products with `disponible=true` and 2 with `disponible=false`, all active
- **WHEN** `GET /api/v1/productos` is called (no query params)
- **THEN** the response is 200 with `total: 3` AND no item has `disponible: false`

#### Scenario: Default pagination returns first 20
- **GIVEN** 25 active available products exist
- **WHEN** `GET /api/v1/productos` is called
- **THEN** the response has `items.length == 20`, `total == 25`, `page == 1`, `limit == 20`

#### Scenario: Filter by categoria_id
- **GIVEN** product P1 is associated with category 5, product P2 is not
- **WHEN** `GET /api/v1/productos?categoria_id=5` is called
- **THEN** the response includes P1 and excludes P2

#### Scenario: Filter by search case-insensitive
- **GIVEN** products with names "Pizza Margherita", "Pizza Napolitana", "Hamburguesa"
- **WHEN** `GET /api/v1/productos?search=PIZZA` is called
- **THEN** the response includes both pizzas and excludes the hamburger

#### Scenario: Filter by search substring
- **GIVEN** products with names "Pizza Especial" and "Especial del día"
- **WHEN** `GET /api/v1/productos?search=especial` is called
- **THEN** the response includes both products

#### Scenario: Filter disponible=false explicit
- **GIVEN** 3 disponible=true and 2 disponible=false products
- **WHEN** `GET /api/v1/productos?disponible=false` is called
- **THEN** the response has only the 2 unavailable products

#### Scenario: excluir_alergenos hides products with non-removable allergens
- **GIVEN** product P1 has ingredient I (es_alergeno=true) with `es_removible=false`; product P2 has ingredient I with `es_removible=true`; product P3 has no allergens
- **WHEN** `GET /api/v1/productos?excluir_alergenos=true` is called
- **THEN** the response includes P2 and P3, excludes P1

#### Scenario: Combined filters AND together
- **WHEN** `GET /api/v1/productos?categoria_id=5&search=pizza&disponible=true&excluir_alergenos=true` is called
- **THEN** the response includes only products that are: associated with category 5 AND match "pizza" in name AND available AND have no non-removable allergens

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

### Requirement: Get product detail endpoint
The system SHALL expose `GET /api/v1/productos/{id}` (public) that returns `ProductoDetail` with the product fields plus `categorias: list[CategoriaRead]` and `ingredientes: list[IngredienteAsociadoRead]` (each ingredient includes `es_removible`). The endpoint SHALL return 404 for soft-deleted or non-existent products. Categories and ingredients listed SHALL be active (`eliminado_en IS NULL` on both pivot row and target row). (US-019, RN-CA08)

#### Scenario: Returns full detail with associations
- **GIVEN** product P with id 5, associated to categories [1,2] and ingredients [{id: 10, es_removible: true}, {id: 11, es_removible: false}]; ingredient 10 has `es_alergeno=true`, 11 has `es_alergeno=false`
- **WHEN** `GET /api/v1/productos/5` is called
- **THEN** the response is 200 with body containing `categorias: [{id:1,...},{id:2,...}]` AND `ingredientes` containing the two entries with the correct `es_removible` and `es_alergeno` flags

#### Scenario: Non-existent product returns 404
- **WHEN** `GET /api/v1/productos/99999` is called
- **THEN** the response is 404 (RFC 7807)

#### Scenario: Soft-deleted product returns 404
- **GIVEN** product id 5 has `eliminado_en` set
- **WHEN** `GET /api/v1/productos/5` is called
- **THEN** the response is 404

#### Scenario: Soft-deleted association is excluded
- **GIVEN** product 5 has a row in `product_ingredients` pointing to ingredient 10, but the pivot row has `eliminado_en` set
- **WHEN** `GET /api/v1/productos/5` is called
- **THEN** the response excludes ingredient 10 from the `ingredientes` array

#### Scenario: Detail endpoint is public
- **WHEN** an anonymous client calls `GET /api/v1/productos/{id}`
- **THEN** the response is 200 (when product is active)

### Requirement: Update product endpoint
The system SHALL expose `PUT /api/v1/productos/{id}` protected by `require_role("ADMIN", "STOCK")` that accepts `ProductoUpdate` (all fields optional: `nombre`, `descripcion`, `precio`, `stock_cantidad`, `disponible`, `imagen_url`). The service SHALL apply the partial update via `model_dump(exclude_unset=True)` to preserve fields the client did not send. The payload SHALL NOT accept `categoria_ids` (categories are managed via the dedicated `PUT /{id}/categorias` endpoint). On success it SHALL return 200 with `ProductoRead`. (US-020, RN-CA04, RN-CA05)

#### Scenario: Successful name update preserves other fields
- **GIVEN** product 5 with `precio=12.50, stock_cantidad=20, disponible=true`
- **WHEN** PUT `/api/v1/productos/5` with `{"nombre": "Nuevo nombre"}`
- **THEN** the response is 200 with `nombre: "Nuevo nombre"`, `precio: 12.50`, `stock_cantidad: 20`, `disponible: true`

#### Scenario: Successful precio update
- **WHEN** PUT `/api/v1/productos/5` with `{"precio": 15.00}`
- **THEN** the response is 200 with `precio: 15.00`

#### Scenario: precio = 0 on update rejected
- **WHEN** PUT `/api/v1/productos/5` with `{"precio": 0}`
- **THEN** the response is 422

#### Scenario: stock_cantidad negative on update rejected
- **WHEN** PUT `/api/v1/productos/5` with `{"stock_cantidad": -1}`
- **THEN** the response is 422

#### Scenario: Non-existent product returns 404
- **WHEN** PUT `/api/v1/productos/99999` with any payload
- **THEN** the response is 404

#### Scenario: Soft-deleted product returns 404
- **GIVEN** product id 5 has `eliminado_en` set
- **WHEN** PUT `/api/v1/productos/5` with any payload
- **THEN** the response is 404

#### Scenario: CLIENT role forbidden on PUT
- **WHEN** a user with role `CLIENT` calls PUT
- **THEN** the response is 403

### Requirement: Patch disponibilidad endpoint
The system SHALL expose `PATCH /api/v1/productos/{id}/disponibilidad` protected by `require_role("ADMIN", "STOCK")` that accepts `PatchDisponibilidad({disponible: bool})` and updates only the `disponible` flag. On success it SHALL return 200 with `ProductoRead`. (US-022)

#### Scenario: Toggle to false hides from public catalog
- **GIVEN** product 5 with `disponible: true`
- **WHEN** PATCH `/api/v1/productos/5/disponibilidad` with `{"disponible": false}`
- **THEN** the response is 200 with `disponible: false` AND `GET /api/v1/productos` (default `disponible=true`) excludes product 5

#### Scenario: Toggle back to true makes product visible
- **GIVEN** product 5 with `disponible: false`
- **WHEN** PATCH `/api/v1/productos/5/disponibilidad` with `{"disponible": true}`
- **THEN** the response is 200 AND `GET /api/v1/productos` (default) includes product 5

#### Scenario: Non-existent product returns 404
- **WHEN** PATCH `/api/v1/productos/99999/disponibilidad` is called
- **THEN** the response is 404

#### Scenario: CLIENT role forbidden
- **WHEN** a user with role `CLIENT` calls the endpoint
- **THEN** the response is 403

### Requirement: Patch stock endpoint (absolute set)
The system SHALL expose `PATCH /api/v1/productos/{id}/stock` protected by `require_role("ADMIN", "STOCK")` that accepts `PatchStock({stock_cantidad: int})` and **absolutely sets** the new value (NOT increment). The service SHALL validate `stock_cantidad >= 0` and reject negatives with `BusinessRuleError` (422). The DB CHECK constraint `ck_products_stock_no_negativo` is the second line of defense. On success it SHALL return 200 with `ProductoRead`. The optimistic locking required for stock decrements at order creation is OUT OF SCOPE for this endpoint (it is `order-creation-backend` responsibility per RN-PE04). (US-021, RN-CA05)

#### Scenario: Set stock to non-zero
- **GIVEN** product 5 with `stock_cantidad: 10`
- **WHEN** PATCH `/api/v1/productos/5/stock` with `{"stock_cantidad": 50}`
- **THEN** the response is 200 with `stock_cantidad: 50`

#### Scenario: Set stock to zero
- **WHEN** PATCH `/api/v1/productos/5/stock` with `{"stock_cantidad": 0}`
- **THEN** the response is 200 with `stock_cantidad: 0`

#### Scenario: Negative stock rejected
- **WHEN** PATCH `/api/v1/productos/5/stock` with `{"stock_cantidad": -1}`
- **THEN** the response is 422 (RFC 7807)

#### Scenario: Non-existent product returns 404
- **WHEN** PATCH `/api/v1/productos/99999/stock` is called
- **THEN** the response is 404

#### Scenario: CLIENT role forbidden
- **WHEN** a user with role `CLIENT` calls the endpoint
- **THEN** the response is 403

### Requirement: Soft delete product endpoint
The system SHALL expose `DELETE /api/v1/productos/{id}` protected by `require_role("ADMIN", "STOCK")` that performs a soft delete (`eliminado_en = now()`). The endpoint MUST NEVER perform a hard delete and MUST NOT cascade-delete rows in `product_categories` or `product_ingredients`. On success it SHALL return 204 with empty body. After soft delete: `GET /api/v1/productos/{id}` returns 404 and `GET /api/v1/productos` excludes the row. (US-022, RN-CA09)

#### Scenario: Successful soft delete
- **GIVEN** product 5 is active
- **WHEN** a user with role `ADMIN` calls `DELETE /api/v1/productos/5`
- **THEN** the response is 204 AND the row in `products` has `eliminado_en IS NOT NULL` (NOT physically removed)

#### Scenario: Hard delete never happens
- **WHEN** any DELETE request succeeds
- **THEN** the row count of `products` (including soft-deleted) is unchanged

#### Scenario: Pivot rows are not modified
- **GIVEN** product 5 has rows in `product_categories` and `product_ingredients`
- **WHEN** `DELETE /api/v1/productos/5` is called
- **THEN** the response is 204 AND the pivot rows still exist with `eliminado_en IS NULL` (the public catalog filters by `products.eliminado_en IS NULL` so they appear orphaned but do not break)

#### Scenario: Already-deleted product returns 404
- **GIVEN** product id 5 was previously soft-deleted
- **WHEN** `DELETE /api/v1/productos/5` is called again
- **THEN** the response is 404

#### Scenario: Non-existent product returns 404
- **WHEN** `DELETE /api/v1/productos/99999` is called
- **THEN** the response is 404

#### Scenario: CLIENT role forbidden
- **WHEN** a user with role `CLIENT` calls the endpoint
- **THEN** the response is 403

### Requirement: Set categorias endpoint (bulk replace)
The system SHALL expose `PUT /api/v1/productos/{id}/categorias` protected by `require_role("ADMIN", "STOCK")` that accepts `SetCategorias({categoria_ids: list[int]})` and **replaces** the entire set of category associations for the product. The service SHALL validate every id in `categoria_ids` exists as an active row in `categories` BEFORE modifying any pivot rows; on failure SHALL raise `BusinessRuleError` (422) without partial changes. On success it SHALL return 200 with the updated `ProductoDetail`. Empty list `[]` is valid and removes all associations. (US-016, RN-CA06)

#### Scenario: Replace with new set
- **GIVEN** product 5 is associated with categories [1, 2]
- **WHEN** PUT `/api/v1/productos/5/categorias` with `{"categoria_ids": [2, 3]}`
- **THEN** the response is 200 AND the product is now associated with [2, 3] only (1 removed, 3 added)

#### Scenario: Empty list removes all associations
- **GIVEN** product 5 is associated with categories [1, 2]
- **WHEN** PUT `/api/v1/productos/5/categorias` with `{"categoria_ids": []}`
- **THEN** the response is 200 AND the product has no category associations

#### Scenario: Non-existent categoria_id rejected, no partial changes
- **GIVEN** product 5 is associated with category 1; category 99999 does not exist
- **WHEN** PUT `/api/v1/productos/5/categorias` with `{"categoria_ids": [1, 99999]}`
- **THEN** the response is 422 (`BusinessRuleError`) AND product 5 is still associated only with category 1 (no rows added or removed)

#### Scenario: Soft-deleted associations are reactivated
- **GIVEN** product 5 had a row `(product_id=5, category_id=2)` that was soft-deleted
- **WHEN** PUT `/api/v1/productos/5/categorias` with `{"categoria_ids": [2]}`
- **THEN** the response is 200 AND the existing pivot row has `eliminado_en` set back to `NULL` (no duplicate row inserted)

#### Scenario: Non-existent product returns 404
- **WHEN** PUT `/api/v1/productos/99999/categorias` is called
- **THEN** the response is 404

#### Scenario: CLIENT role forbidden
- **WHEN** a user with role `CLIENT` calls the endpoint
- **THEN** the response is 403

### Requirement: List ingredientes of product endpoint
The system SHALL expose `GET /api/v1/productos/{id}/ingredientes` (public) that returns `list[IngredienteAsociadoRead]` where each item contains `id`, `nombre`, `es_alergeno` (from the `ingredients` table) and `es_removible` (from the `product_ingredients` pivot row). Only active pivot rows AND active ingredients SHALL be returned. (US-017, RN-CA07)

#### Scenario: Returns associated ingredients with flags
- **GIVEN** product 5 has ingredients [{id: 10, es_alergeno: true, es_removible: false}, {id: 11, es_alergeno: false, es_removible: true}]
- **WHEN** `GET /api/v1/productos/5/ingredientes` is called
- **THEN** the response is 200 with body `[{id: 10, nombre: ..., es_alergeno: true, es_removible: false}, {id: 11, nombre: ..., es_alergeno: false, es_removible: true}]`

#### Scenario: Soft-deleted association excluded
- **GIVEN** product 5 has pivot rows (id 10 active, id 11 with `eliminado_en` set)
- **WHEN** `GET /api/v1/productos/5/ingredientes` is called
- **THEN** the response includes only ingredient 10

#### Scenario: Soft-deleted ingredient excluded
- **GIVEN** product 5's pivot to ingredient 10 is active but ingredient 10 itself has `eliminado_en` set
- **WHEN** the endpoint is called
- **THEN** ingredient 10 is excluded from the response

#### Scenario: Non-existent product returns 404
- **WHEN** `GET /api/v1/productos/99999/ingredientes` is called
- **THEN** the response is 404

#### Scenario: Empty list when no ingredients
- **GIVEN** product 5 has no associated ingredients
- **WHEN** the endpoint is called
- **THEN** the response is 200 with body `[]`

#### Scenario: Endpoint is public
- **WHEN** an anonymous client calls the endpoint
- **THEN** the response is 200

### Requirement: Add ingrediente association endpoint
The system SHALL expose `POST /api/v1/productos/{id}/ingredientes` protected by `require_role("ADMIN", "STOCK")` that accepts `AsociarIngrediente({ingrediente_id: int, es_removible: bool = False})` and creates one row in `product_ingredients` with the given `es_removible` flag. The service SHALL validate the product exists (404 on miss) and the ingrediente exists as active (422 with `BusinessRuleError` on miss). If an active pivot row already exists for that pair → 409 (`ConflictError`). If a soft-deleted pivot row exists → reactivate it (`eliminado_en = NULL`) and update its `es_removible` to the new value. On success it SHALL return 201 with `IngredienteAsociadoRead`. (US-017, RN-CA07)

#### Scenario: Successful association
- **GIVEN** product 5 active and ingredient 10 active, no pivot row exists
- **WHEN** POST `/api/v1/productos/5/ingredientes` with `{"ingrediente_id": 10, "es_removible": true}`
- **THEN** the response is 201 with body containing `id: 10, es_removible: true` AND a new active row exists in `product_ingredients`

#### Scenario: Default es_removible is false
- **WHEN** POST with `{"ingrediente_id": 10}` (no `es_removible` key)
- **THEN** the response is 201 with `es_removible: false`

#### Scenario: Duplicate active association rejected
- **GIVEN** an active pivot row exists for (product 5, ingredient 10)
- **WHEN** POST `/api/v1/productos/5/ingredientes` with `{"ingrediente_id": 10}`
- **THEN** the response is 409 (`ConflictError`)

#### Scenario: Soft-deleted association is reactivated with new flag
- **GIVEN** a soft-deleted pivot row exists for (product 5, ingredient 10) with previous `es_removible: false`
- **WHEN** POST `/api/v1/productos/5/ingredientes` with `{"ingrediente_id": 10, "es_removible": true}`
- **THEN** the response is 201 AND the same pivot row now has `eliminado_en IS NULL` AND `es_removible: true` (no duplicate row inserted)

#### Scenario: Non-existent product returns 404
- **WHEN** POST `/api/v1/productos/99999/ingredientes` is called
- **THEN** the response is 404

#### Scenario: Non-existent ingrediente_id returns 422
- **GIVEN** ingredient id 99999 does not exist or is soft-deleted
- **WHEN** POST `/api/v1/productos/5/ingredientes` with `{"ingrediente_id": 99999}`
- **THEN** the response is 422 (`BusinessRuleError`)

#### Scenario: Unauthenticated rejected
- **WHEN** an anonymous client calls POST
- **THEN** the response is 401

#### Scenario: CLIENT role forbidden
- **WHEN** a user with role `CLIENT` calls POST
- **THEN** the response is 403

### Requirement: Remove ingrediente association endpoint
The system SHALL expose `DELETE /api/v1/productos/{id}/ingredientes/{ingrediente_id}` protected by `require_role("ADMIN", "STOCK")` that **soft-deletes** the pivot row (`eliminado_en = now()`). On success it SHALL return 204 with empty body. If the pivot row does not exist or is already soft-deleted → 404. The associated ingredient's row in `ingredients` SHALL NOT be modified. (US-017, RN-CA07)

#### Scenario: Successful disassociation
- **GIVEN** an active pivot row exists for (product 5, ingredient 10)
- **WHEN** DELETE `/api/v1/productos/5/ingredientes/10` is called
- **THEN** the response is 204 AND the pivot row has `eliminado_en IS NOT NULL` (NOT physically deleted)

#### Scenario: Already disassociated returns 404
- **GIVEN** a soft-deleted pivot row for (product 5, ingredient 10)
- **WHEN** DELETE is called again
- **THEN** the response is 404

#### Scenario: Non-existent association returns 404
- **WHEN** DELETE `/api/v1/productos/5/ingredientes/99999` is called and no pivot row ever existed
- **THEN** the response is 404

#### Scenario: Non-existent product returns 404
- **WHEN** DELETE `/api/v1/productos/99999/ingredientes/10` is called
- **THEN** the response is 404

#### Scenario: Ingredient row not modified
- **GIVEN** ingredient 10 exists active
- **WHEN** the disassociation endpoint succeeds
- **THEN** the row in `ingredients` for id=10 still has `eliminado_en IS NULL`

#### Scenario: CLIENT role forbidden
- **WHEN** a user with role `CLIENT` calls DELETE
- **THEN** the response is 403

### Requirement: API versioned prefix and naming
The system SHALL mount the products router under `/api/v1/productos` (Spanish path) with tag `products`. All endpoints SHALL use the Spanish path segment `productos` to align with `docs/Integrador.txt §5.2` and the rest of the catalog (`/categorias`, `/ingredientes`). The previous English mount path `/api/v1/products` (which existed as a stub) SHALL no longer respond. (Integrador.txt §5.2)

#### Scenario: Endpoints respond under /api/v1/productos
- **WHEN** a client calls `GET /api/v1/productos`
- **THEN** the response is 200

#### Scenario: Endpoints do not respond at /api/v1/products
- **WHEN** a client calls `GET /api/v1/products` (English)
- **THEN** the response is 404

#### Scenario: Endpoints do not respond at /api/productos
- **WHEN** a client calls `GET /api/productos` (no version)
- **THEN** the response is 404

### Requirement: Errors use RFC 7807 Problem Details
All error responses from product endpoints SHALL conform to RFC 7807 (`{type, title, status, detail, instance}`) via the existing exception handlers registered in `backend/main.py` (see `error-handling/spec.md`). Domain exceptions raised by the service (`NotFoundError`, `ConflictError`, `BusinessRuleError`, `ValidationError`, `ForbiddenError`, `UnauthorizedError`) SHALL be the only error path — no raw `HTTPException` from the router.

#### Scenario: NotFoundError yields RFC 7807 404
- **WHEN** a product endpoint raises `NotFoundError`
- **THEN** the response is 404 with body `{type, title: "Not Found", status: 404, detail, instance}`

#### Scenario: ConflictError yields RFC 7807 409
- **WHEN** the service raises `ConflictError` (duplicate ingredient association)
- **THEN** the response is 409 with `title: "Conflict"`

#### Scenario: BusinessRuleError yields RFC 7807 422
- **WHEN** the service raises `BusinessRuleError` (negative stock, missing categoria_id, missing ingrediente_id)
- **THEN** the response is 422 with `title` matching the business-rule handler

#### Scenario: ValidationError yields RFC 7807 422 with errors array
- **WHEN** Pydantic validation fails (empty nombre, precio <= 0, etc.)
- **THEN** the response is 422 with `errors` array listing the failing fields

### Requirement: Soft delete is the only delete mode
The system SHALL never expose a hard-delete endpoint for products or for pivot associations. Both `Producto.delete()` (via `BaseRepository.delete()`) and the bespoke `remove_ingrediente()` SHALL set `eliminado_en` to the current UTC timestamp. (RN-CA09)

#### Scenario: No DELETE endpoint performs hard delete on products
- **WHEN** the OpenAPI schema for `/api/v1/productos` is introspected
- **THEN** there is no endpoint that triggers `session.delete()` against `Producto`

#### Scenario: Soft-deleted row is invisible to default queries
- **GIVEN** product id 5 has `eliminado_en` set
- **WHEN** `repository.read(5)` is called
- **THEN** it returns `None` (filtered out by the soft-delete filter inherited from `BaseRepository`)

#### Scenario: Pivot soft delete leaves row in table
- **GIVEN** an active pivot row for (product 5, ingredient 10)
- **WHEN** the disassociation endpoint succeeds
- **THEN** the row count of `product_ingredients` (including soft-deleted) is unchanged
