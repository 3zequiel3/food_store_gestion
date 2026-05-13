# auth delta

## Purpose
Define the cookie-backed auth contract for the backend auth endpoints and session handling.

## ADDED Requirements

### Requirement: Cookie-backed auth endpoints
Auth endpoints SHALL transport tokens via HttpOnly cookies instead of JSON response bodies.

#### Scenario: Login sets auth cookies
- **WHEN** valid credentials are posted to `/api/v1/auth/login`
- **THEN** the response sets `access_token` and `refresh_token` HttpOnly cookies with `SameSite=Lax` and `Secure=false` in dev
- **AND** the JSON body does not include raw token values

#### Scenario: Refresh rotates cookies
- **WHEN** `/api/v1/auth/refresh` receives a valid `refresh_token` cookie
- **THEN** the backend revokes the old refresh token and sets new access/refresh cookies

#### Scenario: Current user reads cookie
- **WHEN** a protected endpoint is requested with a valid `access_token` cookie
- **THEN** `get_current_user` authenticates the request successfully
