## ADDED Requirements

### Requirement: Auth service register function
The system SHALL provide `authService.register(data: RegisterRequest): Promise<AuthSuccessResponse>` that posts to `POST /api/v1/auth/register` and returns the token pair plus user info on success (HTTP 201). On failure it SHALL re-throw the `AxiosError` so the caller can inspect the status code. (US-001)

#### Scenario: Successful registration returns token pair and user
- **WHEN** `authService.register({ nombre, apellido, email, password })` is called with valid data
- **THEN** the function resolves with `{ accessToken, refreshToken, tokenType, expiresIn, user }` mapped from the backend `TokenPairResponse`

#### Scenario: Registration failure propagates the error
- **WHEN** the backend returns 409 or 422
- **THEN** `authService.register` rejects with the original `AxiosError` (status preserved)

### Requirement: Auth service login function
The system SHALL provide `authService.login(data: LoginRequest): Promise<AuthSuccessResponse>` that posts to `POST /api/v1/auth/login` and returns token pair plus user on success (HTTP 200). On failure it SHALL re-throw the `AxiosError`. (US-002)

#### Scenario: Successful login returns token pair and user
- **WHEN** `authService.login({ email, password })` is called with valid credentials
- **THEN** the function resolves with `{ accessToken, refreshToken, tokenType, expiresIn, user }`

#### Scenario: Login failure propagates the error
- **WHEN** the backend returns 401 or 429
- **THEN** `authService.login` rejects with the original `AxiosError`

### Requirement: Auth service refresh function
The system SHALL provide `authService.refresh(refreshToken: string): Promise<TokenPair>` that posts to `POST /api/v1/auth/refresh` with `{ refresh_token }` and returns the new token pair on success (HTTP 200). This function MUST use a plain `axios` call (not `apiClient`) to avoid interceptor re-entrancy. (US-003, US-066)

#### Scenario: Successful refresh returns new token pair
- **WHEN** `authService.refresh(token)` is called with a valid refresh token
- **THEN** the function resolves with `{ accessToken, refreshToken }`

#### Scenario: Refresh with invalid token rejects
- **WHEN** `authService.refresh` is called with an expired or revoked token
- **THEN** the function rejects with an `AxiosError` with status 401

#### Scenario: Refresh uses plain axios (not apiClient)
- **WHEN** `authService.refresh` is called
- **THEN** the request is sent without an Authorization header and without going through the apiClient interceptors

### Requirement: Auth service logout function
The system SHALL provide `authService.logout(refreshToken: string): Promise<void>` that posts to `POST /api/v1/auth/logout` with `{ refresh_token }`. On success (HTTP 204) it resolves. On failure it resolves silently (best-effort logout — local state is always cleared regardless). (US-004)

#### Scenario: Successful logout resolves
- **WHEN** `authService.logout(token)` is called with a valid token
- **THEN** the function resolves without throwing

#### Scenario: Failed logout still resolves
- **WHEN** `authService.logout` receives a network error or 401
- **THEN** the function resolves without throwing (local auth state will be cleared by the caller)

### Requirement: Auth service TypeScript contract
The system SHALL define and export the following TypeScript types in `src/features/auth/api/types.ts`:
- `RegisterRequest`: `{ nombre: string; apellido: string; email: string; password: string }`
- `LoginRequest`: `{ email: string; password: string }`
- `TokenPair`: `{ accessToken: string; refreshToken: string }`
- `AuthSuccessResponse`: `TokenPair & { tokenType: string; expiresIn: number; user: UsuarioProfile }`
- `UsuarioProfile`: `{ id: number; nombre: string; apellido: string; email: string; roles: string[] }`

#### Scenario: Types align with backend contract
- **WHEN** `authService.login` resolves
- **THEN** the returned object is assignable to `AuthSuccessResponse` without TypeScript errors

#### Scenario: UsuarioProfile roles is string array
- **WHEN** the backend returns `roles: [{ id: 4, codigo: "CLIENT", descripcion: "..." }]`
- **THEN** the mapper in `authService` extracts only the `codigo` strings into `UsuarioProfile.roles`
