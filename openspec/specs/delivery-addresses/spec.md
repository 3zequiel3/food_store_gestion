## Purpose

Support self-service delivery address management for authenticated users. Users can create, list, update, delete, and designate principal addresses. Each address is owned by the user (404 anti-leak on cross-user access). The first address created is auto-marked principal; subsequent addresses require explicit PATCH to promote. Deleting the principal address leaves the user without a principal (no auto-promotion).

## Requirements

### Requirement: Create address endpoint
The system SHALL expose `POST /api/v1/direcciones` protected by `Depends(get_current_user)` (any authenticated role) that accepts `DireccionCreate({calle, numero, piso_depto?, ciudad, codigo_postal, referencia?})` and returns 201 with `DireccionRead`. The endpoint SHALL associate the new address with the authenticated user via `current_user.id` (NEVER from body) and SHALL auto-mark it as `es_principal=True` if and only if the user has zero active addresses at the moment of creation. The schema SHALL reject extra fields including `es_principal` and `usuario_id` with 422 (`extra="forbid"`). (US-024, RN-DI01, RN-RB05)

#### Scenario: First address auto-marked as principal
- **GIVEN** an authenticated user with zero active addresses
- **WHEN** they POST `/api/v1/direcciones` with `{"calle": "Av Siempre Viva", "numero": "742", "ciudad": "Springfield", "codigo_postal": "1000"}`
- **THEN** the response is 201 with body containing `es_principal: true` AND `usuario_id` equal to the authenticated user's id

#### Scenario: Second address NOT auto-marked
- **GIVEN** an authenticated user with one existing principal address
- **WHEN** they POST a second address with valid required fields
- **THEN** the response is 201 with `es_principal: false` AND the previously principal address keeps `es_principal: true`

#### Scenario: Optional fields piso_depto and referencia accepted
- **WHEN** the user POSTs `{"calle":"X", "numero":"1", "piso_depto":"3 B", "ciudad":"Y", "codigo_postal":"Z", "referencia":"frente al parque"}`
- **THEN** the response is 201 with `piso_depto: "3 B"` AND `referencia: "frente al parque"`

#### Scenario: Optional fields omitted are null in response
- **WHEN** the user POSTs without `piso_depto` or `referencia`
- **THEN** the response is 201 with `piso_depto: null` AND `referencia: null`

#### Scenario: Body with es_principal rejected by extra="forbid"
- **WHEN** the user POSTs `{"calle":"X", "numero":"1", "ciudad":"Y", "codigo_postal":"Z", "es_principal": true}`
- **THEN** the response is 422 (RFC 7807) listing `es_principal` as an extra forbidden field AND no row is inserted

#### Scenario: Body with usuario_id rejected by extra="forbid"
- **WHEN** the user POSTs with an extra `usuario_id` field
- **THEN** the response is 422 AND no row is inserted

#### Scenario: Whitespace-only required field rejected after trim
- **WHEN** the user POSTs `{"calle":"   ", "numero":"1", "ciudad":"Y", "codigo_postal":"Z"}`
- **THEN** the response is 422 (BusinessRuleError) with detail "El campo calle no puede ser vacío"

#### Scenario: Required field exceeds max_length
- **WHEN** the user POSTs with `calle` of 256 characters
- **THEN** the response is 422 (Pydantic max_length=255)

#### Scenario: Unauthenticated request rejected
- **WHEN** an anonymous client POSTs to `/api/v1/direcciones`
- **THEN** the response is 401 (RFC 7807) with `title: "Unauthorized"`

### Requirement: List own addresses endpoint
The system SHALL expose `GET /api/v1/direcciones` protected by `Depends(get_current_user)` that returns 200 with a JSON array of `DireccionRead` objects containing exclusively the authenticated user's active (non-soft-deleted) addresses, ordered with the principal address first then by `id` ascending. The endpoint SHALL NOT accept any path or query parameter for filtering by user — the target user is always derived from `current_user.id`. (US-025, RN-DI03)

#### Scenario: User receives only own addresses
- **GIVEN** user A has 2 active addresses and user B has 3 active addresses
- **WHEN** user A calls `GET /api/v1/direcciones`
- **THEN** the response is 200 with exactly 2 elements AND none of B's addresses appear in the array

#### Scenario: Principal address listed first
- **GIVEN** the user has addrA (`es_principal=false`, lower id) and addrB (`es_principal=true`, higher id)
- **WHEN** the user calls `GET /api/v1/direcciones`
- **THEN** `body[0].id == addrB.id` AND `body[1].id == addrA.id`

