## ADDED Requirements

### Requirement: AdminMetricasPage with shared date filter
The system SHALL provide an `AdminMetricasPage` at `/admin/metricas` with a date range filter (desde/hasta) stored in URL query params. All widgets on the page SHALL use the same date range.

#### Scenario: Page loads without date filter
- **WHEN** an ADMIN navigates to `/admin/metricas` without query params
- **THEN** all widgets SHALL fetch data without date restrictions (full historical range)

#### Scenario: Date filter applied
- **WHEN** admin sets desde and/or hasta date inputs
- **THEN** all 4 API calls SHALL include the updated date params and widgets SHALL refresh

### Requirement: KPI summary cards
The system SHALL display 4 KPI cards sourced from `GET /api/v1/admin/metricas/resumen`: total ventas (formatted as currency), total pedidos (count), ticket promedio (formatted as currency), total usuarios (count).

#### Scenario: KPI cards render with data
- **WHEN** the resumen endpoint returns data
- **THEN** each card SHALL display its value with a descriptive label

#### Scenario: KPI cards loading state
- **WHEN** the resumen request is in flight
- **THEN** each card SHALL display a skeleton placeholder

### Requirement: Ventas por periodo chart
The system SHALL display a line chart sourced from `GET /api/v1/admin/metricas/ventas-por-periodo`. The chart SHALL include a granularidad selector (dia/semana/mes) that updates the chart independently from the global date filter.

#### Scenario: Chart renders with data
- **WHEN** the endpoint returns puntos
- **THEN** the chart SHALL render a line with periodo on the X axis and total_ventas on the Y axis

#### Scenario: Empty data state
- **WHEN** the endpoint returns an empty puntos array
- **THEN** the chart SHALL display a "Sin datos para el periodo" message

### Requirement: Top productos chart
The system SHALL display a horizontal bar chart sourced from `GET /api/v1/admin/metricas/top-productos` showing the top 10 products by cantidad_total vendida.

#### Scenario: Chart renders with data
- **WHEN** the endpoint returns productos
- **THEN** the chart SHALL render horizontal bars with nombre on the Y axis and cantidad_total on the X axis

#### Scenario: Empty data state
- **WHEN** the endpoint returns an empty productos array
- **THEN** the chart SHALL display a "Sin ventas en el periodo" message

### Requirement: Pedidos por estado chart
The system SHALL display a pie chart sourced from `GET /api/v1/admin/metricas/pedidos-por-estado` showing the distribution of orders across states.

#### Scenario: Chart renders with data
- **WHEN** the endpoint returns distribucion
- **THEN** the chart SHALL render a pie with each slice representing an estado_codigo and its cantidad

#### Scenario: Empty data state
- **WHEN** all states have cantidad 0
- **THEN** the chart SHALL display a "Sin pedidos en el periodo" message

### Requirement: Admin metrics feature folder
The system SHALL have a `features/admin-metrics/` folder containing:
- `types/admin-metrics.types.ts` — mirrors all backend response schemas
- `services/admin-metrics.service.ts` — wraps all 4 endpoints
- `hooks/useResumen.ts`, `useVentasPorPeriodo.ts`, `useTopProductos.ts`, `usePedidosPorEstado.ts`

#### Scenario: Each hook uses independent query key
- **WHEN** the date filter changes
- **THEN** each hook SHALL independently refetch its own data
