# Proposal — order-state-machine-fsm

## Why

El backend ya transiciona pedidos PENDIENTE→CONFIRMADO vía webhook de MercadoPago (change #15 `payment-mercadopago-backend`, archivado 2026-05-12). El método `OrderService.transicionar_estado()` existe en `backend/features/orders/service.py:167-208` y es invocado desde `PaymentService.procesar_webhook()` cuando llega un pago `approved`.

Sin embargo, esa transición es **minimalista**: solo cambia `estado_codigo` y crea historial. Quedan abiertos los gaps que cubre el resto de la FSM (US-039 a US-044, RN-FS01 a RN-FS09):

1. **No hay decremento de stock** en PENDIENTE→CONFIRMADO (RN-FS03). Hoy el webhook confirma el pedido sin tocar el inventario.
2. **No hay restauración de stock** al cancelar pedidos CONFIRMADO o EN_PREPARACION (RN-FS05).
3. **No hay validación FSM**: cualquier transición pasa si el estado anterior coincide — un bug puede llevar PENDIENTE→ENTREGADO directamente (viola RN-FS01).
4. **No hay RBAC por transición**: la matriz "PENDIENTE→CANCELADO permite CLIENT/PEDIDOS/ADMIN" pero "EN_PREPARACION→CANCELADO solo ADMIN" (RN-RB08, RN-FS08) no está implementada.
5. **No hay endpoint manual**: las US-040 a US-044 requieren `PATCH /api/v1/pedidos/{id}/estado` para gestores y clientes (cancelar el propio pedido).
6. **Falta `motivo`**: RN-FS09 obliga registrar observación en cada transición; el modelo `HistorialEstadoPedido` no tiene la columna.
7. **`find_by_id()` sin lock**: la transición desde webhook no usa `SELECT FOR UPDATE`, lo que abre una race condition si dos workers procesan el mismo webhook.

Cerrar estos gaps NO requiere reescribir nada — requiere **extender** la API que #15 ya estableció.

## What Changes

### Capa de bajo nivel (extender lo existente)

- **EXTENDED** `OrderService.transicionar_estado()` agrega kwarg opcional `motivo: Optional[str] = None`. Su firma actual `(pedido_id, estado_anterior, estado_nuevo, actor_id=None)` queda 100 % backwards-compatible — el webhook de #15 sigue llamándolo igual.
- **EXTENDED** `transicionar_estado()` aplica side-effects de stock condicionales:
  - `PENDIENTE → CONFIRMADO`: decrementa stock atómicamente sobre cada `DetallePedido.producto_id` con `SELECT FOR UPDATE` (RN-FS03, RN-FS04).
  - `CONFIRMADO → CANCELADO` o `EN_PREPARACION → CANCELADO`: restaura stock con el mismo lock (RN-FS05).
  - Cualquier otra transición: solo cambia estado + historial.
- **EXTENDED** `transicionar_estado()` reemplaza `find_by_id()` por `get_pedido_for_update()` con `SELECT FOR UPDATE` (cierra race condition; mejora también el webhook).
- **EXTENDED** `OrderRepository.create_historial_transicion()` acepta `motivo: Optional[str] = None` y lo persiste en la nueva columna.
- **ADDED** `OrderRepository.get_pedido_for_update(pedido_id)` — fetch del pedido con lock pesimista (necesario para idempotencia y races).
- **ADDED** `OrderRepository.decrement_stock_for_items(items)` y `restore_stock_for_items(items)` — operaciones de inventario internas a la UoW.

### Capa de alto nivel (nueva)

- **ADDED** Módulo `backend/features/orders/state_machine.py` con dos constantes (`ALLOWED_TRANSITIONS`, `TRANSITION_ROLES`) y función pura `validate_transition(desde, hacia, user_roles)`. Sin BD, totalmente testeable como unit test.
- **ADDED** `OrderService.avanzar_estado(user_id, pedido_id, nuevo_estado, motivo)` — wrapper de alto nivel para transiciones manuales. Lee estado actual, valida FSM, valida permisos por rol, valida ownership CLIENT, valida `motivo` obligatorio para cancelaciones desde estados con stock decrementado, y **delega a `transicionar_estado()`** para hacer el trabajo real.
- **ADDED** `avanzar_estado()` **rechaza explícitamente** `nuevo_estado=CONFIRMADO` con `BusinessRuleError("CONFIRMADO solo se setea automáticamente vía webhook de pago")` — defensa de RN-FS02. Doble defensa: Pydantic `Literal` sin CONFIRMADO + check en service.
- **ADDED** Schema `AvanzarEstadoRequest` con `nuevo_estado: Literal["CANCELADO", "EN_PREPARACION", "EN_CAMINO", "ENTREGADO"]` (CONFIRMADO no es opción de cliente) + `motivo: Optional[str]` (máx. 500 char).
- **ADDED** Endpoint `PATCH /api/v1/pedidos/{id}/estado` con `Depends(get_current_user)` — el rol se verifica dentro del service según la transición pedida (RBAC dinámico).

### Migración

- **MIGRATION** Alembic: agrega columna `motivo VARCHAR(500) NULL` a tabla `order_state_history` (nullable para no romper filas existentes — RN-FS09 lo pide opcional desde PENDIENTE).

## Capabilities

### New Capabilities

- `order-state-machine`: FSM completa de pedidos. Define transiciones válidas (RN-FS01), matriz RBAC por transición (RN-FS08, RN-RB08), confirmación exclusivamente automática (RN-FS02), efectos de stock en CONFIRMADO/cancelación (RN-FS03, RN-FS04, RN-FS05), estados terminales ENTREGADO/CANCELADO (RN-FS06), append-only historial con motivo (RN-FS07, RN-FS09), endpoint manual `PATCH /api/v1/pedidos/{id}/estado`, compatibilidad con webhook de pago.

### Modified Capabilities

Ninguna. La capability `order-creation` queda intacta (`crear_pedido` no se toca). La capability `payment-mercadopago` queda intacta — su consumo de `transicionar_estado()` sigue siendo válido porque la firma es backwards-compatible.

## Impact

### Código nuevo

- `backend/features/orders/state_machine.py` (módulo nuevo, ~60 LOC).
- `backend/features/orders/service.py`: nueva función `avanzar_estado()`, extensión de `transicionar_estado()`.
- `backend/features/orders/repository.py`: nuevas funciones `get_pedido_for_update()`, `decrement_stock_for_items()`, `restore_stock_for_items()`, extensión de `create_historial_transicion()`.
- `backend/features/orders/schemas.py`: nuevo schema `AvanzarEstadoRequest`.
- `backend/features/orders/router.py`: nuevo endpoint `PATCH /{pedido_id}/estado`.
- `alembic/versions/<rev>_add_motivo_to_historial.py` (migration nueva).
- `backend/features/orders/models.py`: agregar campo `motivo` a `HistorialEstadoPedido`.

### Tests

- Unit tests puros: `state_machine.py` (ALLOWED_TRANSITIONS, TRANSITION_ROLES, validate_transition).
- Unit tests Pydantic: `AvanzarEstadoRequest` rechaza `CONFIRMADO`.
- Integration tests `avanzar_estado()`: FSM válida, FSM inválida (409), permisos rol (403), ownership CLIENT, motivo obligatorio (422), rechazar CONFIRMADO manual (422).
- Integration tests `transicionar_estado()` extendido: decremento de stock en CONFIRMADO, restauración en CANCELADO, lock funciona.
- **Test de regresión**: `PaymentService.procesar_webhook()` sigue funcionando idéntico tras la extensión.
- Integration tests del endpoint: 200/403/404/409/422 según ruta.

Total estimado: ~65-70 tests nuevos distribuidos en:
- ~11 unit tests puros (`state_machine.py`: ALLOWED_TRANSITIONS, TRANSITION_ROLES, validate_transition)
- ~4 unit tests Pydantic (`AvanzarEstadoRequest`)
- ~11 integration tests del repository (get_pedido_for_update, decrement/restore stock, create_historial_transicion con motivo)
- ~11 integration tests de `transicionar_estado()` extendido (decremento stock, restauración, rollback, idempotencia, regresión webhook)
- ~18 integration tests de `avanzar_estado()` (FSM, RBAC, ownership, motivo condicional, rechazo CONFIRMADO, delegación)
- ~10 integration tests del endpoint PATCH (auth, 200/403/404/409/422, doble click, Pydantic Literal)
- ~4 tests e2e (flow completo PENDIENTE→ENTREGADO, cancelación admin desde EN_PREPARACION, cancelación cliente desde PENDIENTE)

### APIs externas

- **Nueva ruta pública**: `PATCH /api/v1/pedidos/{pedido_id}/estado`.
- **Sin cambios** en `POST /api/v1/pedidos` (#14) ni en webhook de MP (#15).

### Dependencias

- Bloqueante: `payment-mercadopago-backend` (#15) — ya archivado.
- Habilita: `order-visualization-backend` (#17), `admin-catalog-permissions`, frontend de gestión de pedidos.

### Estimación

- Implementación + tests: 5–7 horas.
- Verificación + ajustes: 1 hora.
- Migration up/down + smoke test en BD dev: 30 min.
