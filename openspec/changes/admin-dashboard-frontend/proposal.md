## Why

La ruta `/admin/metricas` tiene un `PlaceholderPage`. El backend tiene 4 endpoints completamente implementados: resumen general (`GET /admin/metricas/resumen`), evolución de ventas por periodo (`GET /admin/metricas/ventas-por-periodo`), top productos más vendidos (`GET /admin/metricas/top-productos`), y distribución de pedidos por estado (`GET /admin/metricas/pedidos-por-estado`). Este es el último change del roadmap.

## What Changes

- Instalar `recharts` (no está en `package.json`).
- Feature folder `features/admin-metrics/` con tipos, service y 4 hooks.
- Componentes: `KPICard`, `DateRangeFilter`, `VentasChart`, `TopProductosChart`, `PedidosPorEstadoChart`.
- Página `AdminMetricasPage` en `/admin/metricas`: filtro de fechas compartido, 4 KPI cards, y 3 gráficos recharts.
- `AppRoute.tsx` reemplaza `PlaceholderPage` de `/admin/metricas` → `AdminMetricasPage`.

## Capabilities

### New Capabilities
- `admin-dashboard-frontend`: Dashboard de métricas operativas para el panel de administración.

### Modified Capabilities
- (ninguna — los endpoints del backend no cambian)

## Impact

- **Nuevos archivos**: `features/admin-metrics/types/`, `features/admin-metrics/services/`, `features/admin-metrics/hooks/`, `features/admin-metrics/components/`, `pages/admin/AdminMetricasPage.tsx`
- **Modificados**: `package.json` (recharts), `pnpm-lock.yaml`, `router/AppRoute.tsx`
- **APIs consumidas**: `GET /api/v1/admin/metricas/resumen`, `/ventas-por-periodo`, `/top-productos`, `/pedidos-por-estado`
- **Rol requerido**: Solo ADMIN
