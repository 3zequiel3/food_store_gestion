# Spec — order-state-machine

## ADDED Requirements

### Requirement: FSM define transiciones válidas

El sistema SHALL aceptar solo las siguientes transiciones de estado de pedido, definidas explícitamente en una constante `ALLOWED_TRANSITIONS` del módulo `backend/features/orders/state_machine.py`:

- `PENDIENTE → CONFIRMADO` (solo automática, ver Req. siguiente).
- `PENDIENTE → CANCELADO`.
- `CONFIRMADO → EN_PREPARACION`.
- `CONFIRMADO → CANCELADO`.
- `EN_PREPARACION → TERMINADO`.
- `EN_PREPARACION → CANCELADO`.
- `TERMINADO → ENTREGADO`.

Cualquier intento de transición fuera de esta lista MUST ser rechazado con `BusinessRuleError` (HTTP 422) por `validate_transition()`.

`ENTREGADO` y `CANCELADO` son estados terminales — no se permite ninguna transición saliente desde ellos (RN-FS06).

#### Scenario: Transición FSM válida pasa la validación
- **WHEN** `validate_transition("CONFIRMADO", "EN_PREPARACION", {"PEDIDOS"})` se invoca
- **THEN** retorna sin levantar excepción

#### Scenario: Transición FSM inválida es rechazada
- **WHEN** `validate_transition("PENDIENTE", "ENTREGADO", {"ADMIN"})` se invoca
- **THEN** se levanta `BusinessRuleError` con detalle "Transición 'PENDIENTE' → 'ENTREGADO' no permitida"

#### Scenario: Salto de estado es rechazado
- **WHEN** el cliente invoca `PATCH /api/v1/pedidos/{id}/estado` con `nuevo_estado="EN_CAMINO"` sobre un pedido en `CONFIRMADO`
- **THEN** la respuesta es 422 con código `business_rule_error`

#### Scenario: Estado terminal no transiciona
- **WHEN** el gestor PEDIDOS invoca `PATCH` para llevar un pedido `ENTREGADO` a cualquier otro estado
- **THEN** la respuesta es 422 — `ENTREGADO` no figura en `ALLOWED_TRANSITIONS` como origen

#### Scenario: CANCELADO es terminal
- **WHEN** se intenta transicionar un pedido en `CANCELADO` a cualquier otro estado
- **THEN** la respuesta es 422

### Requirement: PENDIENTE → CONFIRMADO es exclusivamente automática

El sistema SHALL impedir que un usuario humano CLIENTe ejecute la transición `PENDIENTE → CONFIRMADO` a través del endpoint manual. Esta transición es exclusiva del proceso automático del webhook de MercadoPago. **Sin embargo**, en el nuevo flow de `checkout-pay-first-flow`, el camino habitual de creación de un pedido online ya lo deja directamente en `PENDIENTE` (no en estado intermedio), y la transición `PENDIENTE → CONFIRMADO` la dispara el local cuando acepta el pedido (rol PEDIDOS o ADMIN). El webhook MP retiene este comportamiento como red de seguridad para casos excepcionales (reconciliación post-cobro fallido) — sigue siendo exclusivo del sistema, no humano. (RN-FS02 actualizada para reflejar la nueva semántica de PENDIENTE descripta abajo)

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

### Requirement: Permisos por transición (RBAC dinámico)

El sistema SHALL validar, en cada transición manual, que el usuario actor tenga al menos uno de los roles autorizados para esa transición específica. La matriz vive en `TRANSITION_ROLES` del módulo `state_machine.py`:

| Transición                          | Roles autorizados              |
|-------------------------------------|--------------------------------|
| `PENDIENTE → CANCELADO`             | CLIENT, PEDIDOS, ADMIN         |
| `CONFIRMADO → EN_PREPARACION`       | PEDIDOS, ADMIN                 |
| `CONFIRMADO → CANCELADO`            | PEDIDOS, ADMIN                 |
| `EN_PREPARACION → TERMINADO`        | PEDIDOS, ADMIN                 |
| `EN_PREPARACION → CANCELADO`        | ADMIN (solo)                   |
| `TERMINADO → ENTREGADO`             | PEDIDOS, ADMIN                 |

