## ADDED Requirements

### Requirement: Listado paginado de usuarios
El sistema SHALL exponer `GET /api/v1/admin/usuarios` que retorne todos los usuarios (activos e inactivos, no soft-deleted) con paginación, búsqueda por email o nombre, y filtro opcional por código de rol. Solo usuarios con rol ADMIN pueden acceder.

#### Scenario: Listado sin filtros
- **WHEN** un ADMIN hace `GET /api/v1/admin/usuarios?page=1&page_size=20`
- **THEN** el sistema retorna HTTP 200 con `items` (lista de usuarios), `total`, `page` y `page_size`

#### Scenario: Búsqueda por nombre parcial
- **WHEN** un ADMIN hace `GET /api/v1/admin/usuarios?search=juan`
- **THEN** el sistema retorna solo usuarios cuyo `nombre` o `email` contenga "juan" (case-insensitive)

#### Scenario: Filtro por rol
- **WHEN** un ADMIN hace `GET /api/v1/admin/usuarios?rol=STOCK`
- **THEN** el sistema retorna solo usuarios que tengan el rol STOCK

#### Scenario: Usuario sin rol ADMIN es rechazado
- **WHEN** un usuario con rol CLIENT hace `GET /api/v1/admin/usuarios`
- **THEN** el sistema retorna HTTP 403

---

### Requirement: Editar datos personales de un usuario (Admin)
El sistema SHALL exponer `PUT /api/v1/admin/usuarios/{id}` que permita al ADMIN actualizar `nombre`, `apellido` y `telefono` de cualquier usuario activo. El email, contraseña y roles NO son editables por este endpoint.

#### Scenario: Edición exitosa
- **WHEN** un ADMIN hace `PUT /api/v1/admin/usuarios/42` con `{"nombre": "Carlos", "apellido": "López"}`
- **THEN** el sistema retorna HTTP 200 con los datos actualizados del usuario

#### Scenario: Usuario no encontrado
- **WHEN** un ADMIN intenta editar un `id` que no existe o está soft-deleted
- **THEN** el sistema retorna HTTP 404

#### Scenario: Payload con campos no permitidos
- **WHEN** el payload incluye `email` o `password_hash`
- **THEN** el sistema retorna HTTP 422

---

### Requirement: Cambio de roles de un usuario (Admin)
El sistema SHALL exponer `PATCH /api/v1/admin/usuarios/{id}/rol` que reemplace el conjunto de roles del usuario objetivo. La operación MUST invalidar todos los refresh tokens del usuario modificado. El sistema MUST rechazar la operación si resultaría en cero usuarios ADMIN activos.

#### Scenario: Cambio de rol exitoso
- **WHEN** un ADMIN hace `PATCH /api/v1/admin/usuarios/42/rol` con `{"roles": ["STOCK"]}`
- **THEN** el sistema retorna HTTP 200 con el usuario actualizado, y los refresh tokens del usuario 42 quedan revocados

#### Scenario: Degradar último ADMIN
- **WHEN** un ADMIN intenta quitar el rol ADMIN al único usuario con ese rol
- **THEN** el sistema retorna HTTP 409 con mensaje de error descriptivo

#### Scenario: Rol inválido en payload
- **WHEN** el payload contiene un código de rol que no existe en el sistema
- **THEN** el sistema retorna HTTP 422

---

### Requirement: Activar o desactivar un usuario (Admin)
El sistema SHALL exponer `PATCH /api/v1/admin/usuarios/{id}/estado` que cambie `is_active` del usuario. Al desactivar, el sistema MUST revocar todos los refresh tokens del usuario. Un usuario desactivado no puede autenticarse.

#### Scenario: Desactivación exitosa
- **WHEN** un ADMIN hace `PATCH /api/v1/admin/usuarios/42/estado` con `{"is_active": false}`
- **THEN** el sistema retorna HTTP 200, `is_active` del usuario queda en `false`, y sus refresh tokens quedan revocados

#### Scenario: Activación de usuario previamente desactivado
- **WHEN** un ADMIN hace `PATCH /api/v1/admin/usuarios/42/estado` con `{"is_active": true}`
- **THEN** el sistema retorna HTTP 200 y el usuario puede volver a autenticarse

#### Scenario: Login bloqueado para usuario desactivado
- **WHEN** un usuario con `is_active = false` intenta hacer login
- **THEN** el sistema retorna HTTP 401 (ya garantizado por `get_current_user` que filtra `is_active = True`)

---

## ADDED Requirements (from change display-cocina-kds)

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
