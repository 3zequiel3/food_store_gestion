# Proposal: admin-metrics-backend

## What

Implementar los endpoints de métricas administrativas para el panel de inteligencia del negocio. Tres endpoints READ-ONLY bajo `/api/v1/admin/metricas/`:

1. `GET /resumen` — totales generales (ventas, pedidos, ticket promedio, usuarios) con filtro de fecha
2. `GET /ventas-por-periodo` — evolución de ventas agrupada por día/semana/mes
3. `GET /top-productos` — ranking de productos más vendidos por cantidad y/o ingreso
4. `GET /pedidos-por-estado` — distribución de pedidos por estado con filtro de fecha

## Why

US-056, US-057, US-058, US-059 (Epic 17 — Panel de Métricas y Dashboard). El Admin necesita inteligencia del negocio para tomar decisiones informadas. Esta es la capa backend; la visualización con recharts va a la Fase B (frontend).

## Historias cubiertas

- **US-056**: Dashboard métricas generales — totales + filtro fecha
- **US-057**: Ventas por periodo — granularidad dia/semana/mes
- **US-058**: Top productos más vendidos — cantidad + ingreso, filtro fecha
- **US-059**: Distribución pedidos por estado — count per estado, filtro fecha

## Dependencias

- `order-creation-backend` — tablas `orders` y `order_items` deben existir con datos
- `admin-catalog-permissions` — patrón `require_role("ADMIN")` establecido

## Alcance (Sprint 6 #20)

- Nuevo módulo: `backend/features/admin_metrics/`
- Sin migraciones (solo lectura de tablas existentes)
- Solo rol ADMIN
- Tests con SQLite in-memory (no funciones PostgreSQL-específicas)
- Decimal serializado como string en JSON

## Out of scope

- Frontend / visualizaciones recharts (Fase B)
- Métricas de usuarios (US-056 lo menciona pero no hay endpoint dedicado — se incluye en resumen como campo `total_usuarios`)
- Cache de queries (futuro)