Si el usuario no tiene ningún rol válido para la transición pedida, el sistema MUST responder HTTP 403 con `ForbiddenError`.

#### Scenario: ADMIN cancela un pedido en EN_PREPARACION
- **WHEN** un usuario con rol `ADMIN` envía `PATCH` con `nuevo_estado="CANCELADO"` sobre un pedido en `EN_PREPARACION`
- **THEN** la transición se ejecuta — `ADMIN` está en `TRANSITION_ROLES[("EN_PREPARACION", "CANCELADO")]`

#### Scenario: PEDIDOS no puede cancelar pedido en EN_PREPARACION
- **WHEN** un usuario con rol `PEDIDOS` (sin ADMIN) envía `PATCH` con `nuevo_estado="CANCELADO"` sobre un pedido en `EN_PREPARACION`
- **THEN** la respuesta es 403 — `RN-RB08` solo permite ADMIN

#### Scenario: CLIENT no puede avanzar un pedido a EN_PREPARACION
- **WHEN** un usuario con rol `CLIENT` (sin otros roles) envía `PATCH` con `nuevo_estado="EN_PREPARACION"` sobre un pedido en `CONFIRMADO`
- **THEN** la respuesta es 403

### Requirement: Ownership CLIENT en cancelaciones propias

El sistema SHALL impedir que un usuario con rol `CLIENT` (sin otros roles más privilegiados) ejecute transiciones sobre pedidos que **no le pertenecen** (`pedido.user_id != user_id`).

La respuesta MUST ser HTTP 404 (`NotFoundError`), no 403, para no filtrar la existencia del pedido al cliente que no es dueño (patrón anti-leak, RN-RB05).

Usuarios con rol `PEDIDOS` o `ADMIN` ven cualquier pedido — la validación de ownership SHALL saltearse para ellos.

#### Scenario: CLIENT cancela su propio pedido en PENDIENTE
- **WHEN** un `CLIENT` con `user_id=5` envía `PATCH` sobre pedido `pedido_id=10` cuyo `user_id=5`, con `nuevo_estado="CANCELADO"`
- **THEN** la cancelación procede — ownership OK

#### Scenario: CLIENT intenta cancelar pedido ajeno
- **WHEN** un `CLIENT` con `user_id=5` envía `PATCH` sobre pedido `pedido_id=10` cuyo `user_id=99`
- **THEN** la respuesta es 404 — el cliente no es dueño, el sistema reporta "no encontrado"

#### Scenario: PEDIDOS opera sobre pedido de cualquier cliente
- **WHEN** un gestor con rol `PEDIDOS` (no es dueño) envía `PATCH` sobre cualquier pedido
- **THEN** la operación procede (sujeto al resto de validaciones FSM/RBAC)

### Requirement: Motivo obligatorio para cancelaciones desde CONFIRMADO o EN_PREPARACION

El sistema SHALL exigir un `motivo` no vacío (excluyendo espacios en blanco) cuando la transición es `(CONFIRMADO|EN_PREPARACION) → CANCELADO`.

Para cualquier otra transición, `motivo` es opcional.

Si `motivo` falta o es solo espacios cuando es obligatorio, MUST responder 422 con `BusinessRuleError`.

El campo `motivo` MUST tener máximo 500 caracteres (validado por Pydantic y por la columna `VARCHAR(500)` en `order_state_history`).

#### Scenario: Motivo obligatorio en cancelación de pedido CONFIRMADO
- **WHEN** un PEDIDOS envía `PATCH` con `nuevo_estado="CANCELADO"` sobre pedido en `CONFIRMADO`, sin `motivo` (o con `motivo=""`)
- **THEN** la respuesta es 422 con detalle "motivo es obligatorio para cancelar pedidos desde CONFIRMADO o EN_PREPARACION"

#### Scenario: Motivo opcional en cancelación de pedido PENDIENTE
- **WHEN** un CLIENT envía `PATCH` con `nuevo_estado="CANCELADO"` sobre pedido en `PENDIENTE`, sin `motivo`
- **THEN** la cancelación procede; `motivo=NULL` en historial

