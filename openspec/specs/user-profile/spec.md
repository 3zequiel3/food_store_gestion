## Purpose

Enable authenticated users to view and manage their own user profile (US-061, US-062, US-063). This capability supports self-service profile management with endpoints for profile retrieval, partial updates (nombre, apellido, telefono), and secure password changes with refresh-token revocation. Email remains immutable as the unique identifier. All endpoints enforce self-service isolation via `get_current_user` dependency.

## Requirements

### Requirement: Get own profile endpoint
The system SHALL expose `GET /api/v1/usuarios/me` protected by `Depends(get_current_user)` (any authenticated role) that returns the authenticated user's full profile as `ProfileResponse({id, email, nombre, apellido, telefono, roles[], creado_en, actualizado_en})`. The endpoint SHALL eager-load roles via `selectinload` and SHALL NEVER include `password_hash`, `is_active`, or `eliminado_en` in the response payload. (US-061, RN-RB05)

#### Scenario: Authenticated user retrieves own profile with telefono
- **GIVEN** a user with `telefono="+54 11 1234-5678"` is authenticated
- **WHEN** they call `GET /api/v1/usuarios/me`
- **THEN** the response is 200 with body `{id, email, nombre, apellido, telefono: "+54 11 1234-5678", roles, creado_en, actualizado_en}`

#### Scenario: Roles are serialized as code strings
- **GIVEN** an authenticated user with role CLIENT
- **WHEN** they call `GET /api/v1/usuarios/me`
- **THEN** `body.roles == ["CLIENT"]` (list of role code strings, not Rol objects)

#### Scenario: Sensitive fields never appear in response
- **GIVEN** any authenticated user
- **WHEN** they call `GET /api/v1/usuarios/me`
- **THEN** the response JSON SHALL NOT contain the keys `password_hash`, `is_active`, `eliminado_en`

#### Scenario: Unauthenticated request rejected
- **WHEN** an anonymous client calls `GET /api/v1/usuarios/me`
- **THEN** the response is 401 (RFC 7807) with `title: "Unauthorized"`

#### Scenario: Invalid token rejected
- **WHEN** a client sends `Authorization: Bearer foobar` to `GET /api/v1/usuarios/me`
- **THEN** the response is 401

### Requirement: Update own profile endpoint
The system SHALL expose `PATCH /api/v1/usuarios/me` protected by `Depends(get_current_user)` that accepts `UpdateProfileRequest({nombre?: str, apellido?: str, telefono?: str | null})` (all fields optional). On success it SHALL return 200 with `ProfileResponse`. The service SHALL apply `model_dump(exclude_unset=True)` so omitted fields are preserved and explicit `null` for `telefono` is honored. The endpoint SHALL reject any extra fields (`email`, `password`, `roles`) with 422 (`extra="forbid"`). (US-062)

#### Scenario: Successful partial update of nombre
- **GIVEN** a user with `nombre="Juan", apellido="Perez", telefono="+541112"`
- **WHEN** they PATCH `/api/v1/usuarios/me` with `{"nombre": "Juan Carlos"}`
- **THEN** the response is 200 with `nombre: "Juan Carlos"`, `apellido: "Perez"` and `telefono: "+541112"` unchanged

#### Scenario: Successful update of multiple fields
- **WHEN** the user PATCHes with `{"nombre": "Ana", "apellido": "Gomez", "telefono": "+1-555-0100"}`
- **THEN** the response is 200 with all three fields updated

#### Scenario: Setting telefono to null
- **GIVEN** a user with `telefono="+541112"`
- **WHEN** they PATCH with `{"telefono": null}`
- **THEN** the response is 200 with `telefono: null` AND the database column `users.telefono` is `NULL`

#### Scenario: Empty body is a no-op
- **WHEN** the user PATCHes with `{}`
- **THEN** the response is 200 and no fields change

#### Scenario: Email field rejected by extra="forbid"
- **WHEN** the user PATCHes with `{"nombre": "X", "email": "new@example.com"}`
- **THEN** the response is 422 (RFC 7807) listing `email` as an extra forbidden field

#### Scenario: Password field rejected by extra="forbid"
- **WHEN** the user PATCHes with `{"password": "newpass123"}`
- **THEN** the response is 422

#### Scenario: Roles field rejected by extra="forbid"
- **WHEN** the user PATCHes with `{"roles": ["ADMIN"]}`
- **THEN** the response is 422 (a CLIENT cannot self-promote)

