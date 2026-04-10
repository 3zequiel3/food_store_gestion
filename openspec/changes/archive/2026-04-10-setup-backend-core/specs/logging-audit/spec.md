## ADDED Requirements

### Requirement: Structured logging configuration
The system SHALL provide a logging configuration that outputs structured logs with timestamps, log levels, and context.

#### Scenario: Logger is configured on startup
- **WHEN** the application starts
- **THEN** logging is configured with handler outputting to stdout with format: `[LEVEL] [TIMESTAMP] [MODULE] MESSAGE`

#### Scenario: Log level can be set via environment
- **WHEN** `LOG_LEVEL=DEBUG` is set in environment
- **THEN** the application logs at DEBUG level; `LOG_LEVEL=INFO` sets INFO level, etc.

### Requirement: Request/response logging middleware
The system SHALL log all HTTP requests with method, path, status code, and duration for audit and debugging.

#### Scenario: Request is logged
- **WHEN** a GET request is made to `/products`
- **THEN** a log entry is recorded: `[INFO] [HH:MM:SS] GET /products → 200 OK (45ms)`

#### Scenario: Request errors are logged
- **WHEN** a request results in a 500 error
- **THEN** a log entry is recorded at ERROR level with the stack trace

### Requirement: Audit context (foundation for HistorialEstadoPedido)
The system SHALL provide infrastructure for tracking who performed an action and when (fields will be populated by services in later changes).

#### Scenario: User context can be extracted from JWT
- **WHEN** a request is processed and JWT token is present
- **THEN** the user ID and username are available in the request context for logging

### Requirement: Performance logging
The system SHALL record slow database queries and API endpoints for performance monitoring.

#### Scenario: Slow query is logged
- **WHEN** a database query takes longer than 1000ms
- **THEN** a WARNING-level log entry records the query and duration

#### Scenario: Slow endpoint is logged
- **WHEN** an API endpoint response time exceeds 5000ms
- **THEN** a WARNING-level log entry records the endpoint path and duration
