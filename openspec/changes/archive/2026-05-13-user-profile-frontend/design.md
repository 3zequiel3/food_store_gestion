## Context

El backend expone tres endpoints de perfil desde Sprint 4: `GET /api/v1/usuarios/me`, `PATCH /api/v1/usuarios/me`, `POST /api/v1/usuarios/me/password`. La ruta `/cliente/perfil` ya existe en el router con un `PlaceholderPage`. El frontend sigue el patrón feature-first plano: cada feature tiene `types/`, `services/`, `hooks/`, `schemas/`, `components/`, `pages/`. `apiClient` con interceptors y `ENDPOINTS` como fuente de paths ya están disponibles.

La diferencia clave con el tipo `Usuario` del authStore: el endpoint de perfil devuelve `telefono` y `actualizado_en` que el login no incluye. Por eso se crea un tipo `ProfileRead` separado en la feature.

## Goals / Non-Goals

**Goals:**
- `ProfilePage` real en `/cliente/perfil` que muestra los datos del usuario autenticado.
- Formulario inline de datos personales (nombre, apellido, teléfono) con guardado optimista del authStore.
- Modal de cambio de contraseña con flujo de re-login forzado post-204.
- Seguir los patrones establecidos: TanStack Form + Zod, TanStack Query, `apiClient`, feature-first.

**Non-Goals:**
- Cambio de email (el backend lo rechaza con 422 por diseño).
- Upload de foto de perfil (fuera de scope del integrador).
- Admin editando el perfil de otro usuario (pertenece a `admin-users-frontend`).

## Decisions

### D1 — Feature folder separado: `features/user-profile/`
No se extiende `features/auth/` porque perfil y autenticación son dominios distintos. Auth maneja sesión/tokens; user-profile maneja datos del usuario. El `authStore` es el contrato de sesión; el perfil es un recurso editable.

**Alternativa descartada**: poner todo en `features/auth/`. El riesgo es acoplar el manejo de tokens con la lógica de edición de perfil — viola separación de responsabilidades.

### D2 — Tipo `ProfileRead` separado de `Usuario`
`Usuario` en `auth.types.ts` refleja lo que el backend manda en el login (`id, email, nombre, apellido, roles, created_at`). El endpoint `/usuarios/me` devuelve además `telefono` y `actualizado_en`. Se define `ProfileRead` en `features/user-profile/types/` para no contaminar `auth.types.ts` con campos de un endpoint distinto.

### D3 — Actualización del authStore tras PATCH exitoso
Cuando el usuario guarda sus datos personales, se actualiza `authStore.user` con los campos que cambiaron (`nombre`, `apellido`) para que el Sidebar/Navbar reflejen el nombre actual sin esperar re-login. Se hace con `useAuthStore.getState().setSession(...)` tomando el estado actual y mezclando los campos actualizados.

**Riesgo**: `authStore.user` no tiene `telefono`, así que solo se actualizan los campos que `Usuario` sí tiene. El teléfono actualizado se ve desde `useProfile()` que refetch tras mutación.

### D4 — Flujo de cambio de contraseña: clearSession + redirect
POST 204 → el backend revocó todos los refresh tokens. La sesión actual queda inválida (el access token dura 30 min más, pero el refresh ya no funciona). El frontend debe:
1. Llamar `useAuthStore.getState().clearSession()`.
2. Redirect a `/login`.

No se intenta usar la sesión existente ni mostrar un toast — el spec dice que el token queda inválido, así que forzar re-login es la respuesta correcta y honesta.

### D5 — Modal de contraseña con `<dialog>` nativo
Consistente con `CartDrawer` que ya usa `<dialog>` nativo. Se controla con `useState(isOpen)` y `useRef<HTMLDialogElement>`. Se cierra con `Escape` (comportamiento nativo del elemento) y con botón de cancelar.

### D6 — Mapeo de nombres de campos en el servicio
El frontend usa `password_actual` / `password_nuevo` (igual al backend) para el payload de cambio de contraseña, alineando directamente con la spec del backend. El schema Zod en la feature tendrá esos nombres (no los de `auth/schemas/passwordChangeSchema.ts` que usa `current_password`/`new_password`).

### D7 — `useProfile()` usa `/usuarios/me`, no reutiliza `useMe()`
`useMe()` en `features/auth/hooks/` llama a `/auth/me` y devuelve `Usuario`. El perfil usa `/usuarios/me` que devuelve `ProfileRead` con más campos. Son endpoints distintos con responses distintos → hooks distintos.

## Risks / Trade-offs

- **authStore.user desincronizado**: Si el PATCH falla silenciosamente después del optimistic update, el nombre en el navbar quedaría incorrecto. Mitigación: solo actualizar authStore onSuccess de la mutación, nunca antes.
- **Teléfono nullable en el form**: El backend acepta `null` para limpiar el campo, pero un input HTML vacío manda `""`. Mitigación: en el servicio, convertir `""` a `undefined` (omitir del payload, que preserva el valor existente) o a `null` si el usuario explícitamente borra el campo (distinguir con un flag o validación Zod).
- **Modal accesibilidad**: `<dialog>` nativo es accesible por defecto. Se asegura `aria-labelledby` apuntando al título del modal.
