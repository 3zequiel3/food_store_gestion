## MODIFIED Requirements

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

## ADDED Requirements

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
