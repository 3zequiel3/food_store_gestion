## Context

El backend devuelve todos los valores monetarios (`total_ventas`, `ticket_promedio`, `ingreso_total`) como strings (Decimal serializado). recharts necesita números para graficar — hay que hacer `parseFloat()` antes de pasarlos a los componentes. Los 4 endpoints aceptan `desde` y `hasta` como query params de tipo `date` (formato `YYYY-MM-DD`).

La ruta `/admin/metricas` tiene un `PlaceholderPage`. El `AdminLayout` ya existe y provee la navegación lateral.

## Goals / Non-Goals

**Goals:**
- 4 KPI cards: total ventas, total pedidos, ticket promedio, total usuarios.
- Gráfico de línea/barra para evolución de ventas por periodo con selector de granularidad.
- Gráfico de barras horizontal para top productos.
- Gráfico de torta para distribución de pedidos por estado.
- Filtro de fechas compartido (desde/hasta) que aplica a todos los widgets.

**Non-Goals:**
- Exportar datos a CSV.
- Comparación entre periodos.
- Drill-down en productos o estados.

## Decisions

### D1 — recharts como librería de charts

Definido en el roadmap (`docs/CHANGES.md`). No se evalúan alternativas — es el stack elegido para el proyecto.

### D2 — Filtro de fechas compartido en URL params

`desde` y `hasta` se almacenan en la URL (`?desde=2026-01-01&hasta=2026-05-13`). Consistente con los filtros de `/admin/pedidos` y `/admin/usuarios`. Permite compartir la URL del dashboard con un periodo preseleccionado.

### D3 — Granularidad colocalizada con el gráfico de ventas

El parámetro `granularidad` (dia/semana/mes) solo aplica al endpoint `/ventas-por-periodo`. Lo gestiona el componente `VentasChart` internamente con estado local — no va a la URL para no contaminar el namespace de query params del filtro global.

### D4 — Una query TanStack por widget, independientes

Cada componente hace su propio `useQuery`. Si una llamada falla, los otros widgets siguen mostrando datos. Evita un único punto de fallo y permite loading states independientes.

### D5 — Valores monetarios: `parseFloat` antes de recharts

El backend serializa `Decimal` como string. recharts no grafica strings numéricos. Conversión: `parseFloat(punto.total_ventas)` al armar los datos del chart. No hace falta `Number()` ni `toFixed()` para graficar, solo para mostrar en tooltips/labels.

### D6 — `ResponsiveContainer` envuelve todos los charts

Los charts de recharts necesitan width/height fijos o un contenedor que los provea. `ResponsiveContainer width="100%" height={300}` es el patrón estándar para layouts responsivos.

## Risks / Trade-offs

- **[Riesgo] Sin datos en el periodo seleccionado** → recharts renderiza un chart vacío sin errores, pero puede ser confuso. Mitigación: mostrar un mensaje "Sin datos para el periodo" cuando el array de puntos está vacío.
- **[Riesgo] recharts no tiene tipos perfectos con TypeScript estricto** → Usar `as const` en los accessors y tipear los `data` arrays explícitamente.
- **[Trade-off] Granularidad local vs global** → Si el usuario quisiera ver ventas por semana y top productos también por semana, necesitaría configurar por separado. Aceptable para este sprint.
