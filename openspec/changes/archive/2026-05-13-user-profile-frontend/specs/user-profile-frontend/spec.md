## Purpose

UI cliente para que el usuario autenticado visualice y edite su perfil propio (nombre, apellido, teléfono) y cambie su contraseña con re-login forzado. Consume los endpoints del backend `user-profile` (US-061, US-062, US-063).

## ADDED Requirements

### Requirement: Página de perfil en /cliente/perfil
El sistema SHALL renderizar `ProfilePage` en la ruta `/cliente/perfil` — reemplazando el `PlaceholderPage` existente. La página SHALL mostrar los datos del usuario obtenidos de `GET /api/v1/usuarios/me` via `useProfile()` (TanStack Query). Mientras carga SHALL mostrar un skeleton. Si el request falla SHALL mostrar un mensaje de error con botón de reintento.

#### Scenario: Usuario autenticado accede a su perfil
- **WHEN** un cliente navega a `/cliente/perfil`
- **THEN** la página muestra su nombre, apellido, email (no editable) y teléfono actual, cargados desde el backend

#### Scenario: Skeleton mientras carga
- **WHEN** `useProfile()` está en estado `isLoading`
- **THEN** se muestran bloques skeleton en lugar de los campos del formulario

#### Scenario: Error de red
- **WHEN** el request a `/usuarios/me` falla con error de red
- **THEN** se muestra un mensaje de error y un botón "Reintentar" que dispara el refetch

### Requirement: Formulario de edición de datos personales
El sistema SHALL incluir un formulario con los campos `nombre`, `apellido` y `teléfono` (todos opcionales en el PATCH pero requeridos en el form para que no queden vacíos). El formulario SHALL usar TanStack Form con validación Zod onBlur. Los campos iniciales SHALL estar pre-cargados con los valores actuales del usuario. Al hacer submit SHALL llamar `PATCH /api/v1/usuarios/me` con solo los campos modificados.

#### Scenario: Submit exitoso actualiza el perfil
- **WHEN** el usuario modifica su nombre y hace submit
- **THEN** se llama PATCH /usuarios/me, la UI muestra confirmación de guardado y el authStore.user.nombre se actualiza

#### Scenario: Error de validación onBlur en nombre
- **WHEN** el usuario borra el campo nombre y hace blur
- **THEN** se muestra el error "Mínimo 2 caracteres" bajo el campo sin submitear

#### Scenario: Email no es editable
- **WHEN** el usuario ve el formulario de perfil
- **THEN** el campo email está deshabilitado (read-only), sin botón de cambio de email

#### Scenario: Botón guardando durante isPending
- **WHEN** la mutación de update está en curso
- **THEN** el botón "Guardar" está deshabilitado y muestra spinner + "Guardando…"

#### Scenario: Error 422 del backend mostrado inline
- **WHEN** el backend responde 422 (ej: nombre con solo espacios)
- **THEN** se muestra el `detail` del error en el formulario, sin redirigir

### Requirement: Validación Zod del formulario de perfil
El sistema SHALL validar el formulario de perfil con un schema Zod en `features/user-profile/schemas/profileSchema.ts`. Las reglas SHALL ser: `nombre` min 2 / max 80 caracteres; `apellido` min 2 / max 80 caracteres; `telefono` nullable — null o string que matchee `^\+?[\d\s\-\(\)]{6,30}$` (permisivo: permite + inicial, luego dígitos/espacios/guiones/paréntesis); campo vacío `""` SHALL ser transformado a `undefined` (campo omitido del payload, no a null).

#### Scenario: Nombre de 1 caracter es inválido
- **WHEN** el campo nombre contiene "A"
- **THEN** el error del campo es "Mínimo 2 caracteres"

#### Scenario: Teléfono vacío se omite del payload
- **WHEN** el usuario borra el campo teléfono y guarda
- **THEN** el PATCH no incluye la clave `telefono` en el body (campo preservado en el backend)

#### Scenario: Teléfono con formato internacional válido
- **WHEN** el usuario ingresa "+54 11 1234-5678"
- **THEN** no hay error de validación en el campo teléfono

### Requirement: Modal de cambio de contraseña
El sistema SHALL incluir un botón "Cambiar contraseña" en la página de perfil que abre un `<dialog>` modal nativo. El modal SHALL tener dos campos: `password_actual` y `password_nuevo` (mín. 8 caracteres). Al submitear SHALL llamar `POST /api/v1/usuarios/me/password`. Si el response es 204 SHALL ejecutar `clearSession()` y redirigir a `/login`. El modal SHALL cerrarse con el botón Cancelar o la tecla Escape.

#### Scenario: Cambio de contraseña exitoso fuerza re-login
- **WHEN** el usuario completa el modal con contraseña actual correcta y nueva válida
- **THEN** recibe 204, la sesión se limpia y es redirigido a /login

#### Scenario: Contraseña actual incorrecta muestra error 401
- **WHEN** el usuario ingresa su contraseña actual incorrectamente
- **THEN** el modal muestra "Credenciales inválidas" sin cerrar el modal ni redirigir

#### Scenario: Contraseña nueva igual a la actual muestra error 422
- **WHEN** el usuario ingresa la misma contraseña en ambos campos
- **THEN** el modal muestra el detail del backend: "La nueva contraseña debe ser diferente de la actual"

#### Scenario: Escape cierra el modal sin cambios
- **WHEN** el usuario presiona Escape mientras el modal está abierto
- **THEN** el modal se cierra y no se realizó ningún request

#### Scenario: Botón cancelar cierra el modal
- **WHEN** el usuario hace click en "Cancelar"
- **THEN** el modal se cierra y el formulario se resetea

### Requirement: Servicio y hooks de user-profile
El sistema SHALL tener un módulo `features/user-profile/` con: `types/userProfile.types.ts` (tipo `ProfileRead` con `id, email, nombre, apellido, telefono, roles, creado_en, actualizado_en`), `services/userProfile.service.ts` (funciones `getProfile()`, `updateProfile(data)`, `changePassword(payload)`), `hooks/useProfile.ts` (TanStack Query GET), `hooks/useUpdateProfile.ts` (useMutation PATCH), `hooks/useChangePassword.ts` (useMutation POST).

#### Scenario: getProfile retorna ProfileRead
- **WHEN** se llama getProfile()
- **THEN** hace GET a ENDPOINTS.usuarios.me y retorna el body tipado como ProfileRead

#### Scenario: updateProfile omite campos undefined
- **WHEN** se llama updateProfile({ nombre: "Juan" }) sin apellido ni telefono
- **THEN** el PATCH body contiene solo { nombre: "Juan" }

#### Scenario: changePassword mapea al contrato del backend
- **WHEN** se llama changePassword({ password_actual: "X", password_nuevo: "Y" })
- **THEN** el POST body es exactamente { password_actual: "X", password_nuevo: "Y" }
