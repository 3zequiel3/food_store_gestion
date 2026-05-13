## ADDED Requirements

### Requirement: Ingrediente entity model
The system SHALL persist ingredients in the existing `ingredients` table (created in migration `20260428_0001_initial_schema`, lines 285-308) with columns `id BIGSERIAL`, `nombre VARCHAR(255) NOT NULL UNIQUE` (constraint `uq_ingredients_nombre`), `es_alergeno BOOLEAN NOT NULL DEFAULT false`, plus the standard `creado_en/actualizado_en/eliminado_en TIMESTAMPTZ` columns from `BaseModel`. The ORM class `Ingrediente` defined in `backend/features/catalog/models.py` (lines 137-151) SHALL be the single source of truth — the new `ingredients` module MUST import it, not redefine it. (RN-CA07, RN-CA09)

#### Scenario: Ingrediente has UNIQUE constraint on nombre
- **WHEN** the `ingredients` table schema is introspected
- **THEN** there exists a UNIQUE constraint named `uq_ingredients_nombre` on column `nombre`

#### Scenario: Ingrediente has es_alergeno boolean column
- **WHEN** the `ingredients` table schema is introspected
- **THEN** column `es_alergeno` exists as `BOOLEAN NOT NULL DEFAULT false`

#### Scenario: Ingrediente ORM is reused, not redefined
- **WHEN** `backend.features.ingredients.repository` is imported
- **THEN** it imports `Ingrediente` from `backend.features.catalog.models` and does NOT declare a new SQLAlchemy class with `__tablename__ = "ingredients"`

#### Scenario: Ingrediente inherits soft-delete from BaseModel
- **WHEN** an `Ingrediente` instance is loaded from the database
- **THEN** it exposes attributes `id`, `nombre`, `es_alergeno`, `creado_en`, `actualizado_en`, `eliminado_en` and `eliminado_en` is `None` for active rows

### Requirement: Create ingredient endpoint
The system SHALL expose `POST /api/v1/ingredientes` protected by `require_role("ADMIN", "STOCK")` that accepts `IngredienteCreate({nombre: str, es_alergeno: bool = False})`. On success it SHALL return 201 with `IngredienteRead`. The `nombre` field SHALL be validated with `min_length=1, max_length=255`. (US-011)

#### Scenario: Successful ingredient creation as ADMIN
- **WHEN** a user with role `ADMIN` posts `{"nombre": "Tomate", "es_alergeno": false}`
- **THEN** the response is 201 with body `{"id": <int>, "nombre": "Tomate", "es_alergeno": false, "creado_en": <iso>, "actualizado_en": <iso>}` and a row exists in `ingredients`

#### Scenario: Successful ingredient creation as STOCK with es_alergeno true
- **WHEN** a user with role `STOCK` posts `{"nombre": "Mani", "es_alergeno": true}`
- **THEN** the response is 201 with `es_alergeno: true`

#### Scenario: es_alergeno defaults to false when omitted
- **WHEN** a user with role `ADMIN` posts `{"nombre": "Lechuga"}` (no `es_alergeno` key)
- **THEN** the response is 201 with `es_alergeno: false`

#### Scenario: Unauthenticated request rejected
- **WHEN** an anonymous client posts to `/api/v1/ingredientes`
- **THEN** the response is 401 (RFC 7807)

#### Scenario: CLIENT role forbidden
- **WHEN** a user with role `CLIENT` posts a valid create payload
- **THEN** the response is 403 (RFC 7807) with `title: "Forbidden"`

#### Scenario: Empty nombre rejected
- **WHEN** a payload with `nombre: ""` is posted
- **THEN** the response is 422 (RFC 7807) with `errors[]` listing the `nombre` field

#### Scenario: Nombre longer than 255 chars rejected
- **WHEN** a payload with `nombre` of 256 characters is posted
- **THEN** the response is 422 (RFC 7807)

### Requirement: Unique ingredient name
The system SHALL reject creating or updating an ingredient whose `nombre` matches an existing row in the `ingredients` table, regardless of whether the existing row is soft-deleted. This enforces the database-level UNIQUE constraint `uq_ingredients_nombre` and avoids `IntegrityError` from leaking as 500 responses. The check SHALL be performed in the service layer via `IngredientRepository.find_by_nombre(nombre)` which does NOT filter by `eliminado_en`. (US-011 acceptance)

#### Scenario: Duplicate name on active ingredient rejected
- **GIVEN** an active ingredient with `nombre="Tomate"` exists
- **WHEN** a payload `{"nombre": "Tomate"}` is posted
- **THEN** the response is 409 (RFC 7807) with `title: "Conflict"` and detail "Ya existe un ingrediente con ese nombre"

