## ADDED Requirements

### Requirement: Crear preferencia de pago en MercadoPago

El sistema SHALL exponer `POST /api/v1/pagos` (autenticado, rol CLIENT) que crea una preferencia/orden en MercadoPago para un pedido PENDIENTE del cliente autenticado. SHALL registrar un registro `Pago` en BD con `idempotency_key` UUID4 único, `monto` igual al `total` del pedido, `forma_pago_codigo` del pedido, y `mp_status = "pending"`. SHALL retornar un `PagoRead` con `id`, `pedido_id`, `monto`, `mp_status` e `init_point` (URL de checkout de MP).

#### Scenario: Cliente inicia pago de pedido propio en estado PENDIENTE

- **WHEN** un cliente autenticado envía `POST /api/v1/pagos` con `{ "pedido_id": <id> }` y el pedido existe, pertenece al cliente y está en estado `PENDIENTE`
- **THEN** el sistema responde `201 Created` con `PagoRead` incluyendo `id`, `pedido_id`, `mp_status = "pending"` e `init_point` con URL válida de MercadoPago
- **AND** en BD existe una fila en `payments` con `pedido_id` correcto, `idempotency_key` único (UUID4), `monto` igual al total del pedido y `mp_status = "pending"`

#### Scenario: Pedido no existe o no pertenece al cliente

- **WHEN** un cliente envía `POST /api/v1/pagos` con un `pedido_id` que no existe o que pertenece a otro cliente
- **THEN** el sistema responde `403 Forbidden`
- **AND** no se crea ningún registro en `payments`

#### Scenario: Pedido no está en estado PENDIENTE

- **WHEN** un cliente envía `POST /api/v1/pagos` con un `pedido_id` cuyo pedido está en estado distinto de `PENDIENTE` (ej. `CONFIRMADO`, `CANCELADO`)
- **THEN** el sistema responde `409 Conflict` con detalle del estado actual
- **AND** no se crea ningún registro en `payments`

#### Scenario: Pedido con pago aprobado o pendiente previo no admite nuevo intento

- **WHEN** un cliente envía `POST /api/v1/pagos` para un pedido que ya tiene un `Pago` con `mp_status in ("approved", "pending", "in_process")`
- **THEN** el sistema responde `409 Conflict`
- **AND** no se crea un nuevo registro en `payments`

#### Scenario: Reintento permitido tras pago rechazado

- **WHEN** un cliente envía `POST /api/v1/pagos` para un pedido PENDIENTE cuyo último `Pago` tiene `mp_status = "rejected"` (o `"cancelled"`)
- **THEN** el sistema responde `201 Created` con un nuevo `PagoRead`
- **AND** en BD existe un nuevo registro en `payments` con nuevo `idempotency_key` distinto al anterior
- **AND** el registro anterior de pago rechazado permanece en BD (historial preservado, RN-PA08)

---

### Requirement: Procesar webhook IPN de MercadoPago con idempotencia

El sistema SHALL exponer `POST /api/v1/pagos/webhook/mercadopago` (sin autenticación de usuario) que recibe notificaciones IPN de MercadoPago. SHALL responder `HTTP 200` de inmediato. SHALL verificar el estado real del pago consultando la API de MercadoPago (no confiar solo en el payload). SHALL actualizar `Pago.mp_status` según el estado verificado. El procesamiento SHALL ser idempotente: recibir la misma notificación múltiples veces NO debe producir efectos duplicados.

#### Scenario: Webhook approved — transición automática a CONFIRMADO

- **WHEN** se recibe `POST /api/v1/pagos/webhook/mercadopago` con `data.id` de un pago y la API de MP devuelve `status = "approved"` al verificar
- **THEN** el sistema responde `200 OK`
- **AND** en BD el `Pago` correspondiente tiene `mp_status = "approved"`
- **AND** el pedido asociado tiene `estado_codigo = "CONFIRMADO"`
- **AND** existe una fila en `order_state_history` con `estado_anterior_codigo = "PENDIENTE"`, `estado_nuevo_codigo = "CONFIRMADO"` y `cambiado_por_id = NULL` (actor SISTEMA)

#### Scenario: Webhook rejected — pedido permanece PENDIENTE

- **WHEN** se recibe webhook y la API de MP devuelve `status = "rejected"`
- **THEN** el sistema responde `200 OK`
- **AND** en BD el `Pago` tiene `mp_status = "rejected"`
- **AND** el pedido permanece en `estado_codigo = "PENDIENTE"`

#### Scenario: Webhook pending/in_process — solo actualiza estado del pago

- **WHEN** se recibe webhook y la API de MP devuelve `status = "pending"` o `"in_process"`
- **THEN** el sistema responde `200 OK`
- **AND** en BD el `Pago` tiene `mp_status` actualizado al valor verificado
- **AND** el pedido permanece en `estado_codigo = "PENDIENTE"`

#### Scenario: Webhook duplicado no produce efectos dobles

- **WHEN** se recibe el mismo webhook (mismo `data.id` de pago) por segunda vez, siendo que el primero ya fue procesado como `approved`
- **THEN** el sistema responde `200 OK`
- **AND** el pedido sigue en `CONFIRMADO` sin cambios
- **AND** NO se crea una nueva fila en `order_state_history`

#### Scenario: Pago no encontrado en BD al procesar webhook

- **WHEN** se recibe webhook con `data.id` que no corresponde a ningún `mp_payment_id` en BD
- **THEN** el sistema responde `200 OK` (para que MP no reintente indefinidamente)
- **AND** no se produce ningún cambio en BD

---

### Requirement: Consultar estado de pago de un pedido propio

El sistema SHALL exponer `GET /api/v1/pagos/pedido/{pedido_id}` (autenticado, rol CLIENT) que retorna el último `Pago` asociado al pedido. Solo el propietario del pedido puede consultarlo.

#### Scenario: Cliente consulta estado de pago de su pedido

- **WHEN** un cliente autenticado envía `GET /api/v1/pagos/pedido/{pedido_id}` y el pedido pertenece al cliente y tiene al menos un `Pago`
- **THEN** el sistema responde `200 OK` con el `Pago` más reciente: `id`, `pedido_id`, `monto`, `mp_status`, `creado_en`, `actualizado_en`

#### Scenario: Pedido sin pagos aún

- **WHEN** el cliente consulta el estado de pago de un pedido propio que no tiene ningún registro en `payments`
- **THEN** el sistema responde `404 Not Found`

#### Scenario: Pedido de otro cliente

- **WHEN** el cliente consulta el estado de pago de un pedido que no le pertenece
- **THEN** el sistema responde `403 Forbidden`
