# auth-forms Specification

## Purpose
Login and registration form components with client-side validation (react-hook-form + Zod), API error handling, and authStore integration. Implements US-001, US-002.

## Requirements

### Requirement: Login form with client-side validation
The system SHALL provide a `LoginForm` React component that uses `react-hook-form` with a Zod schema to validate `email` (valid email format) and `password` (non-empty) before submitting. On submit it SHALL call `authService.login()`, store the result via `useAuthStore.getState().login()`, and navigate to `/`. On 401 it SHALL display "Credenciales inválidas" inline. On 429 it SHALL display a toast "Demasiados intentos, intentá de nuevo más tarde". (US-002)

#### Scenario: Valid credentials log the user in
- **WHEN** the user fills valid email and password and submits the LoginForm
- **THEN** `authService.login` is called, `useAuthStore.login` is called with the token pair and user, and the user is navigated to `/`

#### Scenario: Empty password blocks submission
- **WHEN** the user submits the LoginForm with an empty password field
- **THEN** the form does NOT call `authService.login` and displays an inline validation message on the password field

#### Scenario: 401 response shows inline error
- **WHEN** `authService.login` rejects with HTTP 401
- **THEN** an error message "Credenciales inválidas" is displayed inside the form (not as a toast)

#### Scenario: 429 response shows toast error
- **WHEN** `authService.login` rejects with HTTP 429
- **THEN** `useUIStore.getState().pushToast` is called with `level: 'error'` and the rate-limit message

#### Scenario: Submit button shows loading state
- **WHEN** the form is submitting (awaiting `authService.login`)
- **THEN** the submit button is disabled and shows a loading indicator

### Requirement: Register form with client-side validation
The system SHALL provide a `RegisterForm` React component that uses `react-hook-form` with a Zod schema to validate `nombre` (min 2, max 80 chars), `apellido` (min 2, max 80 chars), `email` (valid email), and `password` (min 8 chars) before submitting. On success it SHALL call `useAuthStore.getState().login()` and navigate to `/`. On 409 (duplicate email) it SHALL display "Este email ya está registrado" inline. (US-001)

#### Scenario: Valid data creates an account and logs in
- **WHEN** the user fills all fields with valid data and submits the RegisterForm
- **THEN** `authService.register` is called, `useAuthStore.login` is invoked with the returned token pair and user, and the user is navigated to `/`

#### Scenario: Password shorter than 8 chars blocks submission
- **WHEN** the user submits RegisterForm with a password of 7 characters
- **THEN** the form does NOT call `authService.register` and shows an inline error on the password field

#### Scenario: Nombre shorter than 2 chars blocks submission
- **WHEN** the user submits RegisterForm with `nombre` of 1 character
- **THEN** the form does NOT call `authService.register` and shows an inline error on the nombre field

#### Scenario: 409 conflict shows inline error
- **WHEN** `authService.register` rejects with HTTP 409
- **THEN** an error message "Este email ya está registrado" is displayed inside the form

#### Scenario: Apellido field is present and required
- **WHEN** the user submits RegisterForm without filling the apellido field
- **THEN** the form does NOT submit and shows a required error on the apellido field

### Requirement: Login and Register pages wire the forms
The system SHALL update `LoginPage` and `RegisterPage` to render `LoginForm` and `RegisterForm` respectively, replacing the existing static HTML placeholders. The pages SHALL NOT contain form logic themselves — that lives in the form components.

#### Scenario: LoginPage renders LoginForm
- **WHEN** a user navigates to `/login`
- **THEN** the `LoginForm` component is rendered inside `LoginPage`

#### Scenario: RegisterPage renders RegisterForm
- **WHEN** a user navigates to `/register`
- **THEN** the `RegisterForm` component is rendered inside `RegisterPage`
