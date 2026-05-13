## Context

El backend expone `GET /api/v1/pedidos` (lista role-aware con filtros/paginación) y `GET /api/v1/pedidos/{id}` (detalle completo con ítems, historial y pagos). La FSM de transiciones está en `PATCH /api/v1/pedidos/{id}/estado`. Los roles CLIENT, PEDIDOS y ADMIN tienen comportamientos distintos en estos endpoints. El frontend actual tiene `PlaceholderPage` en `/cliente/pedidos` y `/admin/pedidos`.

El patrón establecido en el proyecto es: feature folder en `features/`, hooks TanStack Query, URL-first para filtros (`useSearchParams`), Tailwind + tokens del design system dark-first.

## Goals / Non-Goals

**Goals:**
- UI funcional para que CLIENT consulte su historial de pedidos
- Panel para que PEDIDOS/ADMIN listen, filtren y avancen el estado de pedidos
- Modal de detalle compartido con ítems, timeline de estados y datos de pago
- Integración con la FSM vía PATCH endpoint para PEDIDOS/ADMIN

**Non-Goals:**
- Flujo de creación de pedido (es change #26)
- Flujo de pago con MercadoPago (es change #27)
- Funcionalidad de cancelación por el CLIENT (requiere flujo de pago completo)
- Soporte para rol STOCK (el backend devuelve 403, la UI muestra RoleGuard)

## Decisions

### D1 — Feature folder compartida `features/orders/`
Una sola feature folder con tipos, API client, hooks y componentes base. Las páginas (`MisPedidosPage`, `PedidosAdminPage`) viven en `pages/` y consumen la feature. Evita duplicación de lógica de fetching y tipado.

### D2 — Dos páginas separadas, no una con branching por rol
`MisPedidosPage` (CLIENT) y `PedidosAdminPage` (PEDIDOS/ADMIN) son componentes distintos. Alternativa descartada: una sola página con `if (isAdmin)`. La separación es más limpia, cada vista tiene UX diferente (cards móviles vs tabla con filtros avanzados) y el guard de rol ya vive en el router.

### D3 — URL-first para filtros (mismo patrón que CatalogPage)
Los filtros se leen de `useSearchParams`, no de estado local. Permite compartir links, funciona con el botón atrás del browser. El hook `useOrders` recibe los filtros parseados como parámetro.

### D4 — `OrderDetailModal` compartido
El detalle completo (ítems con precio_snapshot, timeline, pago) se muestra en un modal superpuesto a la lista. Alternativa descartada: página de detalle separada (`/pedidos/:id`). El modal es más fluido para ambas vistas y no requiere nueva ruta.

### D5 — Transiciones de estado solo en vista admin
Los botones FSM (avanzar estado) solo aparecen en `PedidosAdminPage` para PEDIDOS/ADMIN. En la vista CLIENT no hay acción de avance (solo lectura). Las transiciones válidas se calculan en el frontend según la FSM documentada para no depender de un endpoint de "siguiente estado".

### D6 — `OrderStatusBadge` con colores semánticos
Un componente con color-coding fijo por estado:
- `PENDIENTE` → amarillo
- `CONFIRMADO` → azul
- `EN_PREPARACION` → naranja
- `EN_CAMINO` → indigo
- `ENTREGADO` → verde
- `CANCELADO` → rojo/gris

## Risks / Trade-offs

- **FSM hardcodeada en frontend**: Si el backend cambia las transiciones válidas, el frontend queda desincronizado. Mitigación: documentar la FSM en el spec y cubrir con tests de integración en el backend (ya cubiertos en #16).
- **Modal vs página**: el modal de detalle no tiene URL propia, no se puede compartir/linkar un pedido específico. Aceptado para este sprint — si se necesita en el futuro, se agrega ruta `/pedidos/:id`.
- **Polling de estado**: los pedidos no se actualizan en tiempo real. TanStack Query con `staleTime` bajo (30s) da una experiencia aceptable sin websockets.
