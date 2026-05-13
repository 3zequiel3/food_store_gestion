# auth-forms Specification

## Purpose
Login and registration form components with client-side validation (react-hook-form + Zod), API error handling, and authStore integration. Implements US-001, US-002.
## Requirements
### Requirement: Auth forms capability deprecated — consolidated into frontend-foundation

The legacy `auth-forms` capability has been superseded. All form specifications, validation schemas, and page composition SHALL be covered under `frontend-foundation` capability (`Requirement: Login and Register forms with TanStack Form + Zod`, `Requirement: Auth schemas with Zod`, and the route tree requirements). This capability is retained as a historical record; new form development SHALL reference `frontend-foundation` exclusively.

#### Scenario: Forms are built using TanStack Form

- **WHEN** a developer creates or maintains login/register forms
- **THEN** they use `frontend-foundation` specifications and implement with TanStack Form + Zod, not `auth-forms`