#### Scenario: Unauthenticated request rejected
- **WHEN** an anonymous client PATCHes `/api/v1/usuarios/me`
- **THEN** the response is 401

### Requirement: Email is not editable through the profile endpoint
The system SHALL NEVER allow modification of the `users.email` column through `PATCH /api/v1/usuarios/me`. The `UpdateProfileRequest` schema SHALL NOT declare an `email` field, and `extra="forbid"` SHALL cause any attempt to send `email` to be rejected with 422. (US-062 acceptance: "El email NO se puede cambiar (es el identificador)" + Integrador.txt §3.1 — email is the unique identifier)

#### Scenario: Email change attempt is rejected
- **WHEN** a user PATCHes with `{"email": "different@example.com"}`
- **THEN** the response is 422 AND the database row's `email` is unchanged

### Requirement: Validation of nombre and apellido
The system SHALL validate `nombre` and `apellido` with Pydantic constraints `min_length=2, max_length=80` (matching `RegisterRequest`, derived from spec §6.1). Additionally, the service SHALL trim whitespace from non-null values and reject post-trim empty strings as `BusinessRuleError` 422.

#### Scenario: Nombre below minimum length
- **WHEN** a user PATCHes with `{"nombre": "A"}`
- **THEN** the response is 422 with the validation error referencing `nombre`

#### Scenario: Nombre above maximum length
- **WHEN** a user PATCHes with `{"nombre": "<81 characters>"}`
- **THEN** the response is 422

#### Scenario: Whitespace-only nombre is rejected after trim
- **WHEN** a user PATCHes with `{"nombre": "   "}`
- **THEN** the response is 422 (BusinessRuleError) with detail "El campo nombre no puede ser vacío"

### Requirement: Validation of telefono format
The system SHALL validate `telefono` with the regex `^\+?[\d\s\-\(\)]{6,30}$` (permissive: optional leading `+`, then 6-30 chars among digits, spaces, hyphens, and parentheses). Empty string `""` SHALL be rejected (does not match regex); explicit `null` SHALL be accepted to clear the field. (US-062 acceptance "Validación de formato de teléfono")

#### Scenario: Valid international formats accepted
- **WHEN** a user PATCHes with any of: `"+54 11 1234-5678"`, `"(011) 1234-5678"`, `"+1-555-0100"`, `"5491112345678"`
- **THEN** each response is 200

#### Scenario: Alphabetic telefono rejected
- **WHEN** a user PATCHes with `{"telefono": "abcdefghij"}`
- **THEN** the response is 422

#### Scenario: Empty string telefono rejected
- **WHEN** a user PATCHes with `{"telefono": ""}`
- **THEN** the response is 422 (regex requires {6,30} chars)

#### Scenario: Telefono too short rejected
- **WHEN** a user PATCHes with `{"telefono": "+1"}`
- **THEN** the response is 422

### Requirement: Change password endpoint
The system SHALL expose `POST /api/v1/usuarios/me/password` protected by `Depends(get_current_user)` that accepts `ChangePasswordRequest({password_actual: str, password_nuevo: str})`. On success it SHALL return **204 No Content** with empty body. The endpoint SHALL:
1. Verify `password_actual` against the stored hash via `verify_password` (bcrypt constant-time).
2. Reject if `password_nuevo` matches the current password (avoids needless token revocation).
3. Hash the new password with `hash_password` (bcrypt cost ≥ 12, RN-AU01).
4. Persist via `flush()` BEFORE revoking refresh tokens (atomicity within UoW).
5. Revoke ALL refresh tokens of the user via `RefreshTokenRepository.revoke_all_user_tokens` (US-063 textual + RN-AU05).
(US-063, RN-AU01, RN-AU05)

#### Scenario: Successful password change returns 204
- **GIVEN** a user with current password `correct_pass_1` and a valid token
- **WHEN** they POST `{"password_actual": "correct_pass_1", "password_nuevo": "new_pass_2024"}`
- **THEN** the response is 204 with empty body AND `users.password_hash` in DB has changed

#### Scenario: Login with new password works after change
- **GIVEN** the password was successfully changed to `new_pass_2024`
- **WHEN** the user POSTs `/api/v1/auth/login` with `{"email": <user>, "password": "new_pass_2024"}`
- **THEN** the response is 200 with a new token pair