#### Scenario: Motivo excede 500 caracteres
- **WHEN** un usuario envía `motivo` con 501 caracteres
- **THEN** la respuesta es 422 (validación Pydantic)

### Requirement: Decremento atómico de stock en PENDIENTE → CONFIRMADO

El sistema SHALL decrementar el `stock_cantidad` de cada `Producto` asociado al pedido cuando la transición es `PENDIENTE → CONFIRMADO`. Este decremento MUST ocurrir en la misma Unit of Work que cambia el estado y crea el historial (RN-FS03, RN-FS04).

El decremento MUST usar `SELECT FOR UPDATE` sobre cada `productos.id` para serializar bajo concurrencia.

Si el stock disponible de algún producto es insuficiente al momento de confirmar, MUST levantar `BusinessRuleError("Stock insuficiente para confirmar pedido: ...")` y la UoW MUST revertir todo (incluyendo el cambio de estado y el historial parcial).

Esta lógica se aplica indistintamente cuando la transición se dispara desde el webhook (SISTEMA) o desde un endpoint manual — la regla vive en `OrderService.transicionar_estado()`.

#### Scenario: Webhook confirma pedido y decrementa stock
- **GIVEN** un pedido en `PENDIENTE` con un item de `cantidad=3` para `producto_id=7` (stock actual 10)
- **WHEN** llega un webhook de MP con `payment.status="approved"` y `PaymentService.procesar_webhook()` invoca `transicionar_estado(pedido_id, "PENDIENTE", "CONFIRMADO", actor_id=None)`
- **THEN** el `Producto.stock_cantidad` para `producto_id=7` queda en 7, el pedido queda en `CONFIRMADO`, y `order_state_history` tiene una nueva fila

#### Scenario: Confirmación falla por stock insuficiente
- **GIVEN** un pedido en `PENDIENTE` con `cantidad=5` para un producto con `stock=2`
- **WHEN** se intenta `PENDIENTE → CONFIRMADO`
- **THEN** se levanta `BusinessRuleError`, el stock NO se modifica, el estado NO cambia, no se crea historial — rollback completo

### Requirement: Restauración atómica de stock al cancelar pedido con stock decrementado

El sistema SHALL restaurar el `stock_cantidad` de cada `Producto` cuando la transición es `CONFIRMADO → CANCELADO` o `EN_PREPARACION → CANCELADO`. La restauración suma `+cantidad` al stock por cada `DetallePedido` del pedido. MUST ocurrir en la misma UoW que cambia el estado y crea el historial.

Cancelaciones desde `PENDIENTE` NO restauran stock (no se había decrementado).

#### Scenario: Cancelación desde CONFIRMADO restaura stock
- **GIVEN** un pedido en `CONFIRMADO` con un item de `cantidad=2` para `producto_id=4` (stock actual tras confirmación: 8, original era 10)
- **WHEN** un PEDIDOS cancela con `motivo="Sin tiempo de cocinar"`
- **THEN** `Producto.stock_cantidad` vuelve a 10, el pedido queda en `CANCELADO`, hay nueva fila de historial con `motivo` persistido

#### Scenario: Cancelación desde PENDIENTE no toca stock
- **GIVEN** un pedido en `PENDIENTE` con item de `cantidad=2` para producto con stock 10
- **WHEN** el CLIENT cancela
- **THEN** stock sigue en 10 (no se había decrementado), pedido `CANCELADO`, historial registrado

#### Scenario: Cancelación desde EN_PREPARACION (solo ADMIN) restaura stock
- **GIVEN** un pedido en `EN_PREPARACION` con item de `cantidad=1` (stock actual 4)
- **WHEN** un ADMIN cancela con motivo
- **THEN** stock vuelve a 5, pedido `CANCELADO`

### Requirement: Idempotencia — segunda transición desde estado ya cambiado responde 409

El sistema SHALL responder HTTP 409 (`InvalidStateTransitionError`) cuando se intenta transicionar un pedido cuyo `estado_codigo` actual no coincide con el `estado_anterior` esperado.

Este comportamiento existe ya en `transicionar_estado()` y MUST conservarse — sirve como mecanismo de idempotencia frente a webhooks duplicados, doble click del frontend, o race conditions.

