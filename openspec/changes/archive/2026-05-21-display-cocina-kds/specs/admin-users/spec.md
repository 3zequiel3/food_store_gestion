# Spec Delta: admin-users

## ADDED Requirements

### Requirement: Alta de usuarios (Admin)

El sistema SHALL exponer `POST /api/v1/admin/usuarios`, protegido por `require_role("ADMIN")`, que crea un usuario nuevo a partir de email, contraseña, nombre, apellido, teléfono opcional y un conjunto de roles (`min_length=1`). La contraseña SHALL almacenarse hasheada con bcrypt. El email SHALL ser único: un email ya registrado MUST ser rechazado con HTTP 409. Cada código de rol provisto MUST existir en el catálogo (`ADMIN`, `STOCK`, `PEDIDOS`, `CLIENT`, `COCINA`); un código inexistente MUST ser rechazado con HTTP 422. En éxito el sistema SHALL responder 201 con `AdminUserResponse` (sin `password_hash`). El schema de request SHALL usar `extra="forbid"`.

Esta capacidad complementa el listado (GET), la edición de datos (PUT), el cambio de roles (PATCH `/rol`) y el cambio de estado (PATCH `/estado`) ya existentes; el módulo `admin_users` no creaba usuarios hasta ahora.

#### Scenario: Alta exitosa con rol COCINA
- **WHEN** un ADMIN envía `POST /api/v1/admin/usuarios` con email nuevo, contraseña, datos y `roles=["COCINA"]`
- **THEN** la respuesta es 201 con el usuario creado y el rol `COCINA` asignado

#### Scenario: Email duplicado
- **GIVEN** un usuario ya registrado con cierto email
- **WHEN** un ADMIN intenta crear otro usuario con el mismo email
- **THEN** la respuesta es 409

#### Scenario: Rol inexistente
- **WHEN** un ADMIN intenta crear un usuario con `roles=["NO_EXISTE"]`
- **THEN** la respuesta es 422

#### Scenario: Sin al menos un rol
- **WHEN** un ADMIN intenta crear un usuario con `roles=[]`
- **THEN** la respuesta es 422 (validación de `min_length=1`)

#### Scenario: Rol no autorizado no puede crear usuarios
- **WHEN** un usuario sin rol `ADMIN` invoca `POST /api/v1/admin/usuarios`
- **THEN** la respuesta es 403