#### Scenario: Login with old password fails after change
- **GIVEN** the password was successfully changed
- **WHEN** the user POSTs `/api/v1/auth/login` with the OLD password
- **THEN** the response is 401

### Requirement: Wrong password returns 401 with generic message
When `password_actual` does not match the stored hash, the system SHALL raise `UnauthorizedError` mapping to **HTTP 401** (NOT 422), with `detail: "Credenciales inválidas"`. The detail SHALL be deliberately generic and SHALL NOT mention "actual", "nuevo", "incorrecto", or any other word that leaks which credential failed. This aligns with RN-AU08 (login error responses do not differentiate "email not found" from "wrong password").

#### Scenario: Wrong current password yields 401 generic
- **WHEN** a user POSTs `{"password_actual": "WRONG", "password_nuevo": "valid_new_pass"}`
- **THEN** the response is 401 (RFC 7807) with `detail: "Credenciales inválidas"`

#### Scenario: Error detail does not leak credential semantics
- **WHEN** any 401 from this endpoint is returned
- **THEN** the response body's `detail` field SHALL NOT contain the substrings `"actual"`, `"nuevo"`, `"incorrecto"`, `"hash"`, `"password"` (case-insensitive)

### Requirement: New password must differ from current
When `password_nuevo` (after `verify_password` against the stored hash) matches the current password, the system SHALL raise `BusinessRuleError` mapping to HTTP 422 with `detail: "La nueva contraseña debe ser diferente de la actual"`. This avoids unnecessary refresh-token revocation when the user submits the same password twice.

#### Scenario: Same password rejected with 422
- **WHEN** a user POSTs `{"password_actual": "X", "password_nuevo": "X"}` where `X` is their current password
- **THEN** the response is 422 (BusinessRuleError) with `detail` containing "diferente de la actual"

#### Scenario: Refresh tokens are NOT revoked on this rejection
- **GIVEN** the user has 2 active refresh tokens
- **WHEN** the request above returns 422
- **THEN** both refresh tokens still have `revoked_at IS NULL`

### Requirement: New password minimum length
The system SHALL enforce `password_nuevo` `min_length=8` and `max_length=128` via Pydantic validation. The `min_length=8` matches `RegisterRequest` (RN-AU01 implies bcrypt; spec does not mandate a complexity regex). The `max_length=128` defends against payload abuse since bcrypt only consumes the first 72 bytes anyway.

#### Scenario: Too-short new password rejected
- **WHEN** a user POSTs `{"password_actual": "valid_current", "password_nuevo": "1234567"}` (7 chars)
- **THEN** the response is 422 (Pydantic RequestValidationError)

#### Scenario: Excessively long new password rejected
- **WHEN** a user POSTs with `password_nuevo` of 129 characters
- **THEN** the response is 422

### Requirement: All refresh tokens revoked on successful password change
On a successful password change (204), the system SHALL invoke `RefreshTokenRepository.revoke_all_user_tokens(user_id)` which sets `revoked_at = now()` on EVERY refresh token of the user where `revoked_at IS NULL`. This implements RN-AU05 (token replay protection extended to password changes) and US-063 acceptance "Se invalidan todos los refresh tokens existentes". The revocation SHALL be atomic with the password update — if any step fails, the UoW rollback SHALL leave both the password and the tokens unchanged.

#### Scenario: All active refresh tokens are revoked after success
- **GIVEN** a user has 2 active refresh tokens (`revoked_at IS NULL`)
- **WHEN** the user successfully changes their password (204 response)
- **THEN** a query `SELECT revoked_at FROM refresh_tokens WHERE user_id = <id>` returns 2 rows where every `revoked_at IS NOT NULL`

#### Scenario: Refresh with old token fails after password change
- **GIVEN** a user logged in and received `refresh_token=R`
- **WHEN** they successfully change their password, then POST `/api/v1/auth/refresh` with `R`
- **THEN** the response is 401

#### Scenario: Failed password change does not revoke tokens
- **GIVEN** a user has 2 active refresh tokens
- **WHEN** they POST `/me/password` with an incorrect `password_actual` (yielding 401)
- **THEN** both refresh tokens still have `revoked_at IS NULL` (atomicity preserved)

