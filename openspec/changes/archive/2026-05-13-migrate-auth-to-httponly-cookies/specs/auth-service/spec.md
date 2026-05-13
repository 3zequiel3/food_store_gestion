# auth-service delta

## Purpose
Define the frontend auth-service contract for cookie-backed sessions and session-only login responses.

## ADDED Requirements

### Requirement: Frontend auth service uses cookie session responses
The frontend auth service SHALL not receive, pass, or persist raw access/refresh tokens.

#### Scenario: Login returns user session only
- **WHEN** `login()` succeeds
- **THEN** it resolves with `{ user, expires_in, token_type: "cookie" }`
