# checkout — Spec vigente

Capability para crear pedidos de forma atómica online (con pago en MercadoPago) o pickup (pago en efectivo). Este capability centraliza todo el flujo de checkout que antes estaba repartido entre `order-creation`, `payment-mercadopago-backend` y `payments-checkout-api`, junto con validaciones de carrito, snapshots e idempotencia. Especificación completa en `openspec/changes/checkout-pay-first-flow/specs/checkout/spec.md`.

---

## Requirements

### Requirement: POST /api/v1/checkout/online crea pedido + pago atómicamente solo si MP aprueba

El sistema SHALL exponer `POST /api/v1/checkout/online` que ejecuta el flow de checkout con pago online en MercadoPago. El endpoint SHALL persistir el `Pedido`, sus `DetallePedido`, el `HistorialEstadoPedido` inicial y el `Pago` en una **única transacción UnitOfWork**, y SHALL hacerlo SOLO cuando MP devuelva `status == "approved"`. Para cualquier otro `status` devuelto por MP, el endpoint SHALL NOT persistir ningún registro y SHALL responder con un error HTTP descriptivo (ver siguientes requirements).

#### Scenario: MP aprueba el pago — pedido + pago creados en una UoW
- **GIVEN** un cliente autenticado con rol `CLIENT`, productos válidos en el body, dirección propia válida (o pickup), forma de pago online
- **WHEN** el cliente envía `POST /api/v1/checkout/online` con `items`, `direccion_id` (o null), `tipo_entrega`, `notas`, `card_token`, `payment_method_id`, `installments`, `idempotency_key` (UUID4), `identification_type`, `identification_number`
- **AND** MercadoPago devuelve `status="approved"` con un `id` válido y `status_detail="accredited"`
- **THEN** el endpoint responde `200 OK` con `{pedido_id, pago_id, mp_status: "approved", mp_id, status_detail: "accredited"}`
- **AND** en DB existe exactamente 1 fila en `orders` con `estado_codigo="PENDIENTE"`, N filas en `order_items` (una por item del request), 1 fila en `order_state_history` con `estado_anterior_codigo=NULL` y `estado_nuevo_codigo="PENDIENTE"`, y 1 fila en `pagos` con `mp_status="approved"`, `mp_payment_id="<id>"`, `external_reference="<idempotency_key>"`, `pedido_id=<id del pedido recién creado>`

#### Scenario: Atomicidad — fallo en persistencia del Pago revierte todo
- **GIVEN** MP devuelve `status="approved"` correctamente
- **WHEN** durante la persistencia, la inserción del `Pago` falla (e.g. error de integridad simulado)
- **THEN** el endpoint responde `500 Internal Server Error`
- **AND** en DB no existe ningún `Pedido`, `DetallePedido`, `HistorialEstadoPedido` ni `Pago` asociado a este request
- **AND** se emite un `logger.exception` con `mp_payment_id`, `idempotency_key`, `user_id`, payload del carrito y stack trace

#### Scenario: Pedido recién creado nace en PENDIENTE con historial inicial
- **WHEN** el checkout online completa exitosamente
- **THEN** `orders.estado_codigo` vale exactamente `"PENDIENTE"`
- **AND** existe una fila en `order_state_history` con `estado_anterior_codigo=NULL`, `estado_nuevo_codigo="PENDIENTE"`, `cambiado_por_id=<user_id del cliente>`

---

### Requirement: POST /api/v1/checkout/online rechaza pagos no aprobados sin crear pedido

El sistema SHALL responder con HTTP `402 Payment Required` (o `422 Unprocessable Entity` según preferencia del proyecto, manteniendo consistencia) cuando MercadoPago devuelva cualquier `status != "approved"` (incluyendo `pending`, `in_process`, `authorized`, `rejected`, `cancelled`, `refunded`, u otros). El body de error SHALL incluir `code`, `detail` (mensaje user-friendly), `mp_status` y `status_detail`. NINGÚN registro SHALL persistirse en este caso.