#### Scenario: Soft-deleted addresses excluded
- **GIVEN** the user has addrA active and addrB soft-deleted (`eliminado_en IS NOT NULL`)
- **WHEN** the user calls `GET /api/v1/direcciones`
- **THEN** the response contains only addrA

#### Scenario: Empty list when user has no addresses
- **WHEN** an authenticated user with zero addresses calls `GET /api/v1/direcciones`
- **THEN** the response is 200 with body `[]`

#### Scenario: Unauthenticated request rejected
- **WHEN** an anonymous client calls `GET /api/v1/direcciones`
- **THEN** the response is 401

### Requirement: Update address endpoint with PATCH semantics
The system SHALL expose `PUT /api/v1/direcciones/{address_id}` protected by `Depends(get_current_user)` that accepts `DireccionUpdate` (all fields optional) and returns 200 with `DireccionRead`. Despite the verb, the endpoint SHALL apply PATCH semantics via `model_dump(exclude_unset=True)` — omitted fields are preserved and explicit `null` for optional fields (`piso_depto`, `referencia`) is honored as a clear. The schema SHALL reject extra fields including `es_principal` and `usuario_id` with 422 (`extra="forbid"`). (US-026, RN-DI03)

#### Scenario: Partial update preserves omitted fields
- **GIVEN** an address with `calle="Original", numero="1", ciudad="X", codigo_postal="Y"`
- **WHEN** the user PUTs `{"calle": "Nueva Calle"}`
- **THEN** the response is 200 with `calle: "Nueva Calle"` AND `numero: "1"` AND `ciudad: "X"` AND `codigo_postal: "Y"` unchanged

#### Scenario: Setting optional field to null clears it
- **GIVEN** an address with `referencia="some note"`
- **WHEN** the user PUTs `{"referencia": null}`
- **THEN** the response is 200 with `referencia: null` AND the database column `referencia` IS NULL

#### Scenario: Empty body is a no-op
- **WHEN** the user PUTs `{}` for an existing own address
- **THEN** the response is 200 with the address unchanged

#### Scenario: Whitespace-only required field rejected
- **WHEN** the user PUTs `{"calle": "   "}`
- **THEN** the response is 422 (BusinessRuleError) with detail "El campo calle no puede ser vacío"

#### Scenario: Body with es_principal rejected
- **WHEN** the user PUTs `{"es_principal": true}` for an own address
- **THEN** the response is 422 (`extra="forbid"`) — the only legitimate way to change `es_principal` is `PATCH /{id}/predeterminada`

#### Scenario: Body with unknown field rejected
- **WHEN** the user PUTs `{"foo": "bar"}`
- **THEN** the response is 422

### Requirement: Delete address endpoint with soft delete
The system SHALL expose `DELETE /api/v1/direcciones/{address_id}` protected by `Depends(get_current_user)` that returns 204 on success with empty body. Deletion SHALL be soft (sets `eliminado_en = now()`, preserves the row to maintain referential integrity for `orders.direccion_entrega_id`). Deleting the principal address SHALL be allowed and SHALL leave the user with no principal — the system SHALL NOT auto-promote any other address. (US-027, RN-CA09)

#### Scenario: Successful soft delete
- **GIVEN** the user owns an active address
- **WHEN** they DELETE `/api/v1/direcciones/{id}`
- **THEN** the response is 204 with empty body AND the row exists in the database with `eliminado_en IS NOT NULL`

#### Scenario: Soft-deleted address excluded from listing
- **GIVEN** the user has 2 active addresses and DELETEs one
- **WHEN** they call `GET /api/v1/direcciones`
- **THEN** the response contains only 1 address — the deleted one is hidden

#### Scenario: Deleting the principal leaves user without principal
- **GIVEN** the user has addrA (`es_principal=true`) and addrB (`es_principal=false`)
- **WHEN** they DELETE addrA
- **THEN** the response is 204 AND addrB still has `es_principal=false` (no auto-promotion)

#### Scenario: Next create after deleting only address re-auto-marks
- **GIVEN** the user had only one address and DELETEd it (count of active addresses becomes 0)
- **WHEN** they POST a new address
- **THEN** the response is 201 with `es_principal: true` (RN-DI01 re-applies)

### Requirement: Set principal address endpoint with atomic swap
The system SHALL expose `PATCH /api/v1/direcciones/{address_id}/predeterminada` protected by `Depends(get_current_user)` that returns 200 with the updated `DireccionRead`. The endpoint SHALL atomically:
1. Set `es_principal=false` for ALL active addresses of the authenticated user (bulk UPDATE).
2. Set `es_principal=true` on the target address.
Both updates SHALL be staged in the same `UnitOfWork` session and committed by a single `uow.commit()` in the router. If the commit fails, the UoW SHALL roll back both updates atomically. The endpoint SHALL be idempotent — calling it on an address that is already principal SHALL return 200 without error. (US-028, RN-DI02)

