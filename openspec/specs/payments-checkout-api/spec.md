## ADDED Requirements

### Requirement: POST /api/v1/pagos/ devuelve 200 OK con el resultado de MP como dato

El sistema SHALL responder `200 OK` con un body `PagoCreateResponse` cuando MercadoPago haya devuelto un `status` cualquiera (`approved`, `pending`, `in_process`, `authorized`, `rejected`, `cancelled`, u otros). El body MUST contener `mp_status`, `mp_id`, `status_detail` y `pago_id` (ID interno del `Pago` recién creado).

#### Scenario: MP aprueba el pago

- **GIVEN** un cliente autenticado con rol `CLIENT` y un pedido propio en estado `PENDIENTE` sin pago activo
- **WHEN** envía `POST /api/v1/pagos/` con `card_token`, `payment_method_id`, `installments`, `idempotency_key`, `identification_type` e `identification_number` válidos
- **AND** MercadoPago devuelve `status="approved"` y un `id` de payment
- **THEN** el endpoint responde `200 OK` con `{mp_status: "approved", mp_id: "<id>", status_detail: "accredited", pago_id: <int>}`
- **AND** existe en DB un `Pago` con `mp_status="approved"`, `mp_payment_id="<id>"` ligado a ese pedido
- **AND** el pedido transiciona de `PENDIENTE` a `CONFIRMADO`

#### Scenario: MP responde pending o in_process

- **GIVEN** un cliente autenticado con rol `CLIENT` y un pedido propio en estado `PENDIENTE` sin pago activo
- **WHEN** envía `POST /api/v1/pagos/` con datos válidos
- **AND** MercadoPago devuelve `status="pending"` con `status_detail="pending_review_manual"`
- **THEN** el endpoint responde `200 OK` con `{mp_status: "pending", mp_id: "<id>", status_detail: "pending_review_manual", pago_id: <int>}`
- **AND** existe en DB un `Pago` con `mp_status="pending"` ligado a ese pedido
- **AND** el pedido SIGUE en estado `PENDIENTE` (sin transición)

#### Scenario: MP rechaza el pago

- **GIVEN** un cliente autenticado con rol `CLIENT` y un pedido propio en estado `PENDIENTE` sin pago activo
- **WHEN** envía `POST /api/v1/pagos/` con datos válidos
- **AND** MercadoPago devuelve `status="rejected"` con `status_detail="cc_rejected_insufficient_amount"`
- **THEN** el endpoint responde `200 OK` con `{mp_status: "rejected", mp_id: "<id>", status_detail: "cc_rejected_insufficient_amount", pago_id: <int>}`
- **AND** existe en DB un `Pago` con `mp_status="rejected"` ligado a ese pedido
- **AND** el pedido SIGUE en estado `PENDIENTE` (sin transición)
- **AND** un nuevo intento de pago para el mismo pedido NO está bloqueado por `find_active_by_pedido_id` (porque `rejected` no está en `_ACTIVE_STATUSES`)

#### Scenario: MP cancela el pago

- **GIVEN** un cliente autenticado con rol `CLIENT` y un pedido propio en estado `PENDIENTE` sin pago activo
- **WHEN** envía `POST /api/v1/pagos/` con datos válidos
- **AND** MercadoPago devuelve `status="cancelled"`
- **THEN** el endpoint responde `200 OK` con `{mp_status: "cancelled", mp_id: "<id>", status_detail: <string>, pago_id: <int>}`
- **AND** existe en DB un `Pago` con `mp_status="cancelled"` ligado a ese pedido
- **AND** el pedido SIGUE en estado `PENDIENTE`

#### Scenario: MP devuelve un status inesperado

- **GIVEN** un cliente autenticado con rol `CLIENT` y un pedido propio en estado `PENDIENTE` sin pago activo
- **WHEN** envía `POST /api/v1/pagos/` con datos válidos
- **AND** MercadoPago devuelve `status="refunded"` (o cualquier otro status documentado en MP)
- **THEN** el endpoint responde `200 OK` con `{mp_status: "refunded", mp_id: "<id>", status_detail: <string>, pago_id: <int>}`
- **AND** existe en DB un `Pago` con `mp_status="refunded"` ligado a ese pedido

### Requirement: POST /api/v1/pagos/ devuelve 502 mp_unreachable cuando MercadoPago no responde con status

