## MODIFIED Requirements

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

### Requirement: API path and version
The system SHALL mount the user-profile endpoints under `/api/v1/usuarios` with tag `users`. Endpoints SHALL be `GET /me`, `PATCH /me`, `POST /me/password` — using the Spanish path segment `usuarios` to match the lexical convention of `Integrador.txt` (which names the conceptual module `usuarios` at line 91 and consistently uses Spanish path segments for domain resources: `productos`, `pedidos`, `pagos`, `direcciones`, `categorias`, `ingredientes`). The OpenAPI tag remains `users` (English) for consistency with the other six domain tags in `backend/main.py` (`products`, `orders`, `payments`, `addresses`, `categories`, `ingredients`), which use English tag names regardless of their Spanish URL prefix.

#### Scenario: Endpoints respond under /api/v1/usuarios
- **WHEN** a client calls `GET /api/v1/usuarios/me`
- **THEN** the response is 200 (when authenticated)

#### Scenario: Legacy English path returns 404
- **WHEN** a client calls `GET /api/v1/users/me`
- **THEN** the response is 404 (no such route — the legacy English path was removed in favor of the Spanish path that matches the Integrador lexicon)