#### Scenario: Webhook duplicado responde 409 en el segundo intento
- **GIVEN** un pedido en `CONFIRMADO` (porque el primer webhook ya lo confirmó)
- **WHEN** llega un segundo webhook que invoca `transicionar_estado(pedido_id, "PENDIENTE", "CONFIRMADO", actor_id=None)`
- **THEN** se levanta `InvalidStateTransitionError` con detalle "el pedido está en 'CONFIRMADO', se esperaba 'PENDIENTE'" — el segundo decremento NO ocurre

#### Scenario: Doble click del cliente cancelando
- **GIVEN** un pedido en `PENDIENTE`
- **WHEN** el cliente envía dos requests `PATCH` casi simultáneos con `nuevo_estado="CANCELADO"`
- **THEN** uno responde 200 y el otro 409 (porque al ejecutar, el pedido ya está en `CANCELADO`)

### Requirement: SELECT FOR UPDATE en lectura del pedido durante transición

El sistema SHALL adquirir un lock pesimista (`SELECT ... FOR UPDATE`) sobre la fila del pedido al inicio de `OrderService.transicionar_estado()`. Esto reemplaza la lectura sin lock que existe actualmente vía `find_by_id()`.

El método nuevo `OrderRepository.get_pedido_for_update(pedido_id)` MUST implementarlo.

En SQLite (tests) el lock es no-op; tests de concurrencia real MUST marcarse `@pytest.mark.pg_only`.

#### Scenario: Lock previene race condition en concurrencia (Postgres)
- **GIVEN** un pedido en `PENDIENTE` y dos workers procesando el mismo webhook en paralelo
- **WHEN** ambos invocan `transicionar_estado(..., "PENDIENTE", "CONFIRMADO", ...)`
- **THEN** el segundo worker espera al lock, lee `CONFIRMADO` cuando lo obtiene, y aborta con `InvalidStateTransitionError`. Solo un decremento de stock ocurre.

### Requirement: Append-only historial con motivo persistido

El sistema SHALL persistir cada transición exitosa en `order_state_history` con: `estado_anterior_codigo`, `estado_nuevo_codigo`, `cambiado_por_id` (NULL = SISTEMA), `motivo` (NULL si no se proveyó), `creado_en` (timestamp).

La tabla `order_state_history` hereda de `AppendOnlyBaseModel` — solo INSERT, nunca UPDATE ni DELETE a nivel ORM (RN-FS07, RN-03, RN-PA02).

La columna `motivo` MUST agregarse vía migration Alembic como `VARCHAR(500) NULL`.

#### Scenario: Historial incluye motivo en cancelación con motivo
- **WHEN** un PEDIDOS cancela un pedido `CONFIRMADO` con `motivo="Cliente pidió rembolso"`
- **THEN** existe una fila nueva en `order_state_history` con `estado_anterior_codigo="CONFIRMADO"`, `estado_nuevo_codigo="CANCELADO"`, `cambiado_por_id=<id del gestor>`, `motivo="Cliente pidió rembolso"`

#### Scenario: Historial omite motivo en transición de avance
- **WHEN** un PEDIDOS avanza un pedido `CONFIRMADO → EN_PREPARACION` sin motivo
- **THEN** existe una fila nueva con `motivo=NULL`

#### Scenario: Historial registra SISTEMA cuando es webhook
- **WHEN** el webhook confirma un pedido
- **THEN** la fila de historial tiene `cambiado_por_id=NULL` (representa SISTEMA)

### Requirement: Compatibilidad backwards con webhook de payment-mercadopago-backend

El sistema SHALL mantener la firma actual de `OrderService.transicionar_estado(pedido_id, estado_anterior, estado_nuevo, actor_id=None)` invocable sin cambios desde `PaymentService.procesar_webhook()`. Cualquier parámetro nuevo (ej. `motivo`) MUST ser opcional con default.

La extensión de la implementación (side-effects de stock condicionales, `FOR UPDATE`) MUST aplicarse a esa misma llamada — el webhook ahora también decrementa stock al confirmar, sin que su línea de invocación cambie.