El sistema SHALL responder con HTTP `502 Bad Gateway` y `code="mp_unreachable"` cuando la llamada a `sdk.payment().create(...)` no devuelva un `status` (por timeout, 5xx, token inválido, o cualquier error de upstream). En ese caso el sistema MUST NOT crear ningún registro `Pago` en la base de datos.

#### Scenario: MP responde con error sin status

- **GIVEN** un cliente autenticado con rol `CLIENT` y un pedido propio en estado `PENDIENTE` sin pago activo
- **WHEN** envía `POST /api/v1/pagos/` con datos válidos
- **AND** MercadoPago devuelve `response={}` y `error={"message": "...", "cause": [...]}`
- **THEN** el endpoint responde `502 Bad Gateway` con `code="mp_unreachable"` y un `detail` que incluye el mensaje y los `causes` de MP
- **AND** NO existe ningún `Pago` nuevo en la DB ligado a ese pedido
- **AND** el pedido SIGUE en estado `PENDIENTE` (sin transición)
- **AND** un nuevo intento de pago para el mismo pedido NO está bloqueado por phantom Pago

#### Scenario: MP timeout

- **GIVEN** un cliente autenticado con rol `CLIENT` y un pedido propio en estado `PENDIENTE` sin pago activo
- **WHEN** envía `POST /api/v1/pagos/` con datos válidos
- **AND** la llamada a MP hace timeout o devuelve 5xx sin status
- **THEN** el endpoint responde `502 Bad Gateway` con `code="mp_unreachable"`
- **AND** NO existe ningún `Pago` nuevo en la DB ligado a ese pedido

### Requirement: PagoCreateResponse declarado como response_model en el router

El router SHALL declarar `response_model=PagoCreateResponse` en el endpoint `POST /api/v1/pagos/` de modo que el schema OpenAPI generado por FastAPI refleje la estructura exacta del response. El schema MUST contener los campos `mp_status: str`, `mp_id: Optional[str]`, `status_detail: str`, `pago_id: int`.

#### Scenario: OpenAPI documenta el response

- **WHEN** se inspecciona `/docs` o `/openapi.json` para el endpoint `POST /api/v1/pagos/`
- **THEN** el response 200 declara un schema con los campos `mp_status`, `mp_id`, `status_detail` y `pago_id`
- **AND** los tipos coinciden con `PagoCreateResponse`

### Requirement: El Pago se persiste con el mp_status real devuelto por MP

El service SHALL persistir el `Pago` con el `mp_status` exacto devuelto por MercadoPago en el primer y único `INSERT`. El repository SHALL aceptar `mp_status` como parámetro de `create_pago(...)` (no como default fijo `"pending"`).

#### Scenario: Pago aprobado se persiste con mp_status approved

- **WHEN** MP devuelve `status="approved"` para una llamada exitosa
- **THEN** el `INSERT` del `Pago` usa `mp_status="approved"` directamente (no se hace primero `pending` y luego `update`)

#### Scenario: Pago rechazado se persiste con mp_status rejected

- **WHEN** MP devuelve `status="rejected"`
- **THEN** el `INSERT` del `Pago` usa `mp_status="rejected"` directamente
- **AND** `rejected` no figura en `_ACTIVE_STATUSES`, por lo que reintentos posteriores funcionan

### Requirement: La transición PENDIENTE→CONFIRMADO falla con logging, no silenciosamente

Cuando el pago es `approved`, el service SHALL invocar `OrderService().transicionar_estado(...)` para mover el pedido de `PENDIENTE` a `CONFIRMADO`. Si la transición falla, el sistema MUST registrar el error con `logger.exception(...)` indicando `pedido_id` y `mp_payment_id`, y MUST NOT re-lanzar la excepción (el pago ya está cobrado; el webhook reconciliará).

#### Scenario: Transición fallida queda en logs

- **GIVEN** MP devuelve `status="approved"` y el `Pago` se persiste
- **WHEN** `OrderService().transicionar_estado(...)` lanza una excepción
- **THEN** el sistema emite un log de nivel `ERROR` con el `pedido_id`, el `mp_payment_id` y el stack trace
- **AND** el endpoint responde `200 OK` con el `PagoCreateResponse` (el pago está aprobado)
- **AND** el webhook (`procesar_webhook`) puede completar la transición en una invocación posterior

#### Scenario: Transición exitosa no genera log de error

- **GIVEN** MP devuelve `status="approved"`
- **WHEN** la transición se ejecuta sin errores
- **THEN** no se emite ningún log de nivel `ERROR` relacionado con la transición
