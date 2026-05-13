## Context

El backend expone 4 endpoints bajo `/api/v1/admin/usuarios`, todos con `require_role("ADMIN")`. La respuesta de listado es `AdminUserListResponse { items, total, page, page_size }`. Cada `AdminUserResponse` tiene: `id`, `email`, `nombre`, `apellido`, `telefono`, `is_active`, `roles[]`, `creado_en`, `actualizado_en`.

El panel admin ya existe en `/admin` con `AdminLayout`. La ruta `/admin/usuarios` apunta a `PlaceholderPage`.

## Goals / Non-Goals

**Goals:**
- Tabla paginada de usuarios con búsqueda (nombre/email) y filtro por rol.
- 3 modales de acción por fila: editar datos personales, cambiar roles, activar/desactivar.
- Feedback visual inmediato: badges de estado y roles, toast en éxito/error.

**Non-Goals:**
- Crear usuarios nuevos (no existe endpoint de alta desde admin — el registro es público).
- Eliminar usuarios (soft delete no expuesto en este sprint).
- Gestionar contraseñas desde admin.

## Decisions

### D1 — Tres modales separados (no uno combinado)

Cada acción (editar, cambiar rol, toggle estado) tiene semántica y consecuencias distintas. Cambiar rol revoca tokens; desactivar revoca tokens. Un modal combinado mezclaría consecuencias distintas en una misma acción. Tres modales separados permite feedback específico por acción y reduce errores accidentales.

### D2 — Roles como checkboxes con lista fija (no freeform)

Los roles válidos son exactamente 4: `CLIENT`, `ADMIN`, `STOCK`, `PEDIDOS`. El backend retorna 422 si se envía un código inexistente y 409 si la operación deja el sistema sin ningún ADMIN activo. Usar checkboxes con lista hardcodeada evita enviar roles inválidos y muestra claramente qué combinaciones son posibles.

### D3 — URL-first para filtros (search + rol en query params)

Consistente con el patrón del change #28 (`OrderFilters` en MisPedidosPage). Permite compartir la URL filtrada y que el browser back/forward preserve el estado de filtros.

### D4 — Invalidación optimista del cache al mutar

Al hacer `PUT`, `PATCH /rol`, o `PATCH /estado`: en `onSuccess` se invalida `['admin-users']` con TanStack Query. No se hace optimistic update — las consecuencias (revocación de tokens) son side effects que el backend maneja; es más seguro esperar la respuesta real antes de actualizar la UI.

### D5 — `ToggleEstadoModal` muestra confirmación explícita

Desactivar un usuario revoca sus tokens. El usuario admin debe confirmar la acción antes de ejecutarla. El modal muestra el nombre del usuario y el efecto esperado antes del botón de confirmación.

### D6 — Feature folder `features/admin-users/`

Consistente con el patrón Feature-First del proyecto. Aislado de `features/orders/` y `features/payments/`. No comparte lógica con el perfil público del cliente (`features/user-profile/`).

## Risks / Trade-offs

- **[Riesgo] Backend retorna HTTP 409 si se elimina el último ADMIN** → El hook `useChangeRol` captura el 409 y muestra un toast de error descriptivo. El modal no se cierra ante error.
- **[Riesgo] Paginación con filtros activos** → Al cambiar filtros, resetear a página 1. Si no se resetea, podría mostrarse una página vacía cuando hay resultados en la primera página.
- **[Trade-off] Lista de roles hardcodeada** → Si el backend agrega un nuevo rol, el frontend necesita actualización manual. Aceptable para este sprint — la lista de roles es estable.