#### Scenario: Swap unsets previous principal
- **GIVEN** the user has addrA (`es_principal=true`) and addrB (`es_principal=false`)
- **WHEN** they PATCH `/api/v1/direcciones/{addrB.id}/predeterminada`
- **THEN** the response is 200 with `es_principal: true` for addrB AND a database query confirms addrA now has `es_principal=false`

#### Scenario: Idempotent on already-principal address
- **GIVEN** the user has addrA (`es_principal=true`)
- **WHEN** they PATCH `/api/v1/direcciones/{addrA.id}/predeterminada`
- **THEN** the response is 200 with `es_principal: true` AND no error AND addrA still principal

#### Scenario: Promotes when no current principal exists
- **GIVEN** the user has addrA and addrB both with `es_principal=false` (post-deletion of a previous principal)
- **WHEN** they PATCH `/api/v1/direcciones/{addrA.id}/predeterminada`
- **THEN** the response is 200 with addrA principal AND addrB still non-principal

### Requirement: Ownership enforcement returns 404 not 403 (anti-leak)
The system SHALL enforce ownership of addresses via the repository method `find_by_id_and_user(address_id, user_id)` which returns `None` both when the address does not exist AND when it exists but belongs to a different user. The service SHALL raise `NotFoundError` → HTTP 404 with detail `"Dirección no encontrada"` in BOTH cases — the response SHALL NOT differentiate "does not exist" from "belongs to another user". The detail SHALL NOT contain the substrings `"ajena"`, `"propietario"`, `"forbidden"`, `"permission"`, `"owner"` (case-insensitive). (RN-DI03, anti-information-leak design)

#### Scenario: Updating another user's address yields 404
- **GIVEN** user A is authenticated and user B owns address `{id: 42}`
- **WHEN** user A calls `PUT /api/v1/direcciones/42` with a valid body
- **THEN** the response is 404 with detail `"Dirección no encontrada"` AND user B's address is unchanged in the database

#### Scenario: Deleting another user's address yields 404
- **GIVEN** user A is authenticated and user B owns address `{id: 42}`
- **WHEN** user A calls `DELETE /api/v1/direcciones/42`
- **THEN** the response is 404 AND user B's address still has `eliminado_en IS NULL`

#### Scenario: Setting another user's address as principal yields 404
- **WHEN** user A calls `PATCH /api/v1/direcciones/{B's_id}/predeterminada`
- **THEN** the response is 404 AND user B's `es_principal` flag is unchanged

#### Scenario: 404 detail identical for nonexistent and foreign id
- **WHEN** the same authenticated user calls `PUT /api/v1/direcciones/999999` (nonexistent) AND `PUT /api/v1/direcciones/{foreign_id}`
- **THEN** both responses are 404 with the SAME detail `"Dirección no encontrada"` (no semantic leak)

#### Scenario: Detail does not leak ownership vocabulary
- **WHEN** any 404 response from the addresses endpoints is returned
- **THEN** the response body's `detail` field SHALL NOT contain the substrings `"ajena"`, `"propietario"`, `"forbidden"`, `"permission"`, `"owner"` (case-insensitive)

### Requirement: Self-service only (no cross-user access via path or body)
The system SHALL ensure that all delivery-address endpoints operate exclusively on the authenticated user's own addresses, derived from `current_user.id` returned by `Depends(get_current_user)`. No endpoint SHALL accept a `user_id` or `usuario_id` path parameter, query parameter, or body field. This implements RN-RB05 and RN-DI03. Cross-user access for ADMINs is out of scope and belongs to a future `admin-users-backend` change. (RN-DI03, RN-RB05)

#### Scenario: No user_id path parameter exists
- **WHEN** the OpenAPI schema for `/api/v1/direcciones/*` is introspected
- **THEN** there is no route segment `/api/v1/direcciones/{user_id}/...` and no route accepting a `user_id` query parameter

#### Scenario: usuario_id in body is rejected on create
- **WHEN** an authenticated user POSTs with `{"calle":"X", ..., "usuario_id": 99}`
- **THEN** the response is 422 (`extra="forbid"`) — the user cannot create an address for another user