#### Scenario: Duplicate name on soft-deleted ingredient rejected
- **GIVEN** an ingredient with `nombre="Pimienta"` was soft-deleted (`eliminado_en` set)
- **WHEN** a payload `{"nombre": "Pimienta"}` is posted
- **THEN** the response is 409 (RFC 7807) with detail indicating the name is reserved

### Requirement: List ingredients endpoint with pagination and filter
The system SHALL expose `GET /api/v1/ingredientes` (public, no authentication required) that returns a paginated list of non-deleted ingredients wrapped in `PaginatedIngredientes({items: list[IngredienteRead], total: int, page: int, limit: int})`. The endpoint SHALL accept query params `page: int >= 1` (default 1), `limit: int in [1, 100]` (default 20), and `es_alergeno: bool | None` (default None = no filter). Soft-deleted ingredients (`eliminado_en IS NOT NULL`) SHALL be excluded. (US-012, RN-CA09)

#### Scenario: Default pagination returns first 20 items
- **GIVEN** 25 non-deleted ingredients exist
- **WHEN** `GET /api/v1/ingredientes` is called (no query params)
- **THEN** the response is 200 with `items.length == 20`, `total == 25`, `page == 1`, `limit == 20`

#### Scenario: Pagination respects page parameter
- **GIVEN** 25 non-deleted ingredients exist
- **WHEN** `GET /api/v1/ingredientes?page=2&limit=20` is called
- **THEN** the response is 200 with `items.length == 5`, `total == 25`, `page == 2`, `limit == 20`

#### Scenario: Filter es_alergeno=true returns only allergens
- **GIVEN** 3 ingredients with `es_alergeno=true` and 7 with `es_alergeno=false`
- **WHEN** `GET /api/v1/ingredientes?es_alergeno=true` is called
- **THEN** the response is 200 with `items.length == 3`, `total == 3`, every item has `es_alergeno: true`

#### Scenario: Filter es_alergeno=false returns only non-allergens
- **GIVEN** 3 ingredients with `es_alergeno=true` and 7 with `es_alergeno=false`
- **WHEN** `GET /api/v1/ingredientes?es_alergeno=false` is called
- **THEN** the response is 200 with `items.length == 7`, `total == 7`, every item has `es_alergeno: false`

#### Scenario: Empty catalog returns empty items
- **GIVEN** the `ingredients` table has no non-deleted rows
- **WHEN** `GET /api/v1/ingredientes` is called
- **THEN** the response is 200 with body `{"items": [], "total": 0, "page": 1, "limit": 20}`

#### Scenario: Soft-deleted ingredients excluded
- **GIVEN** 3 ingredients exist, 1 with `eliminado_en` set
- **WHEN** `GET /api/v1/ingredientes` is called
- **THEN** the response `total == 2` and the soft-deleted ingredient is NOT in `items`

#### Scenario: Endpoint is public
- **WHEN** an anonymous client calls `GET /api/v1/ingredientes`
- **THEN** the response is 200 (no auth required)

#### Scenario: limit above 100 rejected
- **WHEN** `GET /api/v1/ingredientes?limit=200` is called
- **THEN** the response is 422 (RFC 7807) with `errors[]` listing the `limit` field

#### Scenario: page below 1 rejected
- **WHEN** `GET /api/v1/ingredientes?page=0` is called
- **THEN** the response is 422 (RFC 7807)

