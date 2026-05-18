## REMOVED Requirements

### Requirement: POST /api/v1/pagos/ devuelve 200 OK con el resultado de MP como dato

**Reason**: el endpoint `POST /api/v1/pagos/` se elimina del backend. La razón es estructural: el flow nuevo (`checkout-pay-first-flow`) impide que exista un Pedido sin Pago aprobado o sin contexto pickup+efectivo. Para lograrlo, el cobro y la creación del pedido se hacen en una sola operación atómica (`POST /api/v1/checkout/online`). No hay un punto en el tiempo donde "el pedido existe pero todavía no se intentó cobrar" — esa ventana es exactamente la que generaba pedidos huérfanos.

Adicionalmente, el modo estricto D3 del nuevo flow es **incompatible** con el contrato anterior "200 OK con cualquier mp_status como dato": en el flow nuevo, cualquier `mp_status != "approved"` NO crea pedido y devuelve `402` (o `422`). Persistir `Pago` con `mp_status="rejected"` o `"pending"` ya no aporta valor — sin Pedido asociado, esos `Pago` son huérfanos también.

**Migration**: el cliente migra a `POST /api/v1/checkout/online`. Ver capability `checkout` para el contrato nuevo. El front (único cliente) actualiza su `payments.service.ts` o lo elimina, según convenga. La spec `checkout/spec.md` cubre los casos `approved`/`rejected`/`pending`/`cancelled`/`unreachable`.

---

### Requirement: POST /api/v1/pagos/ devuelve 502 mp_unreachable cuando MercadoPago no responde con status

**Reason**: el endpoint `POST /api/v1/pagos/` se elimina. El comportamiento `502 mp_unreachable` se traslada literalmente al nuevo endpoint `POST /api/v1/checkout/online`, con la misma semántica: si MP no contesta, no se crea ningún registro y se devuelve `502` con `code="mp_unreachable"`.

**Migration**: el cliente espera `502 mp_unreachable` ahora desde `/checkout/online`, no desde `/pagos/`.

---

### Requirement: PagoCreateResponse declarado como response_model en el router

**Reason**: el endpoint que tenía `response_model=PagoCreateResponse` se elimina. El nuevo endpoint `POST /api/v1/checkout/online` declara `response_model=CheckoutOnlineResponse`, con campos similares (`mp_status`, `mp_id`, `status_detail`, `pago_id`) más el `pedido_id` nuevo.

**Migration**: el schema `PagoCreateResponse` puede eliminarse del backend si nadie más lo consume. El schema `CheckoutOnlineResponse` lo reemplaza.

---

### Requirement: El Pago se persiste con el mp_status real devuelto por MP

**Reason**: la lógica de "persistir Pago con `mp_status` real (`approved`, `pending`, `rejected`, etc.) en un solo INSERT" deja de aplicar en el flow nuevo, porque el modo estricto D3 SOLO persiste cuando `mp_status="approved"`. Los demás status no generan ningún registro.

**Migration**: en el `CheckoutService`, el `INSERT` del `Pago` ocurre solo dentro del happy path `mp_status="approved"`, dentro de la UoW que también crea el Pedido. El `mp_status` persistido siempre será `"approved"` en el flow online.

---

### Requirement: La transición PENDIENTE→CONFIRMADO falla con logging, no silenciosamente

**Reason**: la transición automática `PENDIENTE → CONFIRMADO` ya NO ocurre en el flow principal del checkout. En el flow nuevo, después de un pago aprobado, el pedido nace en `PENDIENTE` y permanece ahí hasta que el local lo acepta (transición manual por PEDIDOS/ADMIN). El webhook MP mantiene la capacidad de disparar la transición como red de seguridad, pero ya no es parte del happy path del checkout online.

**Migration**: el comportamiento "logger.exception si la transición falla" sigue siendo válido pero migra al `webhook handler` del `PaymentService` (no al `CheckoutService`). El nuevo `CheckoutService` NO invoca `transicionar_estado` — el pedido se crea directamente en `PENDIENTE` y se queda ahí.

---

## ADDED Requirements

### Requirement: GET /api/v1/pagos/pedido/{pedido_id} se mantiene sin cambios

