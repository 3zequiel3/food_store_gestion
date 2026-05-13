## MODIFIED Requirements

### Requirement: React Router setup with route definitions
The system SHALL configure react-router-dom v6 with a centralized route configuration in `src/app/Router.tsx` defining ALL application routes with their correct access guards — even routes whose page components are not yet implemented (those use placeholder content). The complete route table is:

| Path | Guard | Allowed roles |
|---|---|---|
| `/` | public | all |
| `/products` | public | all |
| `/login`, `/register` | PublicRoute | unauthenticated only |
| `/cart` | PrivateRoute | all authenticated |
| `/checkout` | PrivateRoute | all authenticated |
| `/orders` | PrivateRoute + RoleRoute | CLIENT |
| `/profile` | PrivateRoute | all authenticated |
| `/addresses` | PrivateRoute + RoleRoute | CLIENT |
| `/admin/products` | PrivateRoute + RoleRoute | ADMIN, STOCK |
| `/admin/categories` | PrivateRoute + RoleRoute | ADMIN, STOCK |
| `/admin/ingredients` | PrivateRoute + RoleRoute | ADMIN, STOCK |
| `/admin/orders` | PrivateRoute + RoleRoute | ADMIN, PEDIDOS |
| `/admin/users` | PrivateRoute + RoleRoute | ADMIN |
| `/admin/metrics` | PrivateRoute + RoleRoute | ADMIN |
| `/forbidden` | public | all |
| `*` | public | all (404) |

#### Scenario: Routes are defined centrally
- **WHEN** the application initializes routing
- **THEN** all routes in the table above are defined in `frontend/src/app/Router.tsx`

#### Scenario: Navigation between pages works
- **WHEN** a user clicks a navigation link
- **THEN** the browser URL updates and the correct page component renders without full page reload

## ADDED Requirements

### Requirement: Post-login redirect to original URL
The system SHALL redirect the user to `location.state?.from` after a successful login if that value exists, falling back to `/`. The `from` location is set by `PrivateRoute` when redirecting an unauthenticated user to `/login`.

#### Scenario: User is redirected back after login
- **WHEN** an unauthenticated user tries to access `/orders` and is redirected to `/login`, then logs in successfully
- **THEN** they are navigated to `/orders` (not to `/`)

#### Scenario: Direct login navigates to home
- **WHEN** a user navigates directly to `/login` (no prior redirect) and logs in successfully
- **THEN** they are navigated to `/`
