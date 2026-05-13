# http-client Specification

## Purpose
Centralized Axios instance with JWT request interceptor, singleton-refresh response interceptor, and RFC 7807 error-to-toast handler. All API calls in the frontend go through this client.
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
The system SHALL implement a full response interceptor in `src/shared/api/client.ts` that handles 401 responses with a singleton refresh pattern: a module-level `isRefreshing` boolean and a `pendingQueue` array of `{resolve, reject}` callbacks. When a 401 is received and `isRefreshing` is `false`, the interceptor SHALL set `isRefreshing = true`, call `authService.refresh(refreshToken)`, update the store via `useAuthStore.getState().updateTokens()`, flush all pending callbacks with the new token, and retry the original request. Requests arriving while `isRefreshing` is `true` SHALL be enqueued and resolved after the refresh completes. If the refresh fails, the interceptor SHALL call `useAuthStore.getState().logout()`, reject all pending requests, and redirect to `/login`. (US-066)

#### Scenario: 401 response triggers token refresh attempt
- **WHEN** a response returns 401 Unauthorized and `isRefreshing` is `false`
- **THEN** the interceptor sets `isRefreshing = true` and calls `authService.refresh` with the current refresh token from `useAuthStore`

#### Scenario: Concurrent 401s are queued, not multi-refreshed
- **WHEN** three requests return 401 simultaneously and `isRefreshing` is already `true`
- **THEN** only one refresh call is made; the other two requests are enqueued and retried with the new token after the single refresh completes

#### Scenario: Successful refresh retries all queued requests
- **WHEN** the refresh call succeeds and returns a new token pair
- **THEN** `useAuthStore.updateTokens` is called, `isRefreshing` is reset to `false`, all queued requests are resolved with the new access token, and the original triggering request is retried

#### Scenario: Failed refresh clears auth and redirects
- **WHEN** `authService.refresh` rejects with 401
- **THEN** `useAuthStore.getState().logout()` is called, all queued requests are rejected, `isRefreshing` is reset to `false`, and `window.location.href` is set to `/login`

#### Scenario: 401 after refresh failure triggers logout
- **WHEN** token refresh also returns 401
- **THEN** authStore is cleared and user is redirected to `/login`

#### Scenario: Network error is handled gracefully
- **WHEN** a request fails due to network error (no response object)
- **THEN** `handleApiError` is called and a user-friendly error toast is displayed via `useUIStore`

### Requirement: RFC 7807 error handler
The system SHALL provide a `handleApiError(error: AxiosError): void` function in `src/shared/api/errorHandler.ts` that extracts the RFC 7807 `detail` field (or `errors[0].message` for 422 responses) from the error response body and calls `useUIStore.getState().pushToast({ id, message, level: 'error' })`. It SHALL NOT throw — it is a fire-and-forget side effect. HTTP 401 MUST be excluded (handled by the interceptor). (US-067)

#### Scenario: RFC 7807 detail becomes toast message
- **WHEN** an API call fails with a response body containing `{ detail: "Email ya registrado" }`
- **THEN** `handleApiError` calls `pushToast` with `message: "Email ya registrado"` and `level: 'error'`

#### Scenario: 422 validation error shows first error message
- **WHEN** an API call fails with 422 and `{ errors: [{ field: "password", message: "Mínimo 8 caracteres" }] }`
- **THEN** `handleApiError` calls `pushToast` with `message: "Mínimo 8 caracteres"`

#### Scenario: 401 errors are not handled by handleApiError
- **WHEN** an API call fails with HTTP 401
- **THEN** `handleApiError` does NOT push a toast (401 is handled by the refresh interceptor)

#### Scenario: Network error without response body shows generic message
- **WHEN** an API call fails with no response (network error)
- **THEN** `handleApiError` pushes a toast with a generic message like "Error de conexión, revisá tu red"

### Requirement: API response typing
The system SHALL provide TypeScript types for API responses to ensure type safety across the application.

#### Scenario: API responses are typed
- **WHEN** an API call returns a response
- **THEN** the response data is typed with the expected interface (e.g., `ApiResponse<Product[]>`)

#### Scenario: Error responses are typed
- **WHEN** an API call returns an error
- **THEN** the error response matches `ApiError` type with message, statusCode, and details fields

### Requirement: Axios sends cookies and does not inject Bearer tokens
The HTTP client SHALL use `withCredentials: true` and SHALL NOT attach `Authorization: Bearer` from local state.

#### Scenario: Request uses browser cookies
- **WHEN** an API request is made
- **THEN** auth cookies are sent by the browser/client cookie jar
- **AND** no localStorage token is read

