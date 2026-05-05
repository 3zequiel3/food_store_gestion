# error-handling Specification

## Purpose
TBD - created by archiving change backend-error-handling-validation. Update Purpose after archive.
## Requirements
### Requirement: RFC 7807 error response format
The system SHALL return all error responses following RFC 7807 (Problem Details for HTTP APIs) with a consistent JSON structure.

#### Scenario: Error response contains required fields
- **WHEN** any error occurs in the API
- **THEN** the response body contains: `type` (string), `title` (string), `status` (integer HTTP code), `detail` (string human-readable message), `instance` (string request path)

#### Scenario: Validation errors include per-field details
- **WHEN** a request fails Pydantic validation
- **THEN** the response includes an `errors` array with objects containing `field` (dot-notation path) and `message` (description)

### Requirement: Custom domain exceptions
The system SHALL provide typed exception classes that map to specific HTTP status codes.

#### Scenario: NotFoundError maps to HTTP 404
- **WHEN** a resource is not found
- **THEN** a `NotFoundError` is raised and the response has status 404 with `title: "Not Found"`

#### Scenario: ForbiddenError maps to HTTP 403
- **WHEN** a user lacks permissions
- **THEN** a `ForbiddenError` is raised and the response has status 403 with `title: "Forbidden"`

#### Scenario: UnauthorizedError maps to HTTP 401
- **WHEN** authentication is missing or invalid
- **THEN** an `UnauthorizedError` is raised and the response has status 401 with `title: "Unauthorized"`

#### Scenario: ValidationError maps to HTTP 422
- **WHEN** a business rule validation fails
- **THEN** a `ValidationError` is raised and the response has status 422 with `title: "Validation Error"` and optional `errors` array

#### Scenario: ConflictError maps to HTTP 409
- **WHEN** a resource conflict occurs (e.g., duplicate unique field)
- **THEN** a `ConflictError` is raised and the response has status 409 with `title: "Conflict"`

#### Scenario: BusinessRuleError maps to HTTP 409 or 422
- **WHEN** a business rule is violated (e.g., invalid state transition)
- **THEN** a `BusinessRuleError` is raised and the response has status 409 (for state conflicts) or 422 (for validation failures)

### Requirement: Pydantic validation error mapping
The system SHALL convert FastAPI/Pydantic RequestValidationError to RFC 7807 format instead of the default FastAPI response.

#### Scenario: Missing required field
- **WHEN** a POST request omits a required field
- **THEN** the response is 422 with `errors` array listing the missing field

#### Scenario: Invalid field type
- **WHEN** a request sends a string where a number is expected
- **THEN** the response is 422 with `errors` array describing the type mismatch

### Requirement: Generic exception handler
The system SHALL catch all unhandled exceptions and return a sanitized 500 response.

#### Scenario: Unhandled Python exception
- **WHEN** an unexpected error occurs in any route
- **THEN** the response is 500 with `detail: "An unexpected error occurred. Please try again later."` and does NOT include stack trace, exception type, or internal details

#### Scenario: Error is logged server-side
- **WHEN** an unhandled exception occurs
- **THEN** the full exception with stack trace is logged at ERROR level on the server

### Requirement: Input sanitization
The system SHALL provide sanitization utilities for cleaning user input before database storage.

#### Scenario: Email sanitization
- **WHEN** `sanitize_email` is called with `"  Test@Example.COM  "`
- **THEN** it returns `"test@example.com"` (stripped + lowercased)

#### Scenario: String sanitization escapes HTML
- **WHEN** `sanitize_string` is called with `"<script>alert('xss')</script>"`
- **THEN** it returns `"&lt;script&gt;alert(&#x27;xss&#x27;)&lt;/script&gt;"`

#### Scenario: Phone sanitization removes invalid characters
- **WHEN** `sanitize_phone` is called with `"phone123!@#"`
- **THEN** it returns `"123"` (only digits, +, -, (, ), spaces kept)

