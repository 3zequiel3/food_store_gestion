# Spec Delta: admin-create-user

## ADDED Requirements

### Requirement: Endpoint de alta de usuarios (Admin)

El sistema SHALL exponer `POST /api/v1/admin/usuarios`, protegido por `require_role("ADMIN")`, que crea un usuario nuevo a partir de email, contraseña, nombre, apellido, teléfono opcional y un conjunto de roles (`min_length=1`, `extra="forbid"`). La contraseña SHALL almacenarse hasheada con bcrypt (reutilizando el hashing del registro existente). El email SHALL ser único: un email ya existente MUST ser rechazado con HTTP 409. Cada código de rol provisto MUST existir en el catálogo; un código inexistente MUST ser rechazado con HTTP 422. En éxito el sistema SHALL responder 201 con la representación del usuario creado (sin `password_hash`).

#### Scenario: Alta exitosa con rol COCINA
- **WHEN** un ADMIN envía `POST /api/v1/admin/usuarios` con email nuevo, contraseña, datos y `roles=["COCINA"]`
- **THEN** la respuesta es 201 con el usuario creado, su `password_hash` hasheado y el rol `COCINA` asignado

#### Scenario: Email duplicado es rechazado
- **GIVEN** un usuario ya registrado con `email="x@foodstore.com"`
- **WHEN** un ADMIN intenta crear otro usuario con el mismo email
- **THEN** la respuesta es 409

#### Scenario: Rol inexistente es rechazado
- **WHEN** un ADMIN intenta crear un usuario con `roles=["NO_EXISTE"]`
- **THEN** la respuesta es 422

#### Scenario: Rol no autorizado no puede crear usuarios
- **WHEN** un usuario sin rol `ADMIN` invoca `POST /api/v1/admin/usuarios`
- **THEN** la respuesta es 403

### Requirement: Formulario de alta con selector de tres roles comunes

El sistema SHALL ofrecer en el panel de administración un formulario de alta de usuarios con un selector de los tres roles más comunes, mostrados con labels en español: `ADMIN` ("Admin"), `CLIENT` ("Cliente") y `COCINA` ("Cocinero"). Los códigos enviados al backend MUST ser `ADMIN`, `CLIENT` y `COCINA`; los labels en español son solo de presentación (RN-71). Los roles `STOCK` y `PEDIDOS` siguen existiendo en el catálogo y se asignan mediante el endpoint `PATCH /rol` ya existente, no por este formulario de alta.

#### Scenario: Selector muestra labels en español y envía códigos
- **WHEN** el admin selecciona "Cocinero" en el formulario de alta
- **THEN** el formulario envía el código de rol `COCINA` al backend

#### Scenario: Alta desde el formulario crea el usuario
- **WHEN** el admin completa el formulario con datos válidos y rol "Cliente" y confirma
- **THEN** el usuario se crea con rol `CLIENT` y aparece en el listado de usuarios
