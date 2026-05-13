## ADDED Requirements

### Requirement: Filter ingredients by allergen flag
The system SHALL accept the optional query param `es_alergeno: bool | None = None` on `GET /api/v1/ingredientes`. When `es_alergeno` is `true`, the endpoint SHALL return only ingredients whose `es_alergeno = true`. When `es_alergeno` is `false`, the endpoint SHALL return only ingredients whose `es_alergeno = false`. When `es_alergeno` is omitted or null, the filter SHALL be a no-op (no filter on the column). Soft-deleted ingredients SHALL still be excluded by default (controlled by `incluir_eliminados`, RN-CA10). This filter formalizes the existing implementation and is the contract consumed by the admin frontend (Sprint 7) to populate the allergen multi-select used in conjunction with `excluir_alergeno_ids` on `GET /productos`.

#### Scenario: es_alergeno=true returns only allergens
- **GIVEN** 4 active ingredients: 2 with `es_alergeno=true`, 2 with `es_alergeno=false`
- **WHEN** `GET /api/v1/ingredientes?es_alergeno=true` is called
- **THEN** the response is 200 with `items.length == 2` and every item has `es_alergeno: true`

#### Scenario: es_alergeno=false returns only non-allergens
- **GIVEN** the same 4 ingredients as above
- **WHEN** `GET /api/v1/ingredientes?es_alergeno=false` is called
- **THEN** the response is 200 with `items.length == 2` and every item has `es_alergeno: false`

#### Scenario: es_alergeno omitted returns all active ingredients
- **GIVEN** the same 4 ingredients as above
- **WHEN** `GET /api/v1/ingredientes` is called (no params)
- **THEN** the response is 200 with `items.length == 4`

#### Scenario: Filter combined with pagination
- **GIVEN** 30 active ingredients with `es_alergeno=true`
- **WHEN** `GET /api/v1/ingredientes?es_alergeno=true&page=2&limit=10` is called
- **THEN** the response has `items.length == 10`, `total == 30`, `page == 2`, `limit == 10`

#### Scenario: Filter is public
- **WHEN** an anonymous client calls `GET /api/v1/ingredientes?es_alergeno=true`
- **THEN** the response is 200 (no auth required)

#### Scenario: Soft-deleted allergens excluded by default
- **GIVEN** ingredient `id=10` has `es_alergeno=true` and `eliminado_en IS NOT NULL`
- **WHEN** `GET /api/v1/ingredientes?es_alergeno=true` is called by anyone except ADMIN with `incluir_eliminados=true`
- **THEN** the response does NOT include ingredient 10
