# routing-guards delta

## Purpose
Define the routing guard behavior for cookie-backed auth session state on the frontend.

## ADDED Requirements

### Requirement: Guards use cookie-backed session state
Route guards SHALL derive local authentication from the user/session state, not token presence.

#### Scenario: User session allows private route
- **WHEN** `authStore.user` is present
- **THEN** private routes render without reading access tokens from localStorage
