# Spec Delta: routing-guards

## MODIFIED Requirements

### Requirement: Role-based route access
The system SHALL restrict admin routes to users with the ADMIN role, and SHALL restrict the kitchen display route `/cocina` to users with the `COCINA` or `ADMIN` role. The role catalog keeps the four canonical roles (`ADMIN`, `STOCK`, `PEDIDOS`, `CLIENT`) plus the newly added `COCINA`.

#### Scenario: Non-admin user accesses admin route
- **WHEN** a CLIENTE user navigates to `/admin/products`
- **THEN** a 403 Forbidden page is displayed

#### Scenario: Admin user accesses admin route
- **WHEN** an ADMIN user navigates to `/admin/products`
- **THEN** the admin products page renders normally

#### Scenario: COCINA user accesses /cocina
- **WHEN** a user with role `COCINA` navigates to `/cocina`
- **THEN** the kitchen display renders normally

#### Scenario: CLIENT user blocked from /cocina
- **WHEN** a user with only role `CLIENT` navigates to `/cocina`
- **THEN** a 403 Forbidden page is displayed

## ADDED Requirements

### Requirement: COCINA login lands on /cocina as exclusive view
The system SHALL redirect a user whose role is `COCINA` to `/cocina` after login, presenting it as the exclusive view for that role without exposing the rest of the application shell.

#### Scenario: COCINA login redirect
- **WHEN** a user with role `COCINA` logs in
- **THEN** they are redirected to `/cocina` and do not see the general navigation

### Requirement: /cocina excluded from inactivity auto-logout
The system SHALL exclude the `/cocina` route from the inactivity auto-logout timer, so the kitchen display stays active during the shift even without user interaction.

#### Scenario: /cocina does not auto-logout on inactivity
- **GIVEN** inactivity auto-logout active for the rest of the app
- **WHEN** the user remains on `/cocina` without interaction past the inactivity threshold
- **THEN** the session is not closed

#### Scenario: Other routes still auto-logout
- **GIVEN** inactivity auto-logout active
- **WHEN** the user remains on a non-`/cocina` route without interaction past the threshold
- **THEN** the session is closed as usual
