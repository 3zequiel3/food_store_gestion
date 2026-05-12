## Why

Hoy, los pedidos creados (POST /api/v1/pedidos) y transicionados (PATCH /api/v1/pedidos/{id}/estado) no se pueden CONSULTAR. El CLIENT no puede ver su historial ni el detalle de un pedido que ya pagó; PEDIDOS/ADMIN no tienen panel de gestión. US-049, US-050, US-051 y US-052 (todas prioridad **Alta**) están bloqueadas y son requisito directo para arrancar el frontend de "Mis pedidos" y el panel de gestión.

Esta capability cubre la lectura role-aware: un solo par de endpoints (`GET /api/v1/pedidos`, `GET /api/v1/pedidos/{id}`) que cambia su comportamiento según el JWT del caller — CLIENT ve sólo lo suyo, PEDIDOS/ADMIN ven todo. La spec canónica (`docs/Descripcion.txt:285`) prevalece sobre las "Notas Técnicas" de US-051 que sugerían `/api/admin/pedidos` separado: **un solo endpoint** role-aware, alineado con la convención REST del proyecto.

## What Changes

- **NUEVO** `GET /api/v1/pedidos` — listado role-aware con filtros (`estado`, `desde`, `hasta`, `q`) y paginación (`page`, `limit`). CLIENT ve sólo `pedido.user_id == jwt.user_id`; PEDIDOS/ADMIN ven todos. STOCK sin acceso (403 explícito).
- **NUEVO** `GET /api/v1/pedidos/{id}` — detalle completo con items + historial + pagos + dirección snapshot. Anti-leak 404: si CLIENT pide un pedido que no es suyo, responde 404 (no 403).
- **NUEVOS schemas** en `backend/features/orders/schemas.py`: `PedidoListItem` (compact), `PaginatedPedidos`, `PedidoDetalle` (full), `ItemDetalle`, `HistorialItem`, `PagoSummary`. `PedidoRead` (compact actual) NO se toca — sigue usándose en POST y PATCH.
- **EXTENSIÓN** `OrderRepository`: nuevos `list_with_filter(user_id, estado, desde, hasta, q, page, limit)` y `count_with_filter(...)`. `get_pedido_completo(pedido_id, user_id)` ya existe — se extiende para aceptar `user_id=None` (admin path sin filtro de ownership) y se agrega `selectinload(pagos)` al eager loading.
- **NUEVO en service** `OrderService.listar_pedidos(user, filtros)` y `OrderService.get_pedido_detalle(user, pedido_id)` — encapsulan la lógica role-aware y el anti-leak 404.
- **Filtros validados con Pydantic**: `desde <= hasta` (model_validator), `estado` como Literal de los 6 códigos, `q` único (auto-detecta int → pedido.id, string → ILIKE sobre `usuario.nombre || ' ' || usuario.apellido`), `page>=1`, `1<=limit<=100`.
- **Performance**: la lista NO eager-loadea items/historial/pagos (evita N+1); solo el detalle hace `selectinload(items, historial, pagos)`.
- **Order by** `creado_en DESC` (requisito US-049, "más recientes primero").

## Capabilities

### New Capabilities
- `order-visualization`: lectura role-aware de pedidos (lista + detalle) con filtros, paginación y anti-leak 404.

### Modified Capabilities
<!-- Ninguna. `order-creation` y `order-state-machine` no cambian sus requirements — siguen devolviendo `PedidoRead` compact en sus endpoints (POST y PATCH). Esta capability es aditiva. -->

## Impact

**Afecta:**
- `backend/features/orders/router.py` — agrega 2 endpoints GET (mantiene los actuales POST/PATCH intactos).
- `backend/features/orders/service.py` — agrega 2 métodos públicos.
- `backend/features/orders/repository.py` — agrega 2 métodos y extiende `get_pedido_completo` para `user_id=None`.
- `backend/features/orders/schemas.py` — 6 schemas nuevos. `PedidoRead` existente NO se modifica.
- `backend/features/auth/dependencies.py` — sin cambios (ya existe `get_current_user` y `require_role`).
- `backend/tests/` — nueva suite pytest por escenarios.

**No afecta:**
- Capabilities `order-creation` y `order-state-machine` (lectura es aditiva, no toca write paths).
- Modelos SQLAlchemy (`Pedido`, `DetallePedido`, `HistorialEstadoPedido`, `Pago`) — todas las relaciones requeridas ya existen.
- Alembic migrations — no hay cambios de schema.
- Frontend — esta change es backend-only; el consumer (página "Mis pedidos") es un change posterior.

**Dependencias previas (ya archivadas):**
- `order-creation` (#14) — provee `Pedido`, `DetallePedido`, `direccion_snapshot`.
- `order-state-machine` (#16) — provee `HistorialEstadoPedido` con `motivo` y `cambiado_por_id`.
- `payment-mercadopago-backend` (#15) — provee `Pago` con `pedido_id`, `status`, `monto`.