### Requirement: Get ingredient by id endpoint
The system SHALL expose `GET /api/v1/ingredientes/{id}` (public, no authentication required) that returns a single non-deleted ingredient as `IngredienteRead`. Soft-deleted or non-existent ingredients SHALL return 404. This endpoint exists primarily to support `products-backend` (#11) when validating ingredient associations.

#### Scenario: Successful get by id
- **GIVEN** an active ingredient with `id=5, nombre="Sal"`
- **WHEN** `GET /api/v1/ingredientes/5` is called
- **THEN** the response is 200 with body `{"id": 5, "nombre": "Sal", "es_alergeno": false, ...}`

#### Scenario: Non-existent id returns 404
- **WHEN** `GET /api/v1/ingredientes/99999` is called
- **THEN** the response is 404 (RFC 7807)

#### Scenario: Soft-deleted ingredient returns 404
- **GIVEN** ingredient `id=5` has `eliminado_en` set
- **WHEN** `GET /api/v1/ingredientes/5` is called
- **THEN** the response is 404 (the repository excludes soft-deleted rows)

#### Scenario: Endpoint is public
- **WHEN** an anonymous client calls `GET /api/v1/ingredientes/5`
- **THEN** the response is 200 (no auth required)

### Requirement: Update ingredient endpoint
The system SHALL expose `PUT /api/v1/ingredientes/{id}` protected by `require_role("ADMIN", "STOCK")` that accepts `IngredienteUpdate({nombre: str | None, es_alergeno: bool | None})` (partial update). On success it SHALL return 200 with `IngredienteRead`. The service SHALL use `payload.model_dump(exclude_unset=True)` to distinguish "field not sent" from "field explicitly null/false" — this is critical for `es_alergeno` to avoid silent overwrites when the client only intends to update `nombre`. (US-013)

#### Scenario: Successful nombre-only update
- **GIVEN** ingredient `id=5, nombre="Tomate", es_alergeno=false`
- **WHEN** a user with role `ADMIN` PUTs `/api/v1/ingredientes/5` with `{"nombre": "Tomate Cherry"}`
- **THEN** the response is 200 with `nombre: "Tomate Cherry", es_alergeno: false` (es_alergeno preserved)

#### Scenario: Successful es_alergeno-only update
- **GIVEN** ingredient `id=5, nombre="Mani", es_alergeno=false`
- **WHEN** PUT `/api/v1/ingredientes/5` with `{"es_alergeno": true}` is called
- **THEN** the response is 200 with `nombre: "Mani", es_alergeno: true`

#### Scenario: Successful both-fields update
- **WHEN** PUT `/api/v1/ingredientes/5` with `{"nombre": "Mani Salado", "es_alergeno": true}`
- **THEN** the response is 200 with both fields updated

#### Scenario: Update to existing name rejected
- **GIVEN** ingredients `id=5, nombre="Tomate"` and `id=7, nombre="Lechuga"`
- **WHEN** PUT `/api/v1/ingredientes/7` with `{"nombre": "Tomate"}`
- **THEN** the response is 409 (RFC 7807) with `title: "Conflict"`

#### Scenario: Update preserves nombre when only es_alergeno sent
- **GIVEN** ingredient `id=5, nombre="Tomate"`
- **WHEN** PUT `/api/v1/ingredientes/5` with `{"es_alergeno": true}`
- **THEN** the row in `ingredients` still has `nombre = "Tomate"`

#### Scenario: Non-existent ingredient returns 404
- **WHEN** PUT `/api/v1/ingredientes/99999` with any payload
- **THEN** the response is 404 (RFC 7807)

#### Scenario: Soft-deleted ingredient cannot be updated
- **GIVEN** ingredient `id=5` has `eliminado_en` set
- **WHEN** PUT `/api/v1/ingredientes/5` with any payload
- **THEN** the response is 404 (the repository excludes soft-deleted rows from the base query)

#### Scenario: Empty nombre on update rejected
- **WHEN** PUT `/api/v1/ingredientes/5` with `{"nombre": ""}`
- **THEN** the response is 422 (RFC 7807)

#### Scenario: CLIENT role forbidden
- **WHEN** a user with role `CLIENT` PUTs any payload
- **THEN** the response is 403 (RFC 7807)

### Requirement: Soft delete ingredient endpoint
The system SHALL expose `DELETE /api/v1/ingredientes/{id}` protected by `require_role("ADMIN", "STOCK")` that performs a soft delete by setting `eliminado_en = now()`. The endpoint MUST NEVER perform a hard delete and MUST NOT block deletion when `product_ingredients` rows reference the ingredient — US-014 explicitly states the ingredient should "remain in existing products but stop appearing for new associations", which is achieved naturally by soft delete. On success it SHALL return 204 with empty body. (US-014, RN-CA09)

#### Scenario: Successful soft delete
- **GIVEN** ingredient `id=5` exists
- **WHEN** a user with role `ADMIN` calls `DELETE /api/v1/ingredientes/5`
- **THEN** the response is 204 AND the row in `ingredients` has `eliminado_en IS NOT NULL` (NOT physically removed)

#### Scenario: Hard delete never happens
- **WHEN** any DELETE request succeeds
- **THEN** the row count of `ingredients` (including soft-deleted) is unchanged

#### Scenario: Already-deleted ingredient returns 404
- **GIVEN** ingredient `id=5` was previously soft-deleted
- **WHEN** `DELETE /api/v1/ingredientes/5` is called again
- **THEN** the response is 404

#### Scenario: Non-existent ingredient returns 404
- **WHEN** `DELETE /api/v1/ingredientes/99999` is called
- **THEN** the response is 404

#### Scenario: Delete succeeds even with products associated
- **GIVEN** ingredient `id=5` has rows in `product_ingredients` linking it to active products
- **WHEN** `DELETE /api/v1/ingredientes/5` is called
- **THEN** the response is 204 (no guard — soft delete fulfills US-014 textual)

#### Scenario: Soft-deleted ingredient remains queryable via legacy associations
- **GIVEN** ingredient `id=5` was soft-deleted but `product_ingredients` rows still reference it
- **WHEN** the `product_ingredients` table is queried with `WHERE ingredient_id = 5`
- **THEN** the rows still exist (soft delete does not touch the pivot table)

#### Scenario: CLIENT role forbidden
- **WHEN** a user with role `CLIENT` calls DELETE
- **THEN** the response is 403 (RFC 7807)

### Requirement: Soft delete is the only delete mode
The system SHALL never expose a hard-delete endpoint for ingredients. The repository's `delete()` method (inherited from `BaseRepository`) SHALL set `eliminado_en` to the current UTC timestamp. (RN-CA09)

#### Scenario: No DELETE endpoint performs hard delete
- **WHEN** the OpenAPI schema for `/api/v1/ingredientes` is introspected
- **THEN** there is no endpoint that triggers `session.delete()` against `Ingrediente`

#### Scenario: Soft-deleted row is invisible to default queries
- **GIVEN** ingredient `id=5` has `eliminado_en` set
- **WHEN** `repository.read(5)` is called
- **THEN** it returns `None` (filtered out by the soft-delete filter inherited from `BaseRepository`)

### Requirement: API versioned prefix and Spanish naming
The system SHALL mount the ingredients router under `/api/v1/ingredientes` with tag `ingredients`. All endpoints SHALL use the Spanish path segment `ingredientes` (matching the project convention seen in `categories` and `docs/Integrador.txt §5`). (Integrador.txt §5)

#### Scenario: Endpoints respond under /api/v1/ingredientes
- **WHEN** a client calls `GET /api/v1/ingredientes`
- **THEN** the response is 200 (when fully wired)

#### Scenario: Endpoints do not respond at /ingredients or /api/ingredientes
- **WHEN** a client calls `GET /api/v1/ingredients` (English) or `GET /api/ingredientes` (no version)
- **THEN** the response is 404

### Requirement: Errors use RFC 7807 Problem Details
All error responses from ingredient endpoints SHALL conform to RFC 7807 (`{type, title, status, detail, instance}`) via the existing exception handlers registered in `backend/main.py` (see `error-handling/spec.md`). Domain exceptions raised by the service (`NotFoundError`, `ConflictError`, `BusinessRuleError`, `ValidationError`, `ForbiddenError`, `UnauthorizedError`) SHALL be the only error path — no raw `HTTPException` from the router.

#### Scenario: NotFoundError yields RFC 7807 404
- **WHEN** an ingredient endpoint raises `NotFoundError`
- **THEN** the response is 404 with body `{type, title: "Not Found", status: 404, detail, instance}`

#### Scenario: ConflictError yields RFC 7807 409
- **WHEN** the service raises `ConflictError` (duplicate name)
- **THEN** the response is 409 with `title: "Conflict"`

#### Scenario: BusinessRuleError yields RFC 7807 422
- **WHEN** the service raises `BusinessRuleError` (defensive blank-name check after strip)
- **THEN** the response is 422 with `title` matching the business-rule handler

### Requirement: Service does not commit; router decides transaction boundary
The `IngredientService` MUST NEVER call `uow.commit()` or `session.commit()`. The transaction boundary is owned exclusively by the router (each mutating endpoint calls `uow.commit()` after the service returns). The read-only `GET` endpoints SHALL NOT call `uow.commit()`. This pattern matches `categories-backend` D6 and the Integrador §7.1 semantics for UnitOfWork. (D6 in design.md)

#### Scenario: Service has no commit calls
- **WHEN** `backend/features/ingredients/service.py` is grepped for `commit`
- **THEN** no occurrence of `commit` exists in the service module

#### Scenario: Router commits after each mutation
- **WHEN** the `POST`, `PUT`, or `DELETE` handler completes successfully
- **THEN** `uow.commit()` is called before the response is returned

#### Scenario: Router does not commit on read
- **WHEN** the `GET /` or `GET /{id}` handler completes
- **THEN** `uow.commit()` is NOT called (read-only endpoint)