### Requirement: Access tokens remain valid until natural expiration after password change
The system SHALL NOT attempt to invalidate access tokens on password change. JWT access tokens are stateless (RN-AU02, 30-minute expiration) and there is no token blacklist. The frontend SHALL be responsible for clearing local credentials on receipt of the 204 response. The spec does NOT require an immediate force-logout mechanism; this is documented behavior for the v1 implementation.

#### Scenario: Access token issued before password change continues to work briefly
- **GIVEN** a user has access token `T` (valid for 25 more minutes)
- **WHEN** they successfully change their password and continue to use `T` against `GET /api/v1/usuarios/me`
- **THEN** the response is 200 (not invalidated immediately — stateless JWT)

#### Scenario: After access token expires, refresh fails (forces re-login)
- **GIVEN** the user kept using `T` after password change
- **WHEN** `T` eventually expires AND they try to refresh with the old refresh token
- **THEN** the refresh returns 401 (refresh tokens were revoked) — forcing re-login

### Requirement: Self-service only (no cross-user access)
The system SHALL ensure that all profile endpoints operate exclusively on the authenticated user's own data, derived from `current_user.id` returned by `Depends(get_current_user)`. No endpoint SHALL accept a `user_id` path parameter or body field. This implements RN-RB05 (a CLIENT can only see and operate on their own data). Cross-user access for ADMINs is out of scope and belongs to `admin-users-backend` (#18).

#### Scenario: No path parameter for user_id is exposed
- **WHEN** the OpenAPI schema for `/api/v1/usuarios/*` is introspected
- **THEN** there is no route `/api/v1/usuarios/{user_id}` for the profile endpoints (GET/PATCH/POST `/me/*`)

#### Scenario: Endpoint always derives the target user from the token
- **GIVEN** authenticated user A and authenticated user B
- **WHEN** A calls `GET /api/v1/usuarios/me`
- **THEN** the response contains A's data, never B's (no body or query param can change this)

### Requirement: Errors use RFC 7807 Problem Details
All error responses from user-profile endpoints SHALL conform to RFC 7807 (`{type, title, status, detail, instance}`) via the existing exception handlers registered in `backend/main.py:108-119`. Domain exceptions raised by the service (`NotFoundError`, `UnauthorizedError`, `BusinessRuleError`) and Pydantic `RequestValidationError` SHALL be the only error paths. Routers SHALL NOT raise `HTTPException` directly.

#### Scenario: NotFoundError yields RFC 7807 404
- **WHEN** any user-profile endpoint raises `NotFoundError` (defensive — should not occur if `get_current_user` is correct)
- **THEN** the response is 404 with `title: "Not Found"`

#### Scenario: UnauthorizedError yields RFC 7807 401
- **WHEN** the change-password service raises `UnauthorizedError("Credenciales inválidas")`
- **THEN** the response is 401 with `title: "Unauthorized"` and `detail: "Credenciales inválidas"`

#### Scenario: BusinessRuleError yields RFC 7807 422
- **WHEN** the service raises `BusinessRuleError` (same password / empty trimmed name)
- **THEN** the response is 422 with `title` matching the business-rule handler

#### Scenario: No router raises HTTPException directly
- **WHEN** the implementation of `backend/features/users/router.py` is grepped
- **THEN** there are zero occurrences of `raise HTTPException`

### Requirement: API path and version
The system SHALL mount the user-profile endpoints under `/api/v1/usuarios` with tag `users`. Endpoints SHALL be `GET /me`, `PATCH /me`, `POST /me/password` — using the Spanish path segment `usuarios` to match the lexical convention of `Integrador.txt` (which names the conceptual module `usuarios` at line 91 and consistently uses Spanish path segments for domain resources: `productos`, `pedidos`, `pagos`, `direcciones`, `categorias`, `ingredientes`). The OpenAPI tag remains `users` (English) for consistency with the other six domain tags in `backend/main.py` (`products`, `orders`, `payments`, `addresses`, `categories`, `ingredients`), which use English tag names regardless of their Spanish URL prefix.

#### Scenario: Endpoints respond under /api/v1/usuarios
- **WHEN** a client calls `GET /api/v1/usuarios/me`
- **THEN** the response is 200 (when authenticated)

#### Scenario: Legacy English path returns 404
- **WHEN** a client calls `GET /api/v1/users/me`
- **THEN** the response is 404 (no such route — the legacy English path was removed in favor of the Spanish path that matches the Integrador lexicon)
