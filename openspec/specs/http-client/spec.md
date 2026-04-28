# http-client Specification

## Purpose
TBD - created by archiving change setup-frontend-core. Update Purpose after archive.
## Requirements
### Requirement: Axios instance with base configuration
The system SHALL provide a centralized Axios instance configured with the API base URL, default headers, and timeout.

#### Scenario: HTTP client uses API base URL
- **WHEN** an API call is made using the HTTP client
- **THEN** the request URL is prefixed with `VITE_API_URL` from environment configuration

#### Scenario: Default headers are set
- **WHEN** a request is sent
- **THEN** `Content-Type: application/json` and `Accept: application/json` headers are included

#### Scenario: Request timeout is configured
- **WHEN** a request takes longer than the configured timeout (30 seconds)
- **THEN** the request is aborted and an error is thrown

### Requirement: Request interceptor hooks
The system SHALL provide request interceptors that can modify outgoing requests (e.g., attach JWT token from authStore).

#### Scenario: Authorization header is attached
- **WHEN** an API request is made and authStore has an access token
- **THEN** the request includes `Authorization: Bearer <token>` header

#### Scenario: Request without auth proceeds normally
- **WHEN** an API request is made and authStore has no token
- **THEN** the request is sent without an Authorization header

### Requirement: Response interceptor hooks
The system SHALL provide response interceptors for centralized error handling (e.g., 401 triggers token refresh).

#### Scenario: 401 response triggers token refresh attempt
- **WHEN** a response returns 401 Unauthorized
- **THEN** the interceptor attempts to refresh the token and retry the original request

#### Scenario: 401 after refresh failure triggers logout
- **WHEN** token refresh also returns 401
- **THEN** authStore is cleared and user is redirected to `/login`

#### Scenario: Network error is handled gracefully
- **WHEN** a request fails due to network error
- **THEN** a user-friendly error message is displayed via toast notification

### Requirement: API response typing
The system SHALL provide TypeScript types for API responses to ensure type safety across the application.

#### Scenario: API responses are typed
- **WHEN** an API call returns a response
- **THEN** the response data is typed with the expected interface (e.g., `ApiResponse<Product[]>`)

#### Scenario: Error responses are typed
- **WHEN** an API call returns an error
- **THEN** the error response matches `ApiError` type with message, statusCode, and details fields