#### Scenario: MP responde rejected — pedido no se crea
- **WHEN** el cliente envía `POST /api/v1/checkout/online` con body válido
- **AND** MP devuelve `status="rejected"` con `status_detail="cc_rejected_insufficient_amount"`
- **THEN** el endpoint responde `402 Payment Required` (o `422`) con `{code: "payment_rejected", detail: "Saldo insuficiente. Probá con otra tarjeta.", mp_status: "rejected", status_detail: "cc_rejected_insufficient_amount"}`
- **AND** en DB no existe ningún `Pedido` ni `Pago` ligado a este request

#### Scenario: MP responde pending — pedido NO se crea (modo estricto D3)
- **WHEN** el cliente envía `POST /api/v1/checkout/online` con body válido
- **AND** MP devuelve `status="pending"` con `status_detail="pending_review_manual"`
- **THEN** el endpoint responde `402 Payment Required` (o `422`) con `{code: "payment_pending_not_accepted", detail: "Tu pago quedó en revisión y no podemos confirmar el pedido. Probá con otra tarjeta o elegí pago en efectivo al retirar.", mp_status: "pending", status_detail: "pending_review_manual"}`
- **AND** en DB no existe ningún `Pedido` ni `Pago`

#### Scenario: MP responde in_process — pedido NO se crea (modo estricto D3)
- **WHEN** MP devuelve `status="in_process"`
- **THEN** el endpoint responde `402 Payment Required` (o `422`) con `code="payment_pending_not_accepted"`
- **AND** en DB no existe ningún `Pedido` ni `Pago`

#### Scenario: MP responde cancelled — pedido NO se crea
- **WHEN** MP devuelve `status="cancelled"`
- **THEN** el endpoint responde `402 Payment Required` (o `422`) con `code="payment_cancelled"`
- **AND** en DB no existe ningún `Pedido` ni `Pago`

#### Scenario: MP responde un status no documentado — pedido NO se crea
- **WHEN** MP devuelve un `status` desconocido (e.g. `"refunded"`, `"some_new_status"`)
- **THEN** el endpoint responde `402 Payment Required` (o `422`) con `code="payment_unexpected_status"`, incluye `mp_status` y `status_detail` para diagnóstico
- **AND** en DB no existe ningún `Pedido` ni `Pago`

---

### Requirement: POST /api/v1/checkout/online responde 502 cuando MP no contesta

El sistema SHALL responder HTTP `502 Bad Gateway` con `code="mp_unreachable"` cuando la llamada a `sdk.payment().create(...)` no devuelva un `status` (timeout, 5xx upstream, token inválido, error de red). En ese caso NINGÚN registro SHALL persistirse.

#### Scenario: MP timeout — sin pedido creado
- **WHEN** el cliente envía `POST /api/v1/checkout/online` con datos válidos
- **AND** la llamada a MP timeoutea
- **THEN** el endpoint responde `502 Bad Gateway` con `{code: "mp_unreachable", detail: "MercadoPago no respondió. Intentá de nuevo en un momento."}`
- **AND** en DB no existe ningún `Pedido` ni `Pago`

#### Scenario: MP responde con error sin status — sin pedido creado
- **WHEN** MP devuelve `response={}` y `error={"message": "...", "cause": [...]}`
- **THEN** el endpoint responde `502 Bad Gateway` con `code="mp_unreachable"` y `detail` incluyendo el mensaje y los causes de MP
- **AND** en DB no existe ningún `Pedido` ni `Pago`

---

### Requirement: POST /api/v1/checkout/pickup-efectivo crea pedido sin pago

El sistema SHALL exponer `POST /api/v1/checkout/pickup-efectivo` que crea un pedido para retiro en local con pago en efectivo (cobro en mostrador). El endpoint SHALL persistir `Pedido` + `DetallePedido` + `HistorialEstadoPedido` inicial en una UoW única, SIN crear ningún `Pago` asociado. El pedido nace en `PENDIENTE`.