El sistema SHALL mantener `GET /api/v1/pagos/pedido/{pedido_id}` sin cambios funcionales. Devuelve el `PagoRead` del Pago asociado al pedido (si existe). En el flow nuevo, este endpoint sigue siendo útil para:
- Mostrar al cliente el `mp_status` y `status_detail` del pago de un pedido específico.
- Soporte/auditoría operativa (rol PEDIDOS o ADMIN consultando estado de pagos).

#### Scenario: GET devuelve el Pago aprobado del pedido
- **GIVEN** un pedido creado via `POST /checkout/online` con `mp_status="approved"`
- **WHEN** el cliente (o un PEDIDOS/ADMIN) consulta `GET /api/v1/pagos/pedido/<pedido_id>`
- **THEN** la respuesta es `200 OK` con `PagoRead` (`pago_id`, `mp_status="approved"`, `mp_payment_id`, `external_reference=<idempotency_key>`, `pedido_id`, `created_at`)

#### Scenario: GET devuelve 404 para pedido pickup+efectivo (no tiene Pago)
- **GIVEN** un pedido creado via `POST /checkout/pickup-efectivo` (sin Pago)
- **WHEN** se consulta `GET /api/v1/pagos/pedido/<pedido_id>`
- **THEN** la respuesta es `404 Not Found` (no hay Pago asociado)

---

### Requirement: POST /api/v1/pagos/webhook/mercadopago se mantiene como red de seguridad

El sistema SHALL mantener `POST /api/v1/pagos/webhook/mercadopago` sin cambios funcionales. Recibe notificaciones IPN de MP y reconcilia el estado del Pago + transición del Pedido. En el flow nuevo, este endpoint tiene **menos casos efectivos** porque la mayoría de los Pagos ya existen en la DB con `mp_status="approved"` cuando llega el webhook (creados atómicamente por el checkout). El webhook funciona como red de seguridad para:
1. Casos donde la UoW del checkout falló post-cobro (MP aprobó pero la DB no persistió) — el webhook puede reconciliar usando `external_reference == idempotency_key`.
2. Pagos retrasados que MP confirma horas después (raros con el modo estricto, pero posibles).
3. Notificaciones idempotentes que MP repite.

**Cambio en la lógica de reconciliación**: el lookup ya NO es `pedido_id = int(external_reference)`. Ahora es `pago = repo.find_by_external_reference(idempotency_key)` → si existe, `pedido_id = pago.pedido_id`; si no existe, registrar incidente operativo (cobro sin persistencia).

#### Scenario: Webhook idempotente sobre Pago ya aprobado
- **GIVEN** un Pago en `mp_status="approved"` creado por el checkout
- **WHEN** llega un webhook duplicado para el mismo `mp_payment_id`
- **THEN** el webhook responde `200 OK` sin cambios — idempotencia preservada (`InvalidStateTransitionError` 409 manejado internamente como no-op)

#### Scenario: Webhook reconcilia incidente "MP cobró, DB no persistió"
- **GIVEN** el checkout falló post-cobro (UoW rollback con MP aprobado) y no existe Pago en DB con ese `external_reference`
- **WHEN** llega el webhook reportando `payment.status="approved"` y `external_reference="<idempotency_key>"`
- **THEN** el webhook detecta el incidente, intenta reconciliar (creando retroactivamente Pedido+Pago si la información del request original puede reconstruirse, o registrando el incidente para resolución manual si no se puede)
- **AND** se emite un log de nivel `ERROR` o `WARNING` con `mp_payment_id`, `idempotency_key`, y diagnóstico

> Nota: la implementación exacta de la reconciliación retroactiva queda fuera del alcance estricto de este change. La regla mínima es: el webhook NO debe romper, y debe registrar suficiente información para que un operador humano pueda resolver el caso. Una implementación más completa (recuperación automática) puede hacerse en un change futuro.

#### Scenario: Webhook con external_reference no encontrado registra incidente
- **GIVEN** un webhook con `external_reference="<uuid>"` que no existe en `pagos`
- **WHEN** el handler procesa el webhook
- **THEN** el handler responde `200 OK` (no debe fallar — MP reintentaría)
- **AND** se emite un log `WARNING` con `external_reference`, `mp_payment_id` y `payment.status` para diagnóstico operativo
