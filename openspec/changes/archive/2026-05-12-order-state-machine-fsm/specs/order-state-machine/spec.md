# Spec — order-state-machine

## ADDED Requirements

### Requirement: FSM define transiciones válidas

El sistema SHALL aceptar solo las siguientes transiciones de estado de pedido, definidas explícitamente en una constante `ALLOWED_TRANSITIONS` del módulo `backend/features/orders/state_machine.py`:

- `PENDIENTE → CONFIRMADO` (solo automática, ver Req. siguiente).
- `PENDIENTE → CANCELADO`.
- `CONFIRMADO → EN_PREPARACION`.
- `CONFIRMADO → CANCELADO`.
- `EN_PREPARACION → EN_CAMINO`.
- `EN_PREPARACION → CANCELADO`.
- `EN_CAMINO → ENTREGADO`.

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

El sistema SHALL impedir que un usuario humano (cualquier rol) ejecute la transición `PENDIENTE → CONFIRMADO` a través del endpoint manual. Esta transición es exclusiva del proceso automático del webhook de MercadoPago (RN-FS02).

Defensa en doble capa:
1. El schema `AvanzarEstadoRequest` MUST tipar `nuevo_estado` como `Literal["CANCELADO", "EN_PREPARACION", "EN_CAMINO", "ENTREGADO"]` — `CONFIRMADO` no es un valor aceptado.
2. Aunque el schema sea bypassed, `OrderService.avanzar_estado()` MUST rechazar `nuevo_estado="CONFIRMADO"` con `BusinessRuleError("CONFIRMADO solo se setea automáticamente vía webhook de pago")`.

#### Scenario: Pydantic rechaza CONFIRMADO en el endpoint
- **WHEN** el cliente envía `PATCH /api/v1/pedidos/{id}/estado` con body `{"nuevo_estado": "CONFIRMADO"}`
- **THEN** FastAPI responde 422 antes de invocar el service (validación Pydantic falla)

#### Scenario: Service rechaza CONFIRMADO si Pydantic se bypasea
- **WHEN** el código interno invoca `avanzar_estado(user_id=1, pedido_id=1, nuevo_estado="CONFIRMADO", motivo=None)` directamente
- **THEN** se levanta `BusinessRuleError` con detalle "CONFIRMADO solo se setea automáticamente vía webhook de pago"

### Requirement: Permisos por transición (RBAC dinámico)

El sistema SHALL validar, en cada transición manual, que el usuario actor tenga al menos uno de los roles autorizados para esa transición específica. La matriz vive en `TRANSITION_ROLES` del módulo `state_machine.py`:

| Transición                          | Roles autorizados              |
|-------------------------------------|--------------------------------|
| `PENDIENTE → CANCELADO`             | CLIENT, PEDIDOS, ADMIN         |
| `CONFIRMADO → EN_PREPARACION`       | PEDIDOS, ADMIN                 |
| `CONFIRMADO → CANCELADO`            | PEDIDOS, ADMIN                 |
| `EN_PREPARACION → EN_CAMINO`        | PEDIDOS, ADMIN                 |
| `EN_PREPARACION → CANCELADO`        | ADMIN (solo)                   |
| `EN_CAMINO → ENTREGADO`             | PEDIDOS, ADMIN                 |

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