#### Scenario: Pedido pickup+efectivo creado exitosamente
- **GIVEN** un cliente autenticado con rol `CLIENT` y productos válidos
- **WHEN** el cliente envía `POST /api/v1/checkout/pickup-efectivo` con `items`, `notas`
- **THEN** el endpoint responde `200 OK` con `{pedido_id}`
- **AND** en DB existe 1 fila en `orders` con `estado_codigo="PENDIENTE"`, `forma_pago_codigo="EFECTIVO"`, `direccion_entrega_id=NULL`, `direccion_snapshot=NULL`, `costo_envio=0.00`
- **AND** existen N filas en `order_items`, 1 fila en `order_state_history`
- **AND** NO existe ningún `Pago` asociado a este pedido

#### Scenario: Validación de stock falla — pedido no se crea
- **WHEN** el cliente envía un item con stock insuficiente
- **THEN** el endpoint responde `422 Unprocessable Entity` con detalle del producto sin stock
- **AND** en DB no existe ningún `Pedido` ni `DetallePedido`

#### Scenario: Pickup+efectivo no permite dirección
- **WHEN** el cliente envía body con `direccion_id` no-null
- **THEN** el endpoint responde `422 Unprocessable Entity` (validación Pydantic: este endpoint no acepta `direccion_id`)

---

### Requirement: Validación server-side de carrito (anti-smuggling D11)

El sistema SHALL validar todos los items del carrito server-side ANTES de cualquier llamada a MP o persistencia: existencia del producto (`productos.id`, no soft-deleted, `disponible=true`), stock suficiente (`SELECT FOR UPDATE` con lock pesimista dentro de la transacción), pertenencia de la dirección al usuario (si online + delivery). El sistema SHALL recalcular el `total` server-side a partir de los precios actuales en `productos` y el `costo_envio` fijo v1 (`50.00` con dirección, `0.00` sin dirección). Cualquier `total_estimado` enviado por el cliente SHALL ser ignorado.

#### Scenario: Stock insuficiente rechaza el checkout
- **WHEN** un cliente envía un item con `cantidad=10` para un producto con `stock=2`
- **THEN** el endpoint responde `422 Unprocessable Entity` con mensaje identificando el producto
- **AND** NO se llama a MP (en el caso online)
- **AND** no se crea ningún registro

#### Scenario: Total inyectado por el cliente es ignorado
- **WHEN** un cliente envía `"total": 0.01` en el body
- **THEN** el sistema responde `422 Unprocessable Entity` (Pydantic `extra="forbid"`)
- **AND** no se procesa el checkout

#### Scenario: Dirección de otro usuario responde 404 (anti-leak)
- **WHEN** el cliente A envía `direccion_id` que pertenece al cliente B
- **THEN** el endpoint responde `404 Not Found` con mensaje genérico
- **AND** NO se diferencia "no existe" de "pertenece a otro usuario"

#### Scenario: Producto inexistente responde 404
- **WHEN** el cliente envía `producto_id` que no existe o está soft-deleted
- **THEN** el endpoint responde `404 Not Found`
- **AND** no se crea ningún registro

---

### Requirement: Idempotencia con idempotency_key del cliente (D6, D12)

El sistema SHALL aceptar `idempotency_key` (UUID v4) en el body de `POST /api/v1/checkout/online` y SHALL:
1. Antes de llamar a MP, hacer lookup en `pagos` por `external_reference == idempotency_key`. Si existe un `Pago` con ese key, devolver la respuesta correspondiente del intento previo (no re-cobrar).
2. Pasar `idempotency_key` como header `X-Idempotency-Key` a la SDK de MP.
3. Persistir `pagos.external_reference = idempotency_key` (no `str(pedido_id)`).

#### Scenario: Retry con mismo idempotency_key devuelve el resultado anterior
- **GIVEN** un primer request con `idempotency_key="abc-123"` que aprobó con MP y creó pedido+pago
- **WHEN** el cliente reintenta con el mismo `idempotency_key="abc-123"` (e.g. por timeout en la red previa)
- **THEN** el endpoint responde `200 OK` con el mismo `{pedido_id, pago_id, mp_status, mp_id, status_detail}` del primer intento
- **AND** NO se hace una segunda llamada a MP
- **AND** NO se crea un nuevo pedido ni un nuevo Pago

