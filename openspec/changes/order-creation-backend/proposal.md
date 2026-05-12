## Why

Sprint 5 #14 — **corazón del negocio**. Hoy el feature `orders` tiene los modelos sembrados pero el resto (schemas, repository, service, router) está vacío o stub. Sin este endpoint el cliente no puede convertir el carrito en un pedido persistente, y el resto del Sprint 5 (pago MercadoPago, FSM, visualización) no tiene de qué partir.

La operación es la más compleja del backend: múltiples INSERT (Pedido + N DetallePedido + HistorialEstadoPedido inicial) que **deben ser atómicos** (RN-PE01), con **snapshots inmutables** de precio y dirección (RN-PE02, RN-PE03, RN-DA06), **validación de stock dentro de la transacción** (RN-PE04, RN-PE05 — todo o nada) y **append-only de historial** (RN-DA05). Cualquier desviación rompe trazabilidad o consistencia.

Además, la implementación previa del modelo `Pedido` quedó desalineada con la spec canónica §3.3: hoy `direccion_entrega_id` y `direccion_snapshot` están `NOT NULL`, pero la spec exige `direccion_id BIGINT FK SET NULL — NULL = retiro en local (válido)`. Hay que cerrar esa discrepancia con una migration en el mismo change.

## What Changes

- **NEW capability `order-creation`**: capacidad nueva de dominio — crea pedidos atómicamente desde el carrito del cliente.
- Crear esquemas Pydantic v2 para órdenes (`CrearPedidoRequest`, `ItemPedidoRequest`, `PedidoRead`, `PedidoDetail`, `DetallePedidoRead`, `HistorialEstadoRead`) con `extra="forbid"` en los requests (anti-smuggling: no se acepta `total`, `estado_codigo`, `usuario_id` desde el cliente).
- Implementar `OrderRepository(BaseRepository[Pedido])` con métodos para sub-registros (productos con `SELECT FOR UPDATE`, creación de `DetallePedido`, registro de `HistorialEstadoPedido`) — un único repository unificado para la agregación raíz.
- Implementar `OrderService.crear_pedido()` siguiendo el flujo UoW de 9 pasos de la spec §7.1: lock pesimista sobre productos → validar stock + disponibilidad → calcular total con snapshots → INSERT pedido + flush → INSERT detalles × N → INSERT historial inicial (`estado_desde=None`, RN-02) → COMMIT atómico.
- Implementar `POST /api/v1/pedidos` con auth obligatoria (CLIENT vía `get_current_user`), valida body y devuelve `201 PedidoRead`.
- **BREAKING (modelo)**: migration nueva para alinear `orders.direccion_entrega_id` (`NOT NULL` → `nullable=True`, `ondelete="SET NULL"`) y `orders.direccion_snapshot` (`NOT NULL` → `nullable=True`). Habilita retiro en local sin dirección de entrega (RN-PE03 con snapshot opcional). Sin datos productivos, sin downtime.
- Decisión arquitectónica `personalizacion`: mantener `INTEGER[]` de Postgres con `pg_only` en conftest (Opción B, recomendada). Los tests de items de pedido corren contra Postgres; el resto del integration suite sigue en SQLite.
- Resolver `costo_envio` v1: fijo `50.00` para envíos con dirección, `0.00` para retiro en local. Cualquier lógica de cálculo dinámico (zona, distancia) queda fuera de scope y se documenta como deuda para una futura `shipping-pricing` capability.
- Añadir fixtures de conftest: `sample_estados_pedido` (6 estados seedeados), `sample_formas_pago` (3 métodos seedeados), `sample_producto_disponible(stock=N)` (con stock parametrizable).
- Tests de integración (TDD-first, Strict TDD activo): happy path, stock insuficiente, producto no disponible, producto inexistente, forma_pago inválida o deshabilitada, dirección de otro usuario (404, no 403 — anti-leak D6 ya establecido en `delivery-addresses-backend`), retiro en local (`direccion_id=None`), atomicidad / rollback en mitad de la operación, anti-smuggling (`total`, `estado_codigo`, `usuario_id` rechazados o ignorados), auth-only (401 sin token, 403 si no es CLIENT).

