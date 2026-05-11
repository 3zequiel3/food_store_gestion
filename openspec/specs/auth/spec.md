## ADDED Requirements

### Requirement: Auth service owns the transaction boundary
The `AuthService` SHALL own the lifecycle of the database transaction for every public operation. Each public method (`register`, `login`, `refresh`, `logout`) SHALL open a `UnitOfWork` context, perform all DB operations within it, and rely on the context manager's `__exit__` to commit on success or rollback on exception. The HTTP adapter (router) SHALL NOT receive any `Session` or `UnitOfWork` via dependency injection, and SHALL NOT call `commit()` or `rollback()` explicitly.

#### Scenario: Service method opens its own UnitOfWork
- **WHEN** any public method of `AuthService` is invoked
- **THEN** the method opens `with UnitOfWork() as uow:` internally
- **AND** the router that calls the method does NOT have `db` nor `uow` in its signature
- **AND** the router does NOT call `commit()` or `rollback()`

#### Scenario: Router has no Depends(get_db) in auth endpoints
- **WHEN** the source of `backend/features/auth/router.py` is inspected
- **THEN** none of the 5 endpoints (`register`, `login`, `refresh`, `logout`, `get_me`) declares a `db=Depends(get_db)` parameter
- **AND** `from backend.shared.database import get_db` is NOT imported in the router

#### Scenario: Service has no Session in __init__
- **WHEN** the signature of `AuthService.__init__` is inspected
- **THEN** it accepts no parameters other than `self`
- **AND** `AuthService` has no instance attribute `session` nor `refresh_token_repo` set at construction time

### Requirement: Registration is atomic
The system SHALL persist the new `Usuario` row, the `UsuarioRol` association row, and the initial `RefreshToken` row in a single database transaction. If any of the three inserts fails, NONE of them SHALL be persisted. The `AuthService.register` method SHALL return a `TokenPairResponse` directly (not a `Usuario`), reflecting that the registration unit of work includes the initial token pair creation.

#### Scenario: register returns TokenPairResponse
- **WHEN** `AuthService().register(data)` is called with valid input
- **THEN** the return value is a `TokenPairResponse` with `access_token`, `refresh_token`, `token_type="bearer"`, `expires_in`
- **AND** the return value is NOT a `Usuario` instance

#### Scenario: All three rows are persisted on success
- **GIVEN** a registration request with a unique email
- **WHEN** the endpoint `POST /api/v1/auth/register` completes successfully
- **THEN** the `users` table has a new row for that email
- **AND** the `user_roles` table has a row `(user_id=<new_user_id>, role_id=4)`
- **AND** the `refresh_tokens` table has a row `(user_id=<new_user_id>, token_hash=<sha256_of_returned_refresh_token>)`

#### Scenario: Rollback on RefreshToken insert failure
- **GIVEN** a registration request with a unique email
- **AND** the `INSERT INTO refresh_tokens` operation will fail (e.g. simulated DB error)
- **WHEN** the endpoint `POST /api/v1/auth/register` is invoked
- **THEN** the response is 5xx (an error response, not 201)
- **AND** the `users` table has NO row for that email
- **AND** the `user_roles` table has NO row referencing that email

#### Scenario: Rollback on UsuarioRol insert failure
- **GIVEN** a registration request with a unique email
- **AND** the `INSERT INTO user_roles` operation will fail
- **WHEN** the endpoint `POST /api/v1/auth/register` is invoked
- **THEN** the response is 5xx
- **AND** the `users` table has NO row for that email

### Requirement: Refresh operation is atomic
The system SHALL perform every refresh token operation (revocation of the presented token, optional bulk revocation on replay detection, creation of the new token pair) within a single database transaction. If any step fails, NONE of the UPDATEs nor INSERTs SHALL be persisted.

#### Scenario: All updates and insert commit together
- **GIVEN** a valid, non-revoked refresh token `T1` issued to user `U`
- **WHEN** `POST /api/v1/auth/refresh` is invoked with `T1`
- **THEN** the response is 200 with a new `TokenPairResponse`
- **AND** the row for `T1` has `revoked_at IS NOT NULL`
- **AND** there exists a new row in `refresh_tokens` for user `U` with the hash of the returned refresh token

#### Scenario: Replay detection rolls back partial updates
- **GIVEN** a previously revoked refresh token `T1` of user `U`
- **AND** the bulk revocation (`UPDATE refresh_tokens SET revoked_at = now() WHERE user_id = U AND revoked_at IS NULL`) is initiated
- **AND** a simulated failure occurs after the bulk UPDATE flushes but before the response is sent
- **WHEN** the failure propagates out of the service
- **THEN** the response is 5xx
- **AND** the state of `refresh_tokens` for user `U` is unchanged (no tokens revoked by the failed attempt)