#### Scenario: Retry con idempotency_key tras rejected previo
- **GIVEN** un primer request con `idempotency_key="abc-456"` que MP rechazó (no se creó ningún registro)
- **WHEN** el cliente reintenta con el mismo `idempotency_key="abc-456"`
- **THEN** el endpoint hace una nueva llamada a MP con el mismo `X-Idempotency-Key` (MP devuelve el mismo resultado)
- **AND** la respuesta del endpoint refleja el resultado de MP

#### Scenario: idempotency_key faltante o inválido es rechazado
- **WHEN** el cliente envía un body sin `idempotency_key` o con un valor que no es UUID4
- **THEN** el endpoint responde `422 Unprocessable Entity` (validación Pydantic)

---

### Requirement: Schemas Pydantic estrictos (extra="forbid")

El sistema SHALL declarar `CheckoutOnlineRequest`, `CheckoutPickupEfectivoRequest`, `CheckoutItem`, `CheckoutOnlineResponse`, `CheckoutPickupEfectivoResponse` y `CheckoutErrorResponse` en `backend/features/checkout/schemas.py`. Todos los request schemas SHALL declarar `model_config = ConfigDict(extra="forbid")` para rechazar campos no declarados (anti-smuggling).

#### Scenario: Campo no declarado rechazado en CheckoutOnlineRequest
- **WHEN** el cliente envía un body con un campo `"foo": "bar"` no declarado
- **THEN** el endpoint responde `422 Unprocessable Entity`

#### Scenario: Item con personalizacion negativa rechazado
- **WHEN** un item del request incluye `"personalizacion": [0, -1]`
- **THEN** el endpoint responde `422 Unprocessable Entity`

#### Scenario: items vacío rechazado
- **WHEN** el cliente envía `"items": []`
- **THEN** el endpoint responde `422 Unprocessable Entity` con error `min_length=1`

---

### Requirement: response_model declarado en el router para documentación OpenAPI

El router SHALL declarar `response_model=CheckoutOnlineResponse` y `response_model=CheckoutPickupEfectivoResponse` en los respectivos endpoints, y SHALL documentar los códigos de error vía `responses={...}` con sus schemas (`CheckoutErrorResponse` para `402`/`422`, payload del handler global para `502`).

#### Scenario: OpenAPI documenta los responses
- **WHEN** se inspecciona `/docs` o `/openapi.json`
- **THEN** el endpoint `POST /checkout/online` declara response `200` con `CheckoutOnlineResponse`, response `402` con `CheckoutErrorResponse`, response `422` con error de validación, response `502` con `code="mp_unreachable"`

---

### Requirement: Autenticación CLIENT obligatoria en ambos endpoints

El sistema SHALL requerir autenticación válida (JWT access token) y rol `CLIENT` para invocar ambos endpoints. Requests sin token o sin rol CLIENT SHALL ser rechazados (`401` y `403` respectivamente).

#### Scenario: Sin Authorization header
- **WHEN** se envía `POST /checkout/online` o `POST /checkout/pickup-efectivo` sin header `Authorization`
- **THEN** el endpoint responde `401 Unauthorized`

#### Scenario: Usuario sin rol CLIENT
- **WHEN** un usuario con solo rol `ADMIN` (sin `CLIENT`) intenta checkout
- **THEN** el endpoint responde `403 Forbidden`
- **AND** no se crea ningún registro

---

### Requirement: Snapshots inmutables al crear el pedido

El sistema SHALL capturar y persistir snapshots inmutables al crear el pedido vía cualquiera de los dos endpoints de checkout: `precio_snapshot` y `nombre_snapshot` en cada `DetallePedido`, y `direccion_snapshot` en `Pedido` (cuando aplica). Mismo comportamiento que en el flow viejo de `POST /pedidos/`.
