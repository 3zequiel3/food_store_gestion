## MODIFIED Requirements

### Requirement: PENDIENTE → CONFIRMADO es exclusivamente automática

El sistema SHALL impedir que un usuario humano (cualquier rol) ejecute la transición `PENDIENTE → CONFIRMADO` a través del endpoint manual. Esta transición es exclusiva del proceso automático del webhook de MercadoPago. **Sin embargo**, en el nuevo flow de `checkout-pay-first-flow`, el camino habitual de creación de un pedido online ya lo deja directamente en `PENDIENTE` (no en estado intermedio), y la transición `PENDIENTE → CONFIRMADO` la dispara el local cuando acepta el pedido (rol PEDIDOS o ADMIN). El webhook MP retiene este comportamiento como red de seguridad para casos excepcionales (reconciliación post-cobro fallido) — sigue siendo exclusivo del sistema, no humano. (RN-FS02 actualizada para reflejar la nueva semántica de PENDIENTE descripta abajo)

**Nueva semántica de `PENDIENTE`** (D4 de `checkout-pay-first-flow`): "pedido recién creado, esperando que el local (rol PEDIDOS o ADMIN) lo acepte". Reemplaza la semántica anterior "esperando pago" — que dejó de tener sentido porque en el flow nuevo todo pedido que existe en la DB está pagado (online) o no requiere prepago (pickup+efectivo).

Defensa en doble capa (se conserva):
1. El schema `AvanzarEstadoRequest` MUST tipar `nuevo_estado` como `Literal["CANCELADO", "EN_PREPARACION", "TERMINADO", "ENTREGADO"]` — `CONFIRMADO` no es un valor aceptado.
2. Aunque el schema sea bypassed, `OrderService.avanzar_estado()` MUST rechazar `nuevo_estado="CONFIRMADO"` con `BusinessRuleError("CONFIRMADO solo se setea automáticamente vía webhook de pago o por aceptación del local mediante endpoint dedicado")`.

**Nota sobre transición manual local PEDIDOS/ADMIN → CONFIRMADO**: el endpoint `PATCH /api/v1/pedidos/{id}/estado` que el local usa para aceptar el pedido la transición es `PENDIENTE → CONFIRMADO` y SI debe ser permitida para roles PEDIDOS/ADMIN. La defensa anterior bloqueaba esta transición porque el flow viejo asumía que solo el webhook la disparaba. Esta spec actualiza el bloqueo: `CONFIRMADO` sigue bloqueado en el schema `AvanzarEstadoRequest` para CLIENTes, pero PEDIDOS/ADMIN tienen un endpoint dedicado o un permiso especial que lo habilita. (La implementación exacta de "aceptación por el local" es responsabilidad de un change futuro `order-acceptance-by-local`, que reutiliza esta capability — fuera del alcance del change actual `checkout-pay-first-flow`.)

#### Scenario: Pydantic rechaza CONFIRMADO en el endpoint para CLIENT
- **WHEN** un CLIENT envía `PATCH /api/v1/pedidos/{id}/estado` con body `{"nuevo_estado": "CONFIRMADO"}`
- **THEN** FastAPI responde 422 antes de invocar el service (validación Pydantic falla)

#### Scenario: Webhook MP sigue invocando la transición desde el sistema
- **GIVEN** un pedido en `PENDIENTE` y un webhook MP que reporta `payment.status="approved"` (red de seguridad post-cobro fallido)
- **WHEN** `PaymentService.procesar_webhook()` invoca `transicionar_estado(pedido_id, "PENDIENTE", "CONFIRMADO", actor_id=None)`
- **THEN** la transición se ejecuta sin levantar el bloqueo de "CONFIRMADO no permitido" — el bloqueo solo aplica a endpoints humanos

#### Scenario: Service rechaza CONFIRMADO si Pydantic se bypasea desde un CLIENT
- **WHEN** el código interno invoca `avanzar_estado(user_id=<CLIENT>, pedido_id=1, nuevo_estado="CONFIRMADO", motivo=None)` directamente
- **THEN** se levanta `BusinessRuleError` con detalle apropiado

---

### Requirement: Append-only historial con motivo persistido (semántica actualizada)

