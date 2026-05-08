## MODIFIED Requirements

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