### Requirement: Auth dependencies use a read-only direct session
The dependencies `get_current_user` and `get_optional_user` SHALL open a SQLAlchemy session directly (via `get_session_factory()()`) for the sole purpose of executing the `SELECT users WHERE id = ? AND is_active AND eliminado_en IS NULL` query, and SHALL close the session in a `finally` block. They SHALL NOT open a `UnitOfWork` context, SHALL NOT perform writes, and SHALL NOT depend on `Depends(get_db)`.

#### Scenario: get_current_user does not use Depends(get_db)
- **WHEN** the signature of `get_current_user` is inspected
- **THEN** it has no `db` parameter with `Depends(get_db)`
- **AND** the only `Depends` is the OAuth2 token extraction (`oauth2_scheme`)

#### Scenario: get_optional_user does not use Depends(get_db)
- **WHEN** the signature of `get_optional_user` is inspected
- **THEN** it has no `db` parameter with `Depends(get_db)`

#### Scenario: Session is closed in finally
- **WHEN** `get_current_user` executes (successful path or exception path)
- **THEN** the session opened via `get_session_factory()()` is closed (via `try: ... finally: session.close()`)

### Requirement: get_db is removed from the public contract
The module `backend/shared/database.py` SHALL NOT export a `get_db()` generator function after this change is applied. Any consumer attempting `from backend.shared.database import get_db` SHALL receive an `ImportError`.

#### Scenario: get_db is not importable
- **WHEN** Python code executes `from backend.shared.database import get_db`
- **THEN** it raises `ImportError`

#### Scenario: No production code references get_db
- **WHEN** the codebase is searched with `rg "get_db" backend/`
- **THEN** there are 0 matches in `backend/features/`, `backend/shared/`, and `backend/dependencies.py`
- **AND** there are 0 matches in `backend/tests/conftest.py` related to `override_get_db` or `app.dependency_overrides[get_db]`

### Requirement: Password hashing with bcrypt
The system SHALL hash all user passwords with bcrypt and a cost factor of at least 12 before persisting. Plaintext passwords MUST NEVER be written to the database, logs, or any sink. (RN-AU01)

#### Scenario: Password is hashed on registration
- **WHEN** a user registers with `password: "mypassword123"`
- **THEN** the row in `users.password_hash` is a bcrypt string starting with `$2b$12$` and is not equal to `"mypassword123"`

#### Scenario: Same password produces different hashes
- **WHEN** two users register with the same plaintext password
- **THEN** their stored `password_hash` values are different (per-record salt)

#### Scenario: Password verification with correct value
- **WHEN** `verify_password(plain, stored_hash)` is called with the original plaintext
- **THEN** it returns `True`

#### Scenario: Password verification with wrong value
- **WHEN** `verify_password(plain, stored_hash)` is called with a wrong plaintext
- **THEN** it returns `False`

### Requirement: JWT access token contract
The system SHALL issue access tokens as JWTs signed with HS256 (configurable to RS256). Each access token SHALL have a 30-minute lifetime by default and MUST include the claims `sub` (user id as string), `email`, `roles` (list of role codes), `exp` (unix timestamp), and `type: "access"`. (RN-AU02)

#### Scenario: Access token contains required claims
- **WHEN** `create_access_token(user_id=42, email="a@b.com", roles=["CLIENT"])` is called
- **THEN** the unverified payload contains `sub: "42"`, `email: "a@b.com"`, `roles: ["CLIENT"]`, `type: "access"`, and `exp` is set to roughly now + 30 minutes

#### Scenario: Tampered token is rejected
- **WHEN** `decode_access_token(token)` receives a token whose signature has been altered
- **THEN** it returns `None`

#### Scenario: Expired token is rejected
- **WHEN** `decode_access_token(token)` receives a token whose `exp` is in the past
- **THEN** it returns `None`

### Requirement: Refresh token contract
The system SHALL issue refresh tokens as opaque UUID v4 strings with a 7-day lifetime. The raw token is returned to the client; the database SHALL store only the SHA-256 hex digest (CHAR(64)) of the token. (RN-AU03)

#### Scenario: Refresh token format
- **WHEN** `create_refresh_token()` is called
- **THEN** it returns a string parseable as a UUID with `version == 4`

#### Scenario: Refresh token storage uses hashed form
- **WHEN** a refresh token is persisted by the auth service
- **THEN** the row in `refresh_tokens.token_hash` is the SHA-256 hex digest (64 lowercase hex chars) of the raw token, never the raw token

