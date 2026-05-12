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