### Requirement: Schema field naming consistency
The system SHALL use the field name `usuario_id` (Spanish, matches `Integrador.txt §3.1` lexicon) in `DireccionRead` responses, even though the underlying database column is `user_id` (Anglicism inherited from initial migration). The mapping SHALL be done at the schema layer via Pydantic `validation_alias`. The schemas `DireccionCreate` and `DireccionUpdate` SHALL NOT declare either `user_id` or `usuario_id` (the value is derived from JWT). (Spec naming consistency with `Integrador.txt §3.1`)

#### Scenario: Read response exposes usuario_id
- **WHEN** the user GETs `/api/v1/direcciones`
- **THEN** each item in the array contains a key `usuario_id` (NOT `user_id`)

#### Scenario: Create body cannot contain user_id or usuario_id
- **WHEN** the user POSTs with `{"calle":"X", ..., "user_id": 1}` or `{..., "usuario_id": 1}`
- **THEN** the response is 422 (`extra="forbid"`) in both cases

### Requirement: Errors use RFC 7807 Problem Details
All error responses from delivery-address endpoints SHALL conform to RFC 7807 (`{type, title, status, detail, instance}`) via the existing exception handlers registered in `backend/main.py:108-119`. Domain exceptions raised by the service (`NotFoundError`, `BusinessRuleError`) and Pydantic `RequestValidationError` SHALL be the only error paths. Routers SHALL NOT raise `HTTPException` directly. (Reuses `error-handling` capability)

#### Scenario: NotFoundError yields RFC 7807 404
- **WHEN** an endpoint raises `NotFoundError` (address not found or foreign)
- **THEN** the response is 404 with `title: "Not Found"` AND `detail: "Dirección no encontrada"`

#### Scenario: BusinessRuleError yields RFC 7807 422
- **WHEN** the service raises `BusinessRuleError` (e.g., whitespace-only required field)
- **THEN** the response is 422 with the corresponding business-rule title and detail

#### Scenario: Pydantic RequestValidationError yields RFC 7807 422
- **WHEN** a request body fails Pydantic validation (missing field, max_length, extra="forbid")
- **THEN** the response is 422 (RFC 7807) with structured detail listing the offending fields

#### Scenario: No router raises HTTPException directly
- **WHEN** the implementation of `backend/features/addresses/router.py` is grepped
- **THEN** there are zero occurrences of `raise HTTPException`

### Requirement: API path and version
The system SHALL mount the delivery-address endpoints under `/api/v1/direcciones` with tag `addresses`. The endpoints SHALL be top-level (NOT a sub-path of `/api/v1/usuarios/me`) — this matches `docs/Historias_de_usuario.txt:982` (`POST /api/direcciones`) adapted to the project's `/api/v1/` versioning scheme. The Spanish path segment `direcciones` matches the lexicon used in `Integrador.txt §3.1`. (D1, US-024 through US-028 technical notes)

#### Scenario: Endpoints respond under /api/v1/direcciones
- **WHEN** an authenticated client calls `GET /api/v1/direcciones`
- **THEN** the response is 200 (when the user has access)

#### Scenario: English-Spanish ambiguity rejected
- **WHEN** a client calls `GET /api/v1/addresses` or `GET /api/v1/usuarios/me/direcciones`
- **THEN** the response is 404 (no such route)

### Requirement: Schema column piso_depto added via Alembic migration
The system SHALL include a new optional column `piso_depto VARCHAR(50) NULL` on the `delivery_addresses` table, added via a new Alembic migration with `revision = "piso_depto_delivery_addresses"` and `down_revision = "es_removible_product_ingredients"`. The migration SHALL be reversible (the `downgrade` SHALL drop the column). The model `DireccionEntrega` SHALL declare the matching field as `Mapped[Optional[str]] = mapped_column(String(50), nullable=True)`. (D9, US-024 textual mention of "piso/depto (opcional)")

#### Scenario: piso_depto persists on create
- **WHEN** an authenticated user POSTs `{"calle":"X", "numero":"1", "piso_depto":"3 B", "ciudad":"Y", "codigo_postal":"Z"}`
- **THEN** the response is 201 with `piso_depto: "3 B"` AND a direct DB query returns the row with `piso_depto = '3 B'`

#### Scenario: piso_depto can be cleared via PUT with null
- **GIVEN** an address with `piso_depto = "3 B"`
- **WHEN** the user PUTs `{"piso_depto": null}`
- **THEN** the response is 200 with `piso_depto: null` AND the database column `piso_depto` IS NULL

#### Scenario: piso_depto is optional on create
- **WHEN** the user POSTs without `piso_depto`
- **THEN** the response is 201 with `piso_depto: null` AND the row's column is NULL
