# admin-self-profile Specification

## Purpose

Define the admin self-service profile view. Admins need to view and edit their own profile (like clients already can) and the sidebar footer link must point to the self-profile route instead of the users list.

## Requirements

### Requirement: Admin self-profile route

The system SHALL expose `/admin/mi-perfil` accessible to users with role `ADMIN`. The route SHALL render a profile view reusing or adapting the existing client profile form component.

#### Scenario: Admin accesses self-profile

- **WHEN** a user with role `ADMIN` navigates to `/admin/mi-perfil`
- **THEN** the page renders with the admin's current data (nombre, email, etc.)

#### Scenario: Non-admin cannot access

- **WHEN** a user with role `CLIENT` navigates to `/admin/mi-perfil`
- **THEN** the response is 403 or redirect to unauthorized page

#### Scenario: Unauthenticated cannot access

- **WHEN** an anonymous user navigates to `/admin/mi-perfil`
- **THEN** the response is redirect to login

### Requirement: Admin can edit own profile

The system SHALL allow the admin to edit their personal data (nombre, email) via the self-profile page, using the existing `PUT /api/v1/usuarios/me` endpoint.

#### Scenario: Successful profile edit

- **WHEN** the admin modifies their nombre and saves
- **THEN** the change is persisted and the page reflects the updated data

#### Scenario: Validation error on invalid email

- **WHEN** the admin enters an invalid email format
- **THEN** the form shows a validation error without submitting

### Requirement: Sidebar footer links to self-profile

The admin sidebar footer SHALL link to `/admin/mi-perfil` instead of `/admin/usuarios`. (Previously: linked to `/admin/usuarios`)

#### Scenario: Sidebar footer shows "Mi Perfil" link

- **WHEN** an admin views the sidebar
- **THEN** the footer contains a link labeled "Mi Perfil" pointing to `/admin/mi-perfil`

#### Scenario: Click navigates to self-profile

- **WHEN** the admin clicks the footer link
- **THEN** the router navigates to `/admin/mi-perfil`
