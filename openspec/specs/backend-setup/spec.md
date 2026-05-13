## Purpose

Define the core backend setup, testing infrastructure, and dependency injection patterns for the Food Store application.

## Requirements

### Requirement: FastAPI application initialization
The system SHALL provide a FastAPI application instance configured with necessary middleware, CORS, and error handling foundation.

#### Scenario: Application starts successfully
- **WHEN** the application starts with `uvicorn backend.main:app --reload`
- **THEN** the server listens on `http://localhost:8000` and responds to health check at `GET /health` with status 200

#### Scenario: CORS is configured for local development
- **WHEN** a request is made from `http://localhost:5173` (Vite frontend dev server)
- **THEN** the response includes `Access-Control-Allow-Origin: http://localhost:5173` header

#### Scenario: Request logging is active
- **WHEN** any HTTP request is received
- **THEN** the request method, path, status code, and response time (ms) are logged to stdout

### Requirement: Feature-first module structure
The system SHALL organize code into feature modules under `backend/features/`, with each feature containing router, service, repository, and model layers.

#### Scenario: Feature module exists with expected layout
- **WHEN** the backend is initialized
- **THEN** the directory structure contains:
  - `backend/features/auth/` with `router.py`, `service.py`, `repository.py`, `models.py`
  - `backend/features/products/` with same files
  - `backend/features/orders/` with same files
  - `backend/shared/` for base classes and common utilities

#### Scenario: Feature router is registered with main app
- **WHEN** a feature router is created in `backend/features/<feature>/router.py`
- **THEN** it is automatically registered with the main FastAPI app via `app.include_router()`

### Requirement: Dependency injection pattern
The system SHALL support dependency injection using FastAPI's `Depends()` for loose coupling and testability.

#### Scenario: Service can be injected into router
- **WHEN** a router endpoint uses `Depends(get_service)` 
- **THEN** the service instance is automatically provided by FastAPI's DI container

### Requirement: Environment configuration
The system SHALL read configuration from `.env` file during development and environment variables in production.

#### Scenario: Configuration is loaded from .env
- **WHEN** the application starts in development mode
- **THEN** it reads `DATABASE_URL`, `JWT_SECRET`, `API_PORT` from `.env` file

#### Scenario: Environment variables override .env
- **WHEN** `DATABASE_URL` is set as an environment variable
- **THEN** the application uses the environment variable value instead of the `.env` value

### Requirement: Middleware and exception handling foundation
The system SHALL provide base middleware infrastructure and global exception handlers (specific RFC 7807 handling in separate change).

#### Scenario: Unhandled exceptions are caught
- **WHEN** an unhandled exception occurs in a route
- **THEN** the application catches it and returns a 500 response (specific error format handled in `backend-error-handling-validation` change)

### Requirement: pytest integration
The system SHALL be configured for unit and integration testing with pytest, test fixtures, and test database setup. The test harness SHALL ensure that ALL FastAPI database dependencies (`get_db` AND `get_uow`) resolve to the in-memory SQLite test session, preventing any test from accidentally connecting to a real database.

#### Scenario: Test can be run
- **WHEN** developer runs `pytest backend/tests/`
- **THEN** all tests execute and report pass/fail status

#### Scenario: Database fixture is available
- **WHEN** a test uses `@pytest.fixture` for database session
- **THEN** it receives a clean test database session that is rolled back after the test

#### Scenario: get_uow dependency is overridden in tests
- **GIVEN** the `client` fixture is active and `DATABASE_URL` is unset (or points to a non-running server)
- **WHEN** a test invokes any endpoint declared with `Depends(get_uow)` (for example `GET /api/v1/categorias`)
- **THEN** the request resolves the UnitOfWork against the same in-memory SQLite session used by `test_db_session`, NEVER attempting a TCP connection to a real database server
- **AND** the response status is determined by the endpoint's business logic, NOT by `OperationalError: connection refused`

#### Scenario: TestClient and direct fixture queries share transactional visibility
- **GIVEN** a test seeds data via `test_db_session.add(...)` + `test_db_session.commit()` (or `flush()`)
- **WHEN** the test issues a request through `client` to an endpoint that uses `Depends(get_uow)`
- **THEN** the endpoint sees the data seeded by the fixture (because both sides share the same SQLite session/transaction)
- **AND** any data written by the endpoint is visible to subsequent `test_db_session.query(...)` calls within the same test

#### Scenario: Test isolation is preserved across get_uow requests
- **GIVEN** test A creates a row through an endpoint using `Depends(get_uow)` and the request triggers `uow.commit()`
- **WHEN** test B runs immediately after test A
- **THEN** test B starts with an empty SQLite database (the outer `connection.begin()` transaction in `test_db_session` is rolled back at teardown, discarding any commit made through `get_uow`)
