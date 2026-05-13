## Why

El backend de visualización de pedidos (#17) está completo y testeado, pero no existe UI para consumirlo. CLIENT no puede ver su historial de pedidos, y PEDIDOS/ADMIN no tienen panel para gestionar el ciclo de vida de los mismos.

## What Changes

- Nueva página `MisPedidosPage` para CLIENT en `/cliente/pedidos`: lista paginada de sus pedidos con estado y detalle.
- Nueva página `PedidosAdminPage` para PEDIDOS/ADMIN en `/admin/pedidos`: lista completa con filtros avanzados (estado, fechas, búsqueda por id/cliente) y botones de transición de estado (FSM).
- Nueva feature folder `features/orders/` con tipos, API client, hooks TanStack Query y componentes compartidos.
- `OrderDetailModal` compartido entre ambas vistas: muestra ítems del pedido, historial de estados (timeline) y datos de pago.
- `OrderStatusBadge` con color-coding por estado (PENDIENTE, CONFIRMADO, EN_PREPARACION, EN_CAMINO, ENTREGADO, CANCELADO).
- Reemplazar los dos `PlaceholderPage` en `AppRoute.tsx` por los componentes reales.

## Capabilities

### New Capabilities
- `order-visualization-frontend`: UI para que CLIENT consulte sus pedidos y PEDIDOS/ADMIN gestionen el ciclo de vida completo con transiciones de estado.

### Modified Capabilities
- (ninguna — los requisitos del backend no cambian)

## Impact

- **Nuevos archivos**: `features/orders/` (tipos, api, hooks, componentes), `pages/client/MisPedidosPage.tsx`, `pages/admin/PedidosAdminPage.tsx`
- **Modificado**: `router/AppRoute.tsx` (reemplazar PlaceholderPage en `/cliente/pedidos` y `/admin/pedidos`)
- **APIs consumidas**: `GET /api/v1/pedidos`, `GET /api/v1/pedidos/{id}`, `PATCH /api/v1/pedidos/{id}/estado`
- **Dependencias nuevas**: ninguna (TanStack Query y Axios ya están configurados)