### Requirement: Refresh token rotation
The system SHALL rotate refresh tokens on every `POST /api/v1/auth/refresh`: the presented token is revoked (its `revoked_at` is set to the current timestamp) and a new pair `(access_token, refresh_token)` is issued. (RN-AU04)

#### Scenario: Successful refresh marks old token revoked
- **WHEN** a valid refresh token is presented to `/api/v1/auth/refresh`
- **THEN** the response is 200 with a new `(access_token, refresh_token)` pair AND the old token row has `revoked_at IS NOT NULL`

#### Scenario: New refresh token differs from old one
- **WHEN** a refresh succeeds
- **THEN** the new `refresh_token` value is different from the one presented

### Requirement: Replay attack detection
The system SHALL detect refresh token replay. If a token is presented whose `revoked_at` is already set (revoked by a previous rotation OR by logout), the system MUST treat it as a compromise and revoke ALL refresh tokens of that user (`UPDATE refresh_tokens SET revoked_at = now() WHERE user_id = ? AND revoked_at IS NULL`), then return 401. (RN-AU05)

#### Scenario: Reusing a rotated token revokes all user tokens
- **GIVEN** a user has logged in and obtained refresh token `T1`
- **AND** has rotated it once, obtaining `T2`
- **WHEN** the same `T1` is presented again to `/api/v1/auth/refresh`
- **THEN** the response is 401 AND every refresh token row of that user has `revoked_at IS NOT NULL`

#### Scenario: Reusing a logged-out token revokes all user tokens
- **GIVEN** a user logged in obtaining `T1`, then logged out
- **WHEN** `T1` is presented to `/api/v1/auth/refresh`
- **THEN** the response is 401 AND every refresh token row of that user has `revoked_at IS NOT NULL`

### Requirement: Login rate limiting
The system SHALL rate-limit `POST /api/v1/auth/login` to 5 attempts per IP per 15 minutes. Exceeding the limit returns HTTP 429 with a `Retry-After` header. (RN-AU06)

#### Scenario: Login limit exceeded
- **GIVEN** the same IP has issued 5 login requests in the last 15 minutes
- **WHEN** the IP issues a 6th request
- **THEN** the response is 429

### Requirement: Register rate limiting
The system SHALL rate-limit `POST /api/v1/auth/register` to 3 requests per IP per hour.

#### Scenario: Register limit exceeded
- **GIVEN** the same IP has issued 3 register requests in the last hour
- **WHEN** the IP issues a 4th request
- **THEN** the response is 429

### Requirement: Refresh rate limiting
The system SHALL rate-limit `POST /api/v1/auth/refresh` to 10 requests per IP per minute.

#### Scenario: Refresh limit exceeded
- **GIVEN** the same IP has issued 10 refresh requests in the last minute
- **WHEN** the IP issues an 11th request
- **THEN** the response is 429

### Requirement: Auto-assign CLIENT role on registration
The system SHALL assign the role `CLIENT` (id=4) automatically to every newly registered user. The request body MUST NOT carry a role field; if present, it SHALL be ignored. (RN-AU07)

#### Scenario: Registration grants CLIENT role
- **WHEN** a user registers via `/api/v1/auth/register`
- **THEN** a row exists in `user_roles` with `(user_id, role_id=4)`

### Requirement: Login error message uniformity
The system SHALL return identical error messages for "email does not exist" and "wrong password" cases on `/api/v1/auth/login`. The response SHALL be 401 with body containing `detail: "Credenciales inválidas"`. (RN-AU08)

#### Scenario: Same message for unknown email and wrong password
- **WHEN** a login is attempted with an unknown email
- **AND** another login is attempted with a known email and wrong password
- **THEN** both responses have status 401 AND identical `detail` fields

### Requirement: Registration endpoint
The system SHALL expose `POST /api/v1/auth/register` that accepts `RegisterRequest({nombre, apellido, email, password})` with `EmailStr`, `password min 8 chars`, and `nombre/apellido min 2 max 80 chars`. On success it SHALL return 201 with `TokenPairResponse`. On duplicate email it SHALL return 409 (RFC 7807). On invalid input it SHALL return 422 (RFC 7807 with `errors[]`).

> **Spec note**: `docs/Integrador.txt` section 5.1 documents the response as `UserResponse`. The team has chosen to keep `TokenPairResponse` so US-001 leaves the user logged in. This is an accepted UX deviation tracked in `auth-backend-stabilization/proposal.md`.

