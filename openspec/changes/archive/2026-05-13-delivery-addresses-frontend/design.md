## Context

El backend expone cinco endpoints bajo `/api/v1/direcciones`. `ENDPOINTS.direcciones` ya está configurado en `lib/constants/endpoints.ts`. La ruta `/cliente/direcciones` existe con `PlaceholderPage`. El patrón de módulo feature-first plano está establecido por `user-profile-frontend` (#22).

`DireccionRead` tiene: `id, usuario_id, calle, numero, piso_depto|null, ciudad, codigo_postal, referencia|null, es_principal`. El endpoint `PUT /{id}` aplica PATCH semantics (solo los campos incluidos en el body se actualizan). El `DELETE` devuelve 204. El `PATCH /{id}/predeterminada` devuelve 200 con la dirección actualizada.

## Goals / Non-Goals

**Goals:**
- `AddressesPage` real en `/cliente/direcciones` con listado + CRUD completo.
- Modal único reutilizable para alta y edición (modo controlado por prop `address?: DireccionRead`).
- Confirmación de eliminación inline en la tarjeta (no dialog separado).
- Invalidación de queries tras cada mutación para mantener la lista sincronizada.

**Non-Goals:**
- Selector de dirección para el checkout (pertenece a `order-creation-frontend-checkout` #26).
- Admin viendo direcciones de otro usuario.
- Paginación (el backend no la implementa para direcciones propias).

## Decisions

### D1 — Modal único para alta y edición (`AddressModal`)
Un solo `<dialog>` nativo recibe `address?: DireccionRead`. Si `address` es undefined → modo alta (POST). Si tiene valor → modo edición (PUT), pre-carga los campos. Esto evita duplicar la lógica del formulario.

**Alternativa descartada**: dos componentes separados `CreateModal` y `EditModal`. Duplica 6 campos + validación + submit handling.

### D2 — Confirmación de eliminación inline
Cada `AddressCard` tiene un estado local `confirming: boolean`. Al hacer click en "Eliminar" → muestra un mini-confirm inline ("¿Eliminar? Sí / Cancelar") sin abrir un dialog modal. Es más liviano y consistente con el patrón de `CartDrawer`.

**Alternativa descartada**: dialog de confirmación separado. Más overhead para una acción destructiva de bajo riesgo (soft-delete reversible en el backend).

### D3 — Querykey `['addresses']` con invalidación total post-mutación
Todas las mutaciones (create, update, delete, setPrincipal) invalidan `['addresses']` en onSuccess. Simple y correcto. El listado tiene < 10 elementos típicamente, refetch instantáneo.

### D4 — Schema Zod para el formulario: campos requeridos + opcionales
`calle`, `numero`, `ciudad`, `codigo_postal` → `z.string().min(1).max(255)` (trim + no-vacío). `piso_depto` y `referencia` → `z.string().max(50/255).optional()`, cadena vacía transformada a `undefined` (omitido del payload → preservado en backend). El PUT payload solo incluye los campos que cambiaron respecto a los defaultValues — esto se maneja enviando todos los campos del form (el backend aplica patch semantics de todas formas).

### D5 — `es_principal` en la tarjeta
La tarjeta muestra un badge "Predeterminada" si `es_principal === true`. El botón "Establecer como predeterminada" solo aparece si `!es_principal`. La mutación `useSetPrincipal` llama `PATCH /{id}/predeterminada` e invalida `['addresses']`.

## Risks / Trade-offs

- **Carrera entre mutaciones**: si el usuario hace click rápido en "Establecer predeterminada" y luego edita, puede haber dos requests en vuelo. Mitigación: deshabilitar botones durante isPending de cualquier mutación activa.
- **DELETE 204 sin body**: axios resuelve sin `response.data`. El servicio retorna `void`, el hook invalida la query onSuccess.
