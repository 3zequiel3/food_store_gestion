## 1. Tipos y API client

- [x] 1.1 Crear `features/orders/types/orders.types.ts` con `PedidoListItem`, `PaginatedPedidos`, `PedidoDetalle`, `DetallePedidoItem`, `HistorialEstado`, `PagoInfo`, `OrderFilters`
- [x] 1.2 Crear `features/orders/api/ordersApi.ts` con `listOrders(filters)`, `getOrderDetail(id)` y `advanceOrderState(id, nuevo_estado, motivo?)`

## 2. Hooks TanStack Query

- [x] 2.1 Crear `features/orders/hooks/useOrders.ts` — query `GET /api/v1/pedidos` con filtros, `staleTime: 30_000`
- [x] 2.2 Crear `features/orders/hooks/useOrderDetail.ts` — query `GET /api/v1/pedidos/{id}`, habilitada solo cuando hay id
- [x] 2.3 Crear `features/orders/hooks/useAdvanceOrderState.ts` — mutation `PATCH /api/v1/pedidos/{id}/estado` con `onSuccess` que invalida la query de lista

## 3. Componentes base

- [x] 3.1 Crear `features/orders/components/OrderStatusBadge.tsx` — badge con color-coding por estado y label en español
- [x] 3.2 Crear `features/orders/components/OrderTimeline.tsx` — lista de eventos del historial con fecha y estado
- [x] 3.3 Crear `features/orders/components/OrderDetailModal.tsx` — modal con ítems (precio_snapshot), timeline, datos de pago y dirección snapshot
- [x] 3.4 Crear `features/orders/components/OrderCardSkeleton.tsx` — skeleton para loading state

## 4. Vista CLIENT — Mis Pedidos

- [x] 4.1 Crear `features/orders/components/OrderCard.tsx` — card con id, estado badge, total, fecha y items_count; dispara apertura del modal al hacer click
- [x] 4.2 Crear `pages/client/MisPedidosPage.tsx` — lista de `OrderCard` con paginación simple, estado vacío y skeleton
- [x] 4.3 Integrar `useOrders` en `MisPedidosPage` con filtros desde `useSearchParams`

## 5. Vista PEDIDOS/ADMIN — Gestión de Pedidos

- [x] 5.1 Crear `features/orders/components/OrderFilters.tsx` — controles de filtro (select de estado, inputs de fecha, campo de búsqueda) sincronizados con URL
- [x] 5.2 Crear `features/orders/components/OrderRow.tsx` — fila de tabla con id, cliente (si está disponible), estado badge, total, fecha y botón "Ver detalle"
- [x] 5.3 Crear `features/orders/components/OrderStateActions.tsx` — botones de transición FSM (EN_PREPARACION→EN_CAMINO, EN_CAMINO→ENTREGADO, cancelar si ADMIN) con confirmación
- [x] 5.4 Crear `pages/admin/PedidosAdminPage.tsx` — tabla con `OrderRow`, panel de `OrderFilters`, paginación y `OrderDetailModal`
- [x] 5.5 Integrar `useAdvanceOrderState` en `OrderStateActions` con feedback de error inline

## 6. Router y navegación

- [x] 6.1 Reemplazar `PlaceholderPage` de `/cliente/pedidos` en `AppRoute.tsx` por `MisPedidosPage`
- [x] 6.2 Reemplazar `PlaceholderPage` de `/admin/pedidos` en `AppRoute.tsx` por `PedidosAdminPage`
- [x] 6.3 Verificar que el enlace de "Mis pedidos" en `Sidebar` / `BottomNav` apunta a `/cliente/pedidos`