El sistema SHALL persistir cada transición exitosa en `order_state_history` con: `estado_anterior_codigo`, `estado_nuevo_codigo`, `cambiado_por_id` (NULL = SISTEMA), `motivo` (NULL si no se proveyó), `creado_en` (timestamp). La tabla `order_state_history` hereda de `AppendOnlyBaseModel` — solo INSERT, nunca UPDATE ni DELETE a nivel ORM (RN-FS07, RN-03, RN-PA02). La columna `motivo` MUST ser `VARCHAR(500) NULL`.

**Nuevo en `checkout-pay-first-flow`**: cuando un pedido se crea vía `POST /api/v1/checkout/online` o `POST /api/v1/checkout/pickup-efectivo`, la primera fila de historial registra la transición `NULL → PENDIENTE` con `cambiado_por_id=<user_id del CLIENT>`. La semántica de esa fila ya NO es "pedido esperando pago" sino "pedido creado, esperando que el local lo acepte" (D4).

#### Scenario: Pedido recién creado vía checkout online tiene historial inicial PENDIENTE
- **WHEN** un cliente completa `POST /checkout/online` con MP aprobando el pago
- **THEN** existe una fila en `order_state_history` con `estado_anterior_codigo=NULL`, `estado_nuevo_codigo="PENDIENTE"`, `cambiado_por_id=<user_id>`, `motivo=NULL`

#### Scenario: Pedido recién creado vía pickup+efectivo tiene historial inicial PENDIENTE
- **WHEN** un cliente completa `POST /checkout/pickup-efectivo`
- **THEN** existe una fila en `order_state_history` con `estado_anterior_codigo=NULL`, `estado_nuevo_codigo="PENDIENTE"`, `cambiado_por_id=<user_id>`, `motivo=NULL`

#### Scenario: Historial registra SISTEMA cuando es webhook (sin cambios)
- **WHEN** el webhook confirma un pedido como red de seguridad
- **THEN** la fila de historial tiene `cambiado_por_id=NULL` (SISTEMA)

#### Scenario: Historial incluye motivo en cancelación (sin cambios)
- **WHEN** un PEDIDOS cancela un pedido `CONFIRMADO` con `motivo="Cliente pidió rembolso"`
- **THEN** existe una fila con `estado_anterior_codigo="CONFIRMADO"`, `estado_nuevo_codigo="CANCELADO"` (o variante), `cambiado_por_id=<id del gestor>`, `motivo="Cliente pidió rembolso"`

---

### Requirement: Compatibilidad backwards con webhook de payment-mercadopago-backend (semántica reducida)

El sistema SHALL mantener la firma actual de `OrderService.transicionar_estado(pedido_id, estado_anterior, estado_nuevo, actor_id=None)` invocable sin cambios desde `PaymentService.procesar_webhook()`. Cualquier parámetro nuevo (ej. `motivo`) MUST ser opcional con default.

**Reducción de alcance**: en el flow nuevo (`checkout-pay-first-flow`), el webhook MP ya no es el camino principal de transición `PENDIENTE → CONFIRMADO` — se ejecuta solo como red de seguridad para casos donde la persistencia post-cobro falló en el endpoint principal. Esto significa que la mayoría de los pedidos `PENDIENTE` ya tienen un `Pago.mp_status="approved"` asociado cuando llega el webhook, y la transición `PENDIENTE → CONFIRMADO` se dispara desde el local (PEDIDOS/ADMIN) al aceptar el pedido, NO automáticamente desde el webhook.

**Casos en los que el webhook sigue siendo invocado**:
1. Reconciliación post-cobro fallido (atómica): MP aprobó, la UoW del checkout falló al persistir. Cuando el webhook llega, ve que no hay Pago con ese `external_reference` y crea retroactivamente Pedido+Pago. (Implementación: futura — fuera del alcance estricto de este change.)
2. Pagos retrasados que finalmente aprueban (MP los reporta minutos/horas después).
3. Notificaciones idempotentes (MP las repite por seguridad).

#### Scenario: Webhook sigue invocando con la firma original
- **GIVEN** el código de `PaymentService.procesar_webhook()` que llama `service.transicionar_estado(pedido_id, "PENDIENTE", "CONFIRMADO", actor_id=None)`
- **WHEN** se ejecuta el flow con un webhook real
- **THEN** la transición funciona (cuando aplica), el stock se decrementa, el historial se crea con `cambiado_por_id=NULL` y `motivo=NULL`