## Capabilities

### New Capabilities
- `order-creation`: capacidad de crear pedidos atómicamente desde el carrito del cliente. Incluye request validation, validación de stock con lock pesimista, snapshots inmutables (precio + dirección), creación del historial inicial en estado `PENDIENTE` y la garantía transaccional de "todo o nada".

### Modified Capabilities
<!-- Ninguna: este change introduce una capability nueva. La FSM completa, la visualización
     y el pago viven en changes posteriores del Sprint 5 (sus propias capabilities). -->

## Impact

**Código afectado**
- `backend/features/orders/models.py` — ajustar `direccion_entrega_id` y `direccion_snapshot` a `nullable=True` (alineación con spec §3.3).
- `backend/features/orders/schemas.py` — crear desde cero: `CrearPedidoRequest`, `ItemPedidoRequest`, `PedidoRead`, `PedidoDetail`, `DetallePedidoRead`, `HistorialEstadoRead`.
- `backend/features/orders/repository.py` — crear `OrderRepository` (extiende `BaseRepository[Pedido]`) con métodos: `get_producto_for_update`, `create_pedido`, `create_detalle`, `create_historial`, `get_pedido_completo`.
- `backend/features/orders/service.py` — crear `OrderService.crear_pedido(user_id, payload)` con el flujo UoW de 9 pasos.
- `backend/features/orders/router.py` — reemplazar stubs por `POST /` real con `Depends(get_current_user)` y, opcional, RBAC `CLIENT`.
- `backend/alembic/versions/2026MMDD_xxxx_orders_direccion_nullable.py` — migration nueva (ALTER `direccion_entrega_id` y `direccion_snapshot`).
- `backend/tests/conftest.py` — añadir fixtures `sample_estados_pedido`, `sample_formas_pago`, `sample_producto_disponible`.
- `backend/tests/integration/test_orders.py` — crear desde cero (no existe).

**APIs nuevas**
- `POST /api/v1/pedidos` — body `CrearPedidoRequest`, response `201 PedidoRead`, auth CLIENT obligatoria.

**Dependencias upstream (todas archivadas)**
- `delivery-addresses-backend` ✅ — provee `direcciones` para FK opcional + validación de ownership (patrón `find_by_id_and_user`, D6).
- `products-backend` ✅ — provee `Producto`, `stock_cantidad`, `disponible` y el repo con soft-delete.
- `database-schema-seed` ✅ — tablas `orders`, `order_items`, `order_state_history`, `order_states`, `payment_methods` ya creadas en la migration inicial (`20260428_0001`).
- `refactor-uow-to-context-manager` ✅ — service-driven UoW (commit en `__exit__`), patrón usado por `addresses`, `products`, `users`, `auth`.

**No afecta a**
- Frontend (sigue en Fase B).
- Pago MercadoPago — el pedido nace en `PENDIENTE` y se queda ahí hasta que `payment-mercadopago-backend` lo transicione.
- FSM de transiciones de estado — `order-state-machine-fsm` lo cubre en un change posterior. Acá sólo se inserta el historial inicial `None → PENDIENTE`.
- Visualización (`GET /api/v1/pedidos*`) — la cubre `order-visualization-backend`. Acá no se exponen listados ni detalles.

**Tradeoffs aceptados**
- `personalizacion: INTEGER[]` mantiene la spec literal (RN-PE07) pero obliga a Postgres para tests de `order_items` (ya está el `pg_only` en conftest, sólo hay que decorar los tests).
- `costo_envio` fijo (50.00) — simplificación v1. Cualquier cálculo dinámico se traslada a un change futuro.
- Sin throttling específico para `POST /pedidos` — se hereda el rate limit global. Si se identifica abuso, se sube en `admin-metrics-backend` o un change posterior.

**Estimación**: 5–6 h (sin compactación, incluye TDD-first de 12-15 tests de integración).
