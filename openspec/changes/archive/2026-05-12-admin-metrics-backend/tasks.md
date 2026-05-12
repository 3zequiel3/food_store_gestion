# Tasks: admin-metrics-backend

## T1 — Crear estructura del módulo
- [x] Crear `backend/features/admin_metrics/__init__.py`

## T2 — Schemas de respuesta
- [x] Crear `backend/features/admin_metrics/schemas.py` con todos los response models (Decimal como str, D3)

## T3 — Repository con queries SQLAlchemy 2.0
- [x] Crear `backend/features/admin_metrics/repository.py` con:
  - `get_resumen_pedidos(session, desde, hasta)` → totales (SUM total, COUNT pedidos)
  - `get_total_usuarios(session)` → COUNT usuarios activos
  - `get_ventas_raw(session, desde, hasta)` → filas (creado_en, total) para agrupar en Python
  - `get_top_productos(session, desde, hasta, top)` → SUM cantidad, SUM ingreso, JOIN nombre_snapshot
  - `get_pedidos_por_estado(session, desde, hasta)` → COUNT GROUP BY estado_codigo

## T4 — Service con lógica de agrupación por periodo
- [x] Crear `backend/features/admin_metrics/service.py` con:
  - `MetricsService.get_resumen(desde, hasta)` → ResumenMetricas
  - `MetricsService.get_ventas_por_periodo(desde, hasta, granularidad)` → VentasPorPeriodoResponse
  - `MetricsService.get_top_productos(desde, hasta, top)` → TopProductosResponse
  - `MetricsService.get_pedidos_por_estado(desde, hasta)` → PedidosPorEstadoResponse
  - Agrupación por periodo en Python (D2)
  - Usa UnitOfWork para sesión (compatible con conftest monkeypatch)

## T5 — Router con 4 endpoints ADMIN
- [x] Crear `backend/features/admin_metrics/router.py` con los 4 GET endpoints, `require_role("ADMIN")`

## T6 — Registrar router en main.py
- [x] Agregar import y `app.include_router(admin_metrics_router, prefix="/api/v1/admin/metricas", tags=["admin-metrics"])` en `backend/main.py`

## T7 — Tests
- [x] Crear `backend/tests/integration/test_admin_metrics.py` con tests para los 4 endpoints:
  - resumen vacío (0 pedidos) ✓
  - resumen con datos reales ✓
  - ventas por periodo (dia/semana/mes) ✓
  - top productos (pg_only — usa order_items ARRAY) ✓ skipped en SQLite
  - pedidos por estado ✓
  - filtro fecha desde/hasta ✓
  - acceso denegado para no-ADMIN ✓
  - sin autenticación → 401 ✓
