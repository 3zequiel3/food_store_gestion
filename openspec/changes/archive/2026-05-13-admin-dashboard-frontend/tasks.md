## 1. Dependencia — instalar recharts

- [x] 1.1 Instalar recharts: `pnpm --filter frontend add recharts` desde la raíz del repo

## 2. Feature folder — tipos, service y hooks

- [x] 2.1 Crear `frontend/src/features/admin-metrics/types/admin-metrics.types.ts` con todos los tipos del backend (ResumenMetricas, VentasPorPeriodoResponse, TopProductosResponse, PedidosPorEstadoResponse y sus sub-tipos)
- [x] 2.2 Crear `frontend/src/features/admin-metrics/services/admin-metrics.service.ts` con `getResumen`, `getVentasPorPeriodo`, `getTopProductos`, `getPedidosPorEstado`
- [x] 2.3 Crear `frontend/src/features/admin-metrics/hooks/useResumen.ts` — query con `{ desde?, hasta? }`
- [x] 2.4 Crear `frontend/src/features/admin-metrics/hooks/useVentasPorPeriodo.ts` — query con `{ desde?, hasta?, granularidad }`
- [x] 2.5 Crear `frontend/src/features/admin-metrics/hooks/useTopProductos.ts` — query con `{ desde?, hasta?, top? }`
- [x] 2.6 Crear `frontend/src/features/admin-metrics/hooks/usePedidosPorEstado.ts` — query con `{ desde?, hasta? }`

## 3. Componentes

- [x] 3.1 Crear `frontend/src/features/admin-metrics/components/KPICard.tsx` — card con label, valor formateado y skeleton de carga
- [x] 3.2 Crear `frontend/src/features/admin-metrics/components/DateRangeFilter.tsx` — inputs de fecha desde/hasta que actualizan URL params
- [x] 3.3 Crear `frontend/src/features/admin-metrics/components/VentasChart.tsx` — LineChart de recharts + selector granularidad (dia/semana/mes), ResponsiveContainer, empty state
- [x] 3.4 Crear `frontend/src/features/admin-metrics/components/TopProductosChart.tsx` — BarChart horizontal de recharts, top 10, empty state
- [x] 3.5 Crear `frontend/src/features/admin-metrics/components/PedidosPorEstadoChart.tsx` — PieChart de recharts con labels, empty state

## 4. Página y ruta

- [x] 4.1 Crear `frontend/src/pages/admin/AdminMetricasPage.tsx` — lee desde/hasta de URL params, renderiza DateRangeFilter + 4 KPICards + 3 charts en grid
- [x] 4.2 Reemplazar `PlaceholderPage` de `/admin/metricas` → `AdminMetricasPage` en `AppRoute.tsx`
