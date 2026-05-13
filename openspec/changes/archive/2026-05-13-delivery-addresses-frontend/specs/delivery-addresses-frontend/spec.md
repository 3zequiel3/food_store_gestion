## Purpose

UI cliente para gestionar direcciones de entrega propias: listar, crear, editar, eliminar y establecer predeterminada. Consume los endpoints del backend `delivery-addresses` (US-024 a US-028).

## ADDED Requirements

### Requirement: Página de direcciones en /cliente/direcciones
El sistema SHALL renderizar `AddressesPage` en la ruta `/cliente/direcciones`, reemplazando el `PlaceholderPage`. SHALL mostrar el listado de direcciones obtenido de `GET /api/v1/direcciones` via `useAddresses()`. Mientras carga SHALL mostrar skeletons. Si falla SHALL mostrar error con botón "Reintentar". Si no hay direcciones SHALL mostrar un estado vacío con CTA para agregar la primera.

#### Scenario: Usuario con direcciones ve el listado
- **WHEN** un cliente navega a `/cliente/direcciones`
- **THEN** la página muestra todas sus direcciones, con la predeterminada primera y badge "Predeterminada" visible

#### Scenario: Estado vacío con CTA
- **WHEN** el usuario no tiene ninguna dirección
- **THEN** la página muestra un mensaje de estado vacío y un botón "Agregar mi primera dirección"

#### Scenario: Error de red con reintentar
- **WHEN** el GET /direcciones falla
- **THEN** se muestra error y botón "Reintentar" que dispara refetch

### Requirement: Tarjeta de dirección con acciones
El sistema SHALL renderizar cada dirección como una tarjeta (`AddressCard`) con: datos completos de la dirección (calle numero, piso_depto si existe, ciudad, código postal, referencia si existe), badge "Predeterminada" si `es_principal`, botón "Editar", botón "Eliminar" con confirmación inline, y botón "Establecer como predeterminada" si `!es_principal`. Los botones de acción SHALL estar deshabilitados si cualquier mutación global está en curso.

#### Scenario: Badge en dirección principal
- **WHEN** una dirección tiene es_principal === true
- **THEN** muestra un badge o indicador visual "Predeterminada" y NO muestra el botón "Establecer como predeterminada"

#### Scenario: Confirmación inline antes de eliminar
- **WHEN** el usuario hace click en "Eliminar"
- **THEN** la tarjeta muestra "¿Eliminar esta dirección?" con botones "Sí, eliminar" y "Cancelar" sin abrir ningún dialog modal

#### Scenario: Cancelar eliminación restaura la tarjeta
- **WHEN** el usuario hace click en "Cancelar" dentro de la confirmación inline
- **THEN** la tarjeta vuelve a su estado normal sin eliminar nada

### Requirement: Modal de alta y edición de dirección
El sistema SHALL incluir un `AddressModal` (`<dialog>` nativo) que funciona en dos modos: alta (sin prop `address`) y edición (con prop `address: DireccionRead` pre-cargada). El modal SHALL tener campos: calle (requerido), numero (requerido), piso_depto (opcional), ciudad (requerido), codigo_postal (requerido), referencia (opcional). Submit en modo alta llama POST /direcciones; en modo edición llama PUT /direcciones/{id}. Tras éxito cierra el modal e invalida la query.

#### Scenario: Alta crea nueva dirección
- **WHEN** el usuario completa el formulario y hace submit en modo alta
- **THEN** se llama POST /direcciones, el modal se cierra y la nueva dirección aparece en el listado

#### Scenario: Edición pre-carga los valores actuales
- **WHEN** el usuario abre el modal de edición de una dirección
- **THEN** todos los campos muestran los valores actuales de esa dirección

#### Scenario: Edición actualiza sin cambiar otros campos
- **WHEN** el usuario solo modifica "ciudad" y hace submit
- **THEN** se llama PUT /direcciones/{id} y los demás campos se preservan

#### Scenario: Botón submit deshabilitado durante isPending
- **WHEN** la mutación está en curso
- **THEN** el botón muestra spinner + texto "Guardando…" y está deshabilitado

#### Scenario: Error backend mostrado en el modal
- **WHEN** el backend responde 422 (ej: campo requerido vacío tras trim)
- **THEN** el modal muestra el error inline sin cerrarse

### Requirement: Validación Zod del formulario de dirección
El sistema SHALL validar con `addressSchema.ts`: `calle` min 1 / max 255, `numero` min 1 / max 20, `ciudad` min 1 / max 100, `codigo_postal` min 1 / max 20; todos con `.trim()` antes de validar. `piso_depto` nullable: string vacío → `undefined` (omitido del payload). `referencia` nullable: string vacío → `undefined`.

#### Scenario: Campo requerido vacío
- **WHEN** el usuario deja "calle" vacío y hace blur
- **THEN** aparece el error "Requerido" bajo el campo

#### Scenario: Piso/depto vacío se omite del payload
- **WHEN** el usuario no completa piso_depto y guarda
- **THEN** el POST body no incluye la clave piso_depto

### Requirement: Establecer dirección predeterminada
El sistema SHALL permitir al usuario establecer cualquier dirección como predeterminada via `PATCH /direcciones/{id}/predeterminada` (`useSetPrincipal`). Tras éxito SHALL invalidar `['addresses']` para que la lista se refresque con el nuevo orden (principal primero). El botón SHALL estar visible solo si `!es_principal` y deshabilitado durante isPending.

#### Scenario: Marcar como predeterminada actualiza la lista
- **WHEN** el usuario hace click en "Establecer como predeterminada"
- **THEN** la dirección pasa a tener badge "Predeterminada" y sube al tope de la lista

#### Scenario: Botón oculto en la dirección ya predeterminada
- **WHEN** una dirección tiene es_principal === true
- **THEN** no hay botón "Establecer como predeterminada" en esa tarjeta

### Requirement: Módulo delivery-addresses con service y hooks
El sistema SHALL tener `features/delivery-addresses/` con: `types/` (`DireccionRead`, `DireccionCreate`, `DireccionUpdate`), `services/deliveryAddresses.service.ts` (getAddresses, createAddress, updateAddress, deleteAddress, setPrincipal), `hooks/` (useAddresses, useCreateAddress, useUpdateAddress, useDeleteAddress, useSetPrincipal), `schemas/addressSchema.ts`.

#### Scenario: deleteAddress no retorna body
- **WHEN** se llama deleteAddress(id)
- **THEN** hace DELETE a ENDPOINTS.direcciones.delete(id) y retorna void (204 sin body)

#### Scenario: setPrincipal usa el endpoint correcto
- **WHEN** se llama setPrincipal(id)
- **THEN** hace PATCH a ENDPOINTS.direcciones.predeterminada(id) y retorna DireccionRead