#### Scenario: Successful registration
- **WHEN** a valid `RegisterRequest` is posted
- **THEN** the response is 201 with `access_token`, `refresh_token`, `token_type: "bearer"`, `expires_in`

#### Scenario: Duplicate email
- **WHEN** an email already present in `users` is posted
- **THEN** the response is 409 with RFC 7807 body `{type, title: "Conflict", status: 409, detail, instance}`

#### Scenario: Weak password rejected
- **WHEN** a password shorter than 8 characters is posted
- **THEN** the response is 422 with RFC 7807 body including `errors[]` listing the `password` field

### Requirement: Login endpoint
The system SHALL expose `POST /api/v1/auth/login` that accepts `LoginRequest({email, password})`, validates credentials, and returns 200 with `TokenPairResponse` on success or 401 on failure.

#### Scenario: Successful login
- **WHEN** valid credentials are posted
- **THEN** the response is 200 with `access_token`, `refresh_token`, `token_type: "bearer"`, `expires_in: settings.JWT_ACCESS_TOKEN_EXPIRE_MINUTES * 60`

#### Scenario: Inactive user cannot log in
- **WHEN** a deactivated user (`is_active = False`) attempts login with correct credentials
- **THEN** the response is 401 with the same `detail` as the wrong-password case

### Requirement: Refresh endpoint
The system SHALL expose `POST /api/v1/auth/refresh` that accepts `RefreshRequest({refresh_token})` and returns 200 with a new `TokenPairResponse` on success or 401 on failure.

#### Scenario: Successful refresh
- **WHEN** a valid, non-revoked, non-expired refresh token is posted
- **THEN** the response is 200 AND the old token's `revoked_at` is set AND a new pair is issued

#### Scenario: Expired refresh token
- **WHEN** a refresh token with `expires_at < now()` is posted
- **THEN** the response is 401

#### Scenario: Unknown refresh token
- **WHEN** a refresh token whose hash is not in `refresh_tokens` is posted
- **THEN** the response is 401

### Requirement: Logout endpoint
The system SHALL expose `POST /api/v1/auth/logout` that accepts `RefreshRequest({refresh_token})` and revokes the token by setting `revoked_at = now()`. Successful response is 204 with empty body.

#### Scenario: Successful logout
- **WHEN** a valid refresh token is posted to `/api/v1/auth/logout`
- **THEN** the response is 204 AND the token row has `revoked_at IS NOT NULL`

#### Scenario: Subsequent refresh after logout fails
- **GIVEN** a refresh token was logged out
- **WHEN** the same token is posted to `/api/v1/auth/refresh`
- **THEN** the response is 401 AND replay-attack handling kicks in (all user tokens revoked)

### Requirement: Authenticated /me endpoint
The system SHALL expose `GET /api/v1/auth/me` that requires a Bearer access token and returns 200 with `UserResponse({id, nombre, apellido, email, roles[], created_at})`.

#### Scenario: /me without token
- **WHEN** `/api/v1/auth/me` is requested without an Authorization header
- **THEN** the response is 401

#### Scenario: /me with valid token
- **WHEN** `/api/v1/auth/me` is requested with a valid Bearer token
- **THEN** the response is 200 with `id`, `nombre`, `apellido`, `email`, `roles`, `created_at`, and never `password_hash`

### Requirement: get_current_user dependency
The system SHALL provide an async FastAPI dependency `get_current_user` that extracts the Bearer token, validates it (signature + expiration + `type == "access"`), looks up the user (filtered by `is_active = True` AND `eliminado_en IS NULL`), and returns the `Usuario`. Failure SHALL raise `UnauthorizedError`.

#### Scenario: Missing token
- **WHEN** `get_current_user` is called without a token
- **THEN** it raises `UnauthorizedError`

#### Scenario: Invalid signature
- **WHEN** `get_current_user` is called with a token whose signature does not match `JWT_SECRET`
- **THEN** it raises `UnauthorizedError`

#### Scenario: Inactive user
- **WHEN** `get_current_user` is called with a valid token of a user whose `is_active = False`
- **THEN** it raises `UnauthorizedError`

#### Scenario: Refresh token used as access token
- **WHEN** `get_current_user` is called with a refresh-token-shaped JWT (`type != "access"`)
- **THEN** it raises `UnauthorizedError`

### Requirement: require_role factory dependency
The system SHALL provide a factory `require_role(*roles: str)` that returns a dependency. The dependency SHALL fetch the current user via `get_current_user` and check that at least one of the user's role codes intersects the required set. Failure SHALL raise `ForbiddenError` (HTTP 403). (RN-RB09, RN-RB10)