#### Scenario: Webhook sigue invocando con la firma original
- **GIVEN** el código de `PaymentService.procesar_webhook()` (change #15) que llama `service.transicionar_estado(pedido_id, "PENDIENTE", "CONFIRMADO", actor_id=None)`
- **WHEN** tras este change se ejecuta ese flow con un webhook real
- **THEN** la transición funciona, el stock se decrementa, el historial se crea con `cambiado_por_id=NULL` y `motivo=NULL`

#### Scenario: Tests de regresión de #15 siguen verdes
- **WHEN** se corre la suite completa de tests de `backend/features/payments/` heredada de #15
- **THEN** todos los tests pasan sin modificación

### Requirement: Endpoint PATCH /api/v1/pedidos/{pedido_id}/estado

El sistema SHALL exponer un endpoint REST `PATCH /api/v1/pedidos/{pedido_id}/estado` que:

- Requiere autenticación Bearer JWT (`Depends(get_current_user)`). 401 si falta o es inválido.
- Acepta body JSON validado por `AvanzarEstadoRequest`:
  ```json
  {
    "nuevo_estado": "CANCELADO" | "EN_PREPARACION" | "EN_CAMINO" | "ENTREGADO",
    "motivo": "string opcional (máx 500 chars)"
  }
  ```
- Delega a `OrderService.avanzar_estado(user_id=current_user.id, pedido_id, nuevo_estado, motivo)`.
- Retorna 200 OK con `PedidoRead` del pedido actualizado.
- Mapea excepciones a HTTP: `NotFoundError`→404, `ForbiddenError`→403, `InvalidStateTransitionError`→409, `BusinessRuleError`→422.

#### Scenario: Avance exitoso retorna 200 con estado actualizado
- **WHEN** un PEDIDOS envía `PATCH /api/v1/pedidos/42/estado` con `{"nuevo_estado": "EN_PREPARACION"}` sobre pedido `CONFIRMADO`
- **THEN** respuesta 200 con `PedidoRead` mostrando `estado_codigo="EN_PREPARACION"`

#### Scenario: Pedido inexistente retorna 404
- **WHEN** se envía `PATCH /api/v1/pedidos/9999/estado` y el pedido no existe
- **THEN** respuesta 404

#### Scenario: Sin auth retorna 401
- **WHEN** se envía `PATCH` sin header `Authorization`
- **THEN** respuesta 401

### Requirement: Response payload del endpoint usa PedidoRead

El sistema SHALL retornar `PedidoRead` (schema ya existente en `backend/features/orders/schemas.py`) como response body del endpoint. Incluye `id`, `user_id`, `total`, `estado_codigo`, `forma_pago_codigo`, items, etc.

NO debe retornar el historial completo en este endpoint — eso es responsabilidad de `GET /pedidos/{id}` (capability `order-visualization`, change #17).

#### Scenario: Response incluye nuevo estado
- **WHEN** la transición se completa
- **THEN** el body de respuesta contiene `estado_codigo` igual al `nuevo_estado` solicitado

---

## MODIFIED Requirements (from change display-cocina-kds)

### Requirement: FSM define transiciones válidas

El sistema SHALL aceptar solo las siguientes transiciones de estado de pedido, definidas explícitamente en una constante `ALLOWED_TRANSITIONS` del módulo `backend/features/orders/state_machine.py`:

- `PENDIENTE → CONFIRMADO` (solo automática / aceptación del local, ver Req. siguiente).
- `PENDIENTE → CANCELADO` (y variantes `CANCELADO_ADMIN`, `CANCELADO_CLIENTE`).
- `CONFIRMADO → EN_PREPARACION`.
- `CONFIRMADO → CANCELADO_ADMIN`.
- `EN_PREPARACION → TERMINADO`.
- `EN_PREPARACION → CANCELADO_ADMIN`.
- `TERMINADO → EN_CAMINO`.
- `TERMINADO → ENTREGADO`.
- `EN_CAMINO → ENTREGADO`.

`EN_CAMINO` se **re-introduce** al catálogo como nodo del FSM entre `TERMINADO` y `ENTREGADO`. La elección entre `TERMINADO → EN_CAMINO` y `TERMINADO → ENTREGADO` la decide una regla de negocio según el tipo de entrega del pedido (ver requirement de branching por tipo de entrega), no `ALLOWED_TRANSITIONS` por sí sola.

Cualquier intento de transición fuera de esta lista MUST ser rechazado con `BusinessRuleError` (HTTP 422) por `validate_transition()`.

`ENTREGADO`, `CANCELADO`, `CANCELADO_ADMIN` y `CANCELADO_CLIENTE` son estados terminales — no se permite ninguna transición saliente desde ellos (RN-FS06).

#### Scenario: Transición FSM válida pasa la validación
- **WHEN** `validate_transition("CONFIRMADO", "EN_PREPARACION", {"COCINA"})` se invoca
- **THEN** retorna sin levantar excepción

#### Scenario: Transición FSM inválida es rechazada
- **WHEN** `validate_transition("PENDIENTE", "ENTREGADO", {"ADMIN"})` se invoca
- **THEN** se levanta `BusinessRuleError` con detalle "Transición 'PENDIENTE' → 'ENTREGADO' no permitida"

#### Scenario: EN_CAMINO es origen válido hacia ENTREGADO
- **WHEN** `validate_transition("EN_CAMINO", "ENTREGADO", {"ADMIN"})` se invoca
- **THEN** retorna sin levantar excepción

#### Scenario: TERMINADO admite EN_CAMINO y ENTREGADO en el FSM
- **WHEN** se inspecciona `ALLOWED_TRANSITIONS["TERMINADO"]`
- **THEN** contiene tanto `"EN_CAMINO"` como `"ENTREGADO"`

#### Scenario: Estado terminal no transiciona
- **WHEN** el ADMIN invoca `PATCH` para llevar un pedido `ENTREGADO` a cualquier otro estado
- **THEN** la respuesta es 422 — `ENTREGADO` no figura en `ALLOWED_TRANSITIONS` como origen

#### Scenario: CANCELADO es terminal
- **WHEN** se intenta transicionar un pedido en `CANCELADO` a cualquier otro estado
- **THEN** la respuesta es 422

### Requirement: Rename del código `EN_CAMINO` a `TERMINADO` (vocabulario unificado retiro/envío)

`EN_CAMINO` deja de ser un alias eliminado: el sistema SHALL re-introducir `EN_CAMINO` como estado propio del catálogo `order_states`, distinto de `TERMINADO`, mediante una migración Alembic que revierte parcialmente `20260518_0100_rename_en_camino_to_terminado`. `TERMINADO` mantiene su semántica de "comida lista, esperando despacho o retiro"; `EN_CAMINO` representa el reparto en curso de un pedido de envío a domicilio.

Tras esta migración el nodo `TERMINADO` tiene:
- Entrante: `EN_PREPARACION → TERMINADO` (roles PEDIDOS, ADMIN, COCINA).
- Salientes: `TERMINADO → EN_CAMINO` (roles PEDIDOS, ADMIN, solo envíos) y `TERMINADO → ENTREGADO` (roles PEDIDOS, ADMIN, solo retiros).

El alcance de la re-introducción incluye:

1. **Backend datos**: migración Alembic que vuelve a insertar la fila `order_states.codigo = "EN_CAMINO"` (con `orden` entre `TERMINADO` y `ENTREGADO`, `es_terminal=False`). La migración MUST tener `downgrade()` que la elimine de forma segura (solo si no hay pedidos en ese estado).
2. **Backend código**: `state_machine.py` agrega `EN_CAMINO` a `ALLOWED_TRANSITIONS` y `TRANSITION_ROLES`; los schemas que tipan `nuevo_estado` lo aceptan como valor válido.
3. **Frontend**: los tipos y componentes de pedidos (`orders.types.ts`, `OrderTimeline`, `OrderStatusBadge`, `OrderStateActions`, charts de métricas) reconocen `EN_CAMINO` con un label adecuado a envío ("En camino").

**Justificación**: el rename del 18-may había unificado retiro y envío bajo `TERMINADO`, pero el despacho de envíos necesita un estado propio que distinga "listo" de "en reparto". Documentado en D4 del design.

#### Scenario: Migración Alembic re-agrega EN_CAMINO al catálogo
- **GIVEN** una DB cuyo catálogo `order_states` no contiene `"EN_CAMINO"`
- **WHEN** se ejecuta `alembic upgrade head` con la migración del change
- **THEN** existe una fila `order_states.codigo = "EN_CAMINO"` con `es_terminal=False`

#### Scenario: ALLOWED_TRANSITIONS reconoce EN_CAMINO
- **WHEN** se inspecciona `backend/features/orders/state_machine.py`
- **THEN** `ALLOWED_TRANSITIONS["TERMINADO"]` incluye `"EN_CAMINO"` y `ALLOWED_TRANSITIONS["EN_CAMINO"]` incluye `"ENTREGADO"`

#### Scenario: Frontend muestra label de envío para EN_CAMINO
- **WHEN** un usuario ve un pedido cuyo estado actual es `EN_CAMINO`
- **THEN** el `OrderStatusBadge` muestra "En camino" (o equivalente de reparto en curso)

#### Scenario: Downgrade elimina EN_CAMINO de forma segura
- **GIVEN** una DB migrada con `EN_CAMINO` en el catálogo y sin pedidos en ese estado
- **WHEN** se ejecuta `alembic downgrade -1`
- **THEN** la fila `EN_CAMINO` se elimina del catálogo sin dejar FKs colgando

### Requirement: Permisos por transición (RBAC dinámico)

El sistema SHALL validar, en cada transición manual, que el usuario actor tenga al menos uno de los roles autorizados para esa transición específica. La matriz vive en `TRANSITION_ROLES` del módulo `state_machine.py`. Los 4 roles de la spec (`ADMIN`/`STOCK`/`PEDIDOS`/`CLIENT`) se mantienen intactos; este change solo **agrega** `COCINA` a las 2 transiciones de cocina y re-introduce `EN_CAMINO`. La matriz resultante:

| Transición                          | Roles autorizados              |
|-------------------------------------|--------------------------------|
| `PENDIENTE → CANCELADO`             | CLIENT, PEDIDOS, ADMIN         |
| `PENDIENTE → CANCELADO_CLIENTE`     | CLIENT                         |
| `PENDIENTE → CANCELADO_ADMIN`       | PEDIDOS, ADMIN                 |
| `CONFIRMADO → EN_PREPARACION`       | PEDIDOS, ADMIN, COCINA         |
| `CONFIRMADO → CANCELADO_ADMIN`      | PEDIDOS, ADMIN                 |
| `EN_PREPARACION → TERMINADO`        | PEDIDOS, ADMIN, COCINA         |
| `EN_PREPARACION → CANCELADO_ADMIN`  | ADMIN (solo)                   |
| `TERMINADO → EN_CAMINO`             | PEDIDOS, ADMIN                 |
| `TERMINADO → ENTREGADO`             | PEDIDOS, ADMIN                 |
| `EN_CAMINO → ENTREGADO`             | PEDIDOS, ADMIN                 |

El despacho y la entrega los siguen ejecutando `PEDIDOS`/`ADMIN` (sin cambios respecto del estado actual); las transiciones de cocina (`CONFIRMADO → EN_PREPARACION`, `EN_PREPARACION → TERMINADO`) **suman** `COCINA` a los `PEDIDOS`/`ADMIN` que ya las ejecutaban. Si el usuario no tiene ningún rol válido para la transición pedida, el sistema MUST responder HTTP 403 con `ForbiddenError`.

#### Scenario: COCINA avanza un pedido a EN_PREPARACION
- **WHEN** un usuario con rol `COCINA` envía `PATCH` con `nuevo_estado="EN_PREPARACION"` sobre un pedido en `CONFIRMADO`
- **THEN** la transición se ejecuta — `COCINA` está en `TRANSITION_ROLES[("CONFIRMADO", "EN_PREPARACION")]`

#### Scenario: PEDIDOS sigue avanzando un pedido a EN_PREPARACION
- **WHEN** un usuario con rol `PEDIDOS` envía `PATCH` con `nuevo_estado="EN_PREPARACION"` sobre un pedido en `CONFIRMADO`
- **THEN** la transición se ejecuta — `PEDIDOS` permanece en `TRANSITION_ROLES[("CONFIRMADO", "EN_PREPARACION")]`

#### Scenario: COCINA no puede despachar a EN_CAMINO
- **WHEN** un usuario con solo rol `COCINA` envía `PATCH` con `nuevo_estado="EN_CAMINO"` sobre un pedido en `TERMINADO`
- **THEN** la respuesta es 403 — el despacho es de `PEDIDOS`/`ADMIN`

#### Scenario: ADMIN despacha un envío a EN_CAMINO
- **WHEN** un usuario con rol `ADMIN` envía `PATCH` con `nuevo_estado="EN_CAMINO"` sobre un pedido de envío en `TERMINADO`
- **THEN** la transición se ejecuta

#### Scenario: CLIENT no puede avanzar un pedido a EN_PREPARACION
- **WHEN** un usuario con rol `CLIENT` (sin otros roles) envía `PATCH` con `nuevo_estado="EN_PREPARACION"` sobre un pedido en `CONFIRMADO`
- **THEN** la respuesta es 403

## ADDED Requirements (from change display-cocina-kds)

### Requirement: Branching de despacho condicional al tipo de entrega

El sistema SHALL elegir la transición de salida de `TERMINADO` según el tipo de entrega del pedido, determinado por `Pedido.direccion_entrega_id`:

- **Envío** (`direccion_entrega_id NOT NULL`): el camino válido es `TERMINADO → EN_CAMINO → ENTREGADO`. Un intento de `TERMINADO → ENTREGADO` directo MUST ser rechazado con `BusinessRuleError` (422).
- **Retiro** (`direccion_entrega_id IS NULL`): el camino válido es `TERMINADO → ENTREGADO` directo. Un intento de `TERMINADO → EN_CAMINO` MUST ser rechazado con `BusinessRuleError` (422).

Esta regla vive en el servicio (`OrderService`), que carga el `Pedido` concreto, no en `ALLOWED_TRANSITIONS` (que es un mapa estático de códigos sin conocimiento de la instancia).

#### Scenario: Envío exige pasar por EN_CAMINO
- **GIVEN** un pedido de envío (`direccion_entrega_id` no nulo) en estado `TERMINADO`
- **WHEN** un ADMIN intenta `TERMINADO → ENTREGADO` directo
- **THEN** la respuesta es 422

#### Scenario: Envío válido pasa por EN_CAMINO y luego ENTREGADO
- **GIVEN** un pedido de envío en `TERMINADO`
- **WHEN** un ADMIN ejecuta `TERMINADO → EN_CAMINO` y luego `EN_CAMINO → ENTREGADO`
- **THEN** ambas transiciones se ejecutan correctamente

#### Scenario: Retiro va directo a ENTREGADO
- **GIVEN** un pedido de retiro (`direccion_entrega_id` nulo) en `TERMINADO`
- **WHEN** un ADMIN ejecuta `TERMINADO → ENTREGADO`
- **THEN** la transición se ejecuta correctamente

#### Scenario: Retiro no admite EN_CAMINO
- **GIVEN** un pedido de retiro en `TERMINADO`
- **WHEN** un ADMIN intenta `TERMINADO → EN_CAMINO`
- **THEN** la respuesta es 422

### Requirement: Publicación de eventos de tiempo real tras commit de transición

El sistema SHALL publicar un evento hacia las pantallas de cocina conectadas después de commitear cada transición de estado relevante en la Unit of Work del servicio del FSM. La publicación SHALL ocurrir post-commit y SHALL ser best-effort: un fallo del broadcast MUST NOT revertir la transición. Los eventos son `pedido_confirmado`, `pedido_en_preparacion`, `pedido_terminado` y `pedido_cancelado` (ver capability `kitchen-display-backend`).

#### Scenario: Transición a EN_PREPARACION publica evento post-commit
- **GIVEN** una pantalla de cocina conectada
- **WHEN** un pedido transiciona `CONFIRMADO → EN_PREPARACION` y la UoW commitea
- **THEN** se publica `pedido_en_preparacion` después del commit

#### Scenario: Fallo del broadcast no afecta la transición
- **GIVEN** una transición ya commiteada
- **WHEN** la publicación del evento falla
- **THEN** la transición permanece persistida y la respuesta HTTP es exitosa
