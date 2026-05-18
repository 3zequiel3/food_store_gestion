### Requirement: Toaster provider mounted at app root
The app SHALL mount the `<Toaster />` component from `sonner` at the root level so that toast notifications render in all routes, including the checkout flow.

#### Scenario: Toast renders after order creation error
- **WHEN** `useCreateOrder` calls `toast.error(...)` after a failed order creation
- **THEN** the toast notification SHALL be visible to the user

### Requirement: OrderConfirmationPage route registered
The router SHALL register the route `/cliente/pedidos/:id/confirmacion` pointing to `OrderConfirmationPage`.

#### Scenario: Navigate to confirmation after order creation
- **WHEN** `useCreateOrder` succeeds and calls `navigate('/cliente/pedidos/:id/confirmacion', { state: { pedido, cartItems } })`
- **THEN** `OrderConfirmationPage` SHALL render with the pedido and cartItems from location state


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

### Requirement: statusDetailMessages mapea los status_detail más comunes de MP a mensajes en castellano rioplatense

El archivo `frontend/src/features/payments/lib/statusDetailMessages.ts` SHALL exportar:

- Un objeto `statusDetailMessages: Record<string, string>` con entradas para al menos los siguientes `status_detail`: `cc_rejected_insufficient_amount`, `cc_rejected_bad_filled_security_code`, `cc_rejected_bad_filled_card_number`, `cc_rejected_bad_filled_date`, `cc_rejected_other_reason`, `cc_rejected_call_for_authorize`, `cc_rejected_high_risk`, `pending_review_manual`, `pending_waiting_payment`, `accredited`.
- Una función `friendlyMessageFor(statusDetail: string | null | undefined): string` que devuelve el mapeo si existe, el `status_detail` crudo si no existe pero es truthy, y `"Sin información adicional."` si es null/undefined.

#### Scenario: Mensaje conocido se traduce

- **WHEN** se llama a `friendlyMessageFor("cc_rejected_insufficient_amount")`
- **THEN** devuelve `"Saldo insuficiente. Probá con otra tarjeta."`

#### Scenario: Mensaje desconocido devuelve el status_detail crudo

- **WHEN** se llama a `friendlyMessageFor("cc_some_unknown_detail")`
- **THEN** devuelve `"cc_some_unknown_detail"`

#### Scenario: Mensaje null devuelve fallback

- **WHEN** se llama a `friendlyMessageFor(null)`
- **THEN** devuelve `"Sin información adicional."`

#### Scenario: Mensaje undefined devuelve fallback

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

#### Scenario: Mensaje undefined devuelve fallback

- **WHEN** se llama a `friendlyMessageFor(undefined)`
- **THEN** devuelve `"Sin información adicional."`

### Requirement: PaymentPage maneja onPending mostrando un estado en revisión

`PaymentPage` SHALL pasar a `<PaymentForm />` un callback `onPending` que renderiza dentro de la página un panel "en revisión" con:

- Ícono visual de espera (e.g. `lucide-react` `Clock`).
- El `friendlyMessage` recibido.
- Texto secundario indicando que se avisará por mail al confirmarse.
- Un botón "Ver estado del pedido" que navega a `/cliente/pedidos/:id/confirmacion`.

`PaymentPage` MUST NOT redirigir automáticamente — el usuario decide cuándo salir del flow.

#### Scenario: PaymentForm dispara onPending y se muestra el panel

- **GIVEN** el usuario está en `/cliente/pedidos/42/pago`
- **WHEN** `PaymentForm` invoca `onPending(response, "Tu pago está en revisión...")`
- **THEN** `PaymentPage` renderiza un panel con el mensaje y un botón "Ver estado del pedido"
- **AND** no ocurre navegación automática

#### Scenario: Botón "Ver estado del pedido" navega a la confirmación

- **GIVEN** el panel de pending está visible
- **WHEN** el usuario clickea "Ver estado del pedido"
- **THEN** el router navega a `/cliente/pedidos/42/confirmacion`

### Requirement: PaymentResponse incluye pago_id

El tipo `PaymentResponse` en `payments.types.ts` SHALL incluir el campo opcional `pago_id?: number` que refleja el ID interno del `Pago` devuelto por el backend.

#### Scenario: pago_id presente en la respuesta

- **GIVEN** el backend devuelve `{mp_status, mp_id, status_detail, pago_id: 7}`
- **WHEN** el front parsea el response como `PaymentResponse`
- **THEN** `response.pago_id` es `7` y TypeScript lo tipa como `number | undefined`

### Requirement: MercadoPago Checkout Pro research document
The system SHALL include a research document at `docs/mercadopago-checkout-pro-research.md` that covers: preference creation flow, webhook IPN format, return URL behavior, notification polling strategy, and current integration gaps. The document SHALL be dated and link to official MercadoPago documentation.

> **ADDED (ui-sidebar-user-and-ingredient-fix)**: Research document created — covers preference creation, webhook IPN, return URL behavior, polling strategy, and integration gaps.

#### Scenario: Research document exists and is findable
- **WHEN** a developer looks for MercadoPago integration documentation
- **THEN** `docs/mercadopago-checkout-pro-research.md` exists and covers preference creation, webhooks, return URLs, and polling

#### Scenario: Document links to official MP docs
- **WHEN** the research document is read
- **THEN** it contains at least one link to the official MercadoPago Checkout Pro documentation
