## MODIFIED Requirements

### Requirement: PaymentForm clasifica el resultado de MP en cuatro categorías

El componente `PaymentForm` SHALL distinguir el resultado de la operación de pago en cuatro categorías. **Cambio en `checkout-pay-first-flow`**: el flow de pago se ejecuta ahora **dentro** del endpoint `POST /api/v1/checkout/online`, no en un endpoint separado `POST /api/v1/pagos/`. Por lo tanto el `PaymentForm` ya no invoca `createInlinePayment` (que llamaba a `POST /pagos/`) sino que produce un `card_token` (vía MP card brick o flow inline) y lo entrega al `CheckoutPage` para que éste lo incluya en el body de `POST /api/v1/checkout/online`.

Las cuatro categorías ahora se distinguen según la **response del checkout completo**:

- **Terminal success**: response `200 OK` con `mp_status="approved"` → `CheckoutPage` redirige a confirmación.
- **Terminal failure**: response `402` con `code="payment_rejected"` o `code="payment_cancelled"` → `CheckoutPage` muestra toast con `friendlyMessageFor(status_detail)` y permite reintentar.
- **Pending review (no aceptado en modo estricto D3)**: response `402` con `code="payment_pending_not_accepted"` → `CheckoutPage` muestra toast con mensaje explicativo del modo estricto. NO existe la categoría "onPending" del flow viejo porque el backend nunca persiste pagos `pending`/`in_process` (modo estricto).
- **Upstream error**: response `502` con `code="mp_unreachable"` → `CheckoutPage` muestra toast invitando a reintentar.

`friendlyMessage` SHALL derivarse de `status_detail` mediante la función `friendlyMessageFor(...)` exportada desde `statusDetailMessages.ts` (sin cambios respecto al spec original).

#### Scenario: Pago aprobado redirige a confirmación
- **GIVEN** `PaymentForm` produjo un `card_token` válido y `CheckoutPage` invocó `POST /checkout/online`
- **WHEN** el backend responde `200 OK` con `mp_status="approved"`
- **THEN** `CheckoutPage` navega a `/cliente/pedidos/<pedido_id>/confirmacion`
- **AND** el `cartStore` se limpia

#### Scenario: Pago rechazado muestra toast con mensaje user-friendly
- **WHEN** el backend responde `402` con `code="payment_rejected"`, `status_detail="cc_rejected_insufficient_amount"`
- **THEN** `CheckoutPage` muestra toast con "Saldo insuficiente. Probá con otra tarjeta."
- **AND** el usuario permanece en `CheckoutPage` con el `idempotency_key` activo para reintentar

#### Scenario: Pago pending dispara toast de modo estricto
- **WHEN** el backend responde `402` con `code="payment_pending_not_accepted"`
- **THEN** `CheckoutPage` muestra toast "Tu pago quedó en revisión y no podemos confirmar el pedido. Probá con otra tarjeta o elegí pago en efectivo al retirar."
- **AND** ningún pedido ni Pago existe en la DB

#### Scenario: MP unreachable permite reintentar
- **WHEN** el backend responde `502` con `code="mp_unreachable"`
- **THEN** `CheckoutPage` muestra toast "MercadoPago no respondió. Intentá de nuevo en un momento."
- **AND** el botón "Confirmar y pagar" se rehabilita
- **AND** el `idempotency_key` se preserva para el reintento

#### Scenario: Status inesperado dispara toast genérico
- **WHEN** el backend responde `402` con `code="payment_unexpected_status"`, `mp_status="refunded"` (u otro no mapeado)
- **THEN** `CheckoutPage` muestra toast con el `status_detail` crudo como fallback

---

### Requirement: PaymentResponse incluye pago_id

El tipo `CheckoutOnlineResponse` en `checkout.types.ts` (nuevo archivo del feature `checkout` en frontend) SHALL incluir los campos `pedido_id: number`, `pago_id: number`, `mp_status: "approved"` (literal), `mp_id: string`, `status_detail: string`. El tipo viejo `PaymentResponse` se mantiene solo si `PaymentForm` se sigue exportando como componente reutilizable; en ese caso, `PaymentForm` ya no produce un `PaymentResponse` sino un `card_token`.

**Migration**: si `PaymentResponse` sigue en uso, mantenerlo como contrato del componente `PaymentForm` (qué reporta hacia su parent). Si nadie lo consume tras el refactor, eliminarlo.

#### Scenario: CheckoutOnlineResponse tipa correctamente la response
- **GIVEN** el backend devuelve `{pedido_id: 42, pago_id: 7, mp_status: "approved", mp_id: "MP-123", status_detail: "accredited"}`
- **WHEN** el front parsea la respuesta como `CheckoutOnlineResponse`
- **THEN** TypeScript tipa cada campo correctamente
- **AND** `pedido_id` y `pago_id` son `number` (no `undefined`)

---

## REMOVED Requirements

### Requirement: PaymentPage maneja onPending mostrando un estado en revisión

**Reason**: en `checkout-pay-first-flow`, el modo estricto D3 elimina el caso `onPending` porque el backend nunca persiste pagos `pending`/`in_process` ni crea pedidos para ellos. Si MP devuelve `pending`, el endpoint responde `402` con `code="payment_pending_not_accepted"` y el usuario permanece en `CheckoutPage` con un toast. NO existe una pantalla intermedia "en revisión" ni un panel renderizado dentro de `PaymentPage`. La pantalla `PaymentPage` separada (`/cliente/pedidos/:id/pago`) deja de existir en el flow nuevo — el pago vive inline dentro de `CheckoutPage`.

**Migration**: el frontend elimina el archivo `frontend/src/pages/client/PaymentPage.tsx` (y sus tests). La ruta `/cliente/pedidos/:id/pago` se elimina del router. El callback `onPending` ya no es necesario porque `PaymentForm` no clasifica resultados — los clasifica `CheckoutPage` a partir de la response del backend.
