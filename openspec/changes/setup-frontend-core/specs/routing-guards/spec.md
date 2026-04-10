## ADDED Requirements

### Requirement: React Router setup with route definitions
The system SHALL configure react-router-dom v6 with a centralized route configuration defining all application routes.

#### Scenario: Routes are defined centrally
- **WHEN** the application initializes routing
- **THEN** all routes are defined in `frontend/src/app/Router.tsx` with path, component, and access level

#### Scenario: Navigation between pages works
- **WHEN** a user clicks a navigation link
- **THEN** the browser URL updates and the correct page component renders without full page reload

### Requirement: Public route access
The system SHALL allow unauthenticated users to access public routes (home, login, register, product catalog).

#### Scenario: Unauthenticated user accesses public route
- **WHEN** an unauthenticated user navigates to `/products`
- **THEN** the products page renders normally

#### Scenario: Authenticated user accesses login page
- **WHEN** an authenticated user navigates to `/login`
- **THEN** they are redirected to the home page (no need to log in again)

### Requirement: Private route guards
The system SHALL protect private routes by checking authentication state from authStore before rendering.

#### Scenario: Unauthenticated user accesses private route
- **WHEN** an unauthenticated user navigates to `/checkout`
- **THEN** they are redirected to `/login` with the original URL saved for post-login redirect

#### Scenario: Authenticated user accesses private route
- **WHEN** an authenticated user navigates to `/checkout`
- **THEN** the checkout page renders normally

### Requirement: Role-based route access
The system SHALL restrict admin routes to users with the ADMIN role.

#### Scenario: Non-admin user accesses admin route
- **WHEN** a CLIENTE user navigates to `/admin/products`
- **THEN** a 403 Forbidden page is displayed

#### Scenario: Admin user accesses admin route
- **WHEN** an ADMIN user navigates to `/admin/products`
- **THEN** the admin products page renders normally

### Requirement: Error pages
The system SHALL display appropriate error pages for 404 (Not Found) and 403 (Forbidden) scenarios.

#### Scenario: User navigates to non-existent route
- **WHEN** a user navigates to `/this-does-not-exist`
- **THEN** a 404 Not Found page is displayed with a link back to home

#### Scenario: User lacks permission
- **WHEN** a user accesses a route they don't have permission for
- **THEN** a 403 Forbidden page is displayed with explanation