#### Scenario: Tests de regresión del webhook siguen verdes
- **WHEN** se corre la suite completa de tests de `backend/features/payments/` heredada de `payment-mercadopago-backend` y `payments-checkout-api`
- **THEN** todos los tests pasan sin modificación funcional (algunos pueden necesitar ajustes menores por el cambio de `external_reference` de `str(pedido_id)` a `idempotency_key`)


---

### Requirement: Rename del código `EN_CAMINO` a `TERMINADO` (vocabulario unificado retiro/envío)

El sistema SHALL renombrar el código de estado `EN_CAMINO` a `TERMINADO` en toda la base de código y los datos persistidos. El nodo del FSM mantiene sus mismas transiciones entrantes y salientes:

- Entrante: `EN_PREPARACION → TERMINADO` (rol PEDIDOS, ADMIN).
- Saliente: `TERMINADO → ENTREGADO` (rol PEDIDOS, ADMIN).

La matriz `ALLOWED_TRANSITIONS` y `TRANSITION_ROLES` mantiene su forma — solo cambia la clave. El alcance del rename incluye:

1. **Backend código**: `backend/features/orders/state_machine.py`, `backend/features/orders/schemas.py`, `backend/scripts/seed.py`, `backend/tests/conftest.py`, `backend/tests/integration/test_*.py`, `backend/README.md`.
2. **Backend datos**: migración Alembic con UPDATEs idempotentes en `estados_pedido.codigo`, `orders.estado_codigo`, `order_state_history.estado_anterior_codigo` y `order_state_history.estado_nuevo_codigo`. La migración MUST tener `downgrade()` reverso (TERMINADO → EN_CAMINO).
3. **Frontend**: `frontend/src/features/orders/types/orders.types.ts` (tipo `EstadoCodigo`), `OrderFilters.tsx`, `OrderTimeline.tsx`, `OrderStatusBadge.tsx`, `OrderStateActions.tsx`, `frontend/src/features/admin-metrics/components/PedidosPorEstadoChart.tsx`.

**Justificación**: el usuario pidió un flujo de estados consistente independientemente del tipo de entrega. `EN_CAMINO` solo tiene sentido en delivery — en pickup el pedido no "va en camino". `TERMINADO` ("pedido listo para ser retirado o entregado") cumple esa semántica unificada. Documentado en D13 del design.

#### Scenario: Migración Alembic renombra filas existentes
- **GIVEN** una DB con `estados_pedido` que contiene una fila con `codigo = "EN_CAMINO"`
- **WHEN** se ejecuta `alembic upgrade head` con la migración del rename
- **THEN** la fila tiene `codigo = "TERMINADO"` y la tabla NO contiene `"EN_CAMINO"`

#### Scenario: Pedidos existentes en EN_CAMINO migran a TERMINADO
- **GIVEN** una DB con pedidos en `orders.estado_codigo = "EN_CAMINO"` y filas correspondientes en `order_state_history`
- **WHEN** se ejecuta la migración
- **THEN** todos los pedidos y filas de historial reflejan `TERMINADO` consistentemente; ningún FK queda colgando

#### Scenario: ALLOWED_TRANSITIONS usa la clave TERMINADO
- **WHEN** se inspecciona `backend/features/orders/state_machine.py`
- **THEN** la matriz tiene `"EN_PREPARACION": {"TERMINADO", "CANCELADO_ADMIN"}` y `"TERMINADO": {"ENTREGADO"}`; ninguna referencia a `"EN_CAMINO"` queda en el módulo

#### Scenario: Frontend muestra label "Listo" o equivalente
- **WHEN** un usuario ve un pedido cuyo estado actual es `TERMINADO`
- **THEN** el `OrderStatusBadge` muestra un label semánticamente correcto para retiro y envío (e.g. "Listo para retirar/entregar"), no "En camino"

#### Scenario: Downgrade revierte el rename
- **GIVEN** una DB ya migrada al estado nuevo (`TERMINADO`)
- **WHEN** se ejecuta `alembic downgrade -1`
- **THEN** todas las filas vuelven a `EN_CAMINO` consistentemente en `estados_pedido`, `orders`, `order_state_history`