#### Scenario: User has required role
- **WHEN** a user with `roles=["ADMIN"]` requests an endpoint protected by `require_role("ADMIN")`
- **THEN** the dependency returns the user

#### Scenario: User lacks required role
- **WHEN** a user with `roles=["CLIENT"]` requests an endpoint protected by `require_role("ADMIN")`
- **THEN** the dependency raises `ForbiddenError` and the response is 403

#### Scenario: Multiple acceptable roles
- **WHEN** an endpoint is protected by `require_role("ADMIN", "PEDIDOS")` and the user holds `PEDIDOS`
- **THEN** the dependency returns the user

### Requirement: RefreshToken data model
The system SHALL persist refresh tokens with the following columns aligned with `docs/Integrador.txt` section 3.1: `id BIGSERIAL PK`, `user_id BIGINT FK→users.id ON DELETE CASCADE`, `token_hash CHAR(64) UNIQUE NOT NULL`, `expires_at TIMESTAMPTZ NOT NULL`, `revoked_at TIMESTAMPTZ NULL`, plus the BaseModel timestamps (`creado_en`, `actualizado_en`, `eliminado_en`). The model SHALL NOT contain `family_id` or `used` columns.

#### Scenario: Model does not declare family_id
- **WHEN** the `RefreshToken` SQLAlchemy class is introspected
- **THEN** it has no attribute named `family_id`

#### Scenario: Model does not declare used
- **WHEN** the `RefreshToken` SQLAlchemy class is introspected
- **THEN** it has no attribute named `used`

#### Scenario: token_hash is CHAR(64)
- **WHEN** the `RefreshToken.token_hash` column is introspected
- **THEN** its type is a fixed-length string of length 64

### Requirement: API versioned prefix
The system SHALL mount the auth router under the prefix `/api/v1/auth`. All documented endpoints, the `oauth2_scheme.tokenUrl`, the README, and curl examples SHALL use this prefix. (Integrador.txt §5)

#### Scenario: Auth endpoints respond under /api/v1
- **WHEN** a client posts to `/api/v1/auth/login` with valid credentials
- **THEN** the response is 200 with a token pair

#### Scenario: Auth endpoints do not respond at unversioned path
- **WHEN** a client posts to `/api/auth/login`
- **THEN** the response is 404

### Requirement: TokenPairResponse expires_in derives from settings
The system SHALL compute `TokenPairResponse.expires_in` as `settings.JWT_ACCESS_TOKEN_EXPIRE_MINUTES * 60` rather than a hardcoded literal.

#### Scenario: expires_in matches configured TTL
- **GIVEN** `settings.JWT_ACCESS_TOKEN_EXPIRE_MINUTES = 30`
- **WHEN** any endpoint that returns `TokenPairResponse` is invoked
- **THEN** the response field `expires_in` equals `1800`

#### Scenario: expires_in tracks config changes
- **GIVEN** `settings.JWT_ACCESS_TOKEN_EXPIRE_MINUTES = 60`
- **WHEN** any endpoint that returns `TokenPairResponse` is invoked
- **THEN** the response field `expires_in` equals `3600`

### Requirement: Schema length constraints align with spec
The system SHALL validate `RegisterRequest.nombre` and `RegisterRequest.apellido` with `min_length=2` and `max_length=80` (per `docs/Integrador.txt` §6.1).

#### Scenario: Apellido longer than 80 chars rejected
- **WHEN** a register request with `apellido` of 81 characters is posted
- **THEN** the response is 422

### Requirement: All error responses use RFC 7807 format
The system SHALL register exception handlers in `main.py` for every typed exception (`UnauthorizedError`, `ForbiddenError`, `NotFoundError`, `ConflictError`, `ValidationError`, `BusinessRuleError`), for `RequestValidationError`, for FastAPI/Starlette `HTTPException`, and for the catch-all `Exception`. The handlers SHALL produce RFC 7807 bodies (`type, title, status, detail, instance`). (See `openspec/specs/error-handling/spec.md`.)

#### Scenario: 404 from unknown route is RFC 7807
- **WHEN** a GET to a non-existent path is issued
- **THEN** the response is 404 with body `{type, title: "Not Found", status: 404, detail, instance}`

#### Scenario: ConflictError yields RFC 7807 409
- **WHEN** an operation raises `ConflictError`
- **THEN** the response is 409 with body containing `title: "Conflict"`, `status: 409`, `detail`

#### Scenario: Validation error yields RFC 7807 422 with errors[]
- **WHEN** a POST request fails Pydantic validation
- **THEN** the response is 422 with body containing `errors[]` of `{field, message}`
