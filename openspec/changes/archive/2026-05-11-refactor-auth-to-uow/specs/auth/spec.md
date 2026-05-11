# Spec Delta: auth — Service-owned transaction boundary

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
