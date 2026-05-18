## ADDED Requirements

### Requirement: PaymentForm clasifica el resultado de MP en cuatro categorías

El componente `PaymentForm` SHALL distinguir el resultado de `createInlinePayment` en cuatro categorías según `response.mp_status`:

- **Terminal success**: `approved` → invoca `onSuccess(response)`.
- **Pending review**: `pending`, `in_process`, `authorized` → invoca `onPending(response, friendlyMessage)`.
- **Terminal failure**: `rejected`, `cancelled` → invoca `onError(friendlyMessage)`.
- **Resultado inesperado** (cualquier otro `mp_status`): invoca `onError(response.status_detail ?? \`Resultado inesperado: ${response.mp_status}\`)`.

`friendlyMessage` SHALL derivarse de `status_detail` mediante la función `friendlyMessageFor(...)` exportada desde `statusDetailMessages.ts`.

#### Scenario: Pago aprobado dispara onSuccess

- **GIVEN** el componente `PaymentForm` con props `onSuccess`, `onPending`, `onError`
- **WHEN** `createInlinePayment` resuelve con `{mp_status: "approved", mp_id: "1", status_detail: "accredited", pago_id: 7}`
- **THEN** `onSuccess` es invocado con el response completo
- **AND** ni `onPending` ni `onError` son invocados

#### Scenario: Pago pending dispara onPending con mensaje user-friendly

- **GIVEN** el componente `PaymentForm`
- **WHEN** `createInlinePayment` resuelve con `{mp_status: "pending", status_detail: "pending_review_manual", ...}`
- **THEN** `onPending` es invocado con el response y el mensaje `"Tu pago está en revisión. Te avisaremos cuando se confirme."`
- **AND** ni `onSuccess` ni `onError` son invocados

#### Scenario: Pago in_process dispara onPending

- **GIVEN** el componente `PaymentForm`
- **WHEN** `createInlinePayment` resuelve con `{mp_status: "in_process", status_detail: "pending_waiting_payment", ...}`
- **THEN** `onPending` es invocado con el response y un mensaje user-friendly

#### Scenario: Pago rejected con status_detail mapeado

- **GIVEN** el componente `PaymentForm`
- **WHEN** `createInlinePayment` resuelve con `{mp_status: "rejected", status_detail: "cc_rejected_insufficient_amount", ...}`
- **THEN** `onError` es invocado con el mensaje `"Saldo insuficiente. Probá con otra tarjeta."`

#### Scenario: Pago rejected con status_detail no mapeado

- **GIVEN** el componente `PaymentForm`
- **WHEN** `createInlinePayment` resuelve con `{mp_status: "rejected", status_detail: "cc_some_new_detail_unknown", ...}`
- **THEN** `onError` es invocado con el `status_detail` crudo (`"cc_some_new_detail_unknown"`) como fallback

#### Scenario: Pago cancelled dispara onError

- **GIVEN** el componente `PaymentForm`
- **WHEN** `createInlinePayment` resuelve con `{mp_status: "cancelled", status_detail: null, ...}`
- **THEN** `onError` es invocado con `"Sin información adicional."` (fallback de `friendlyMessageFor`)

#### Scenario: mp_status inesperado dispara onError genérico

- **GIVEN** el componente `PaymentForm`
- **WHEN** `createInlinePayment` resuelve con `{mp_status: "refunded", status_detail: null, ...}`
- **THEN** `onError` es invocado con `"Resultado inesperado: refunded"`

#### Scenario: Error de red sigue cayendo al catch

- **GIVEN** el componente `PaymentForm`
- **WHEN** `createInlinePayment` rechaza con `ApiError` (502 mp_unreachable u otro)
- **THEN** `onError` es invocado con el mensaje del error
- **AND** ni `onSuccess` ni `onPending` son invocados

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

## REMOVED Requirements

### Requirement: Payments feature folder

**Reason**: La sub-lista de archivos exigía explícitamente `hooks/useInitPayment.ts` como mutation hook para "iniciar el pago", que era parte del flow wallet legacy ya superado por el flow Checkout API inline (`SecureCardForm` + `createInlinePayment`). El hook `useInitPayment` no tiene consumidores reales y manda un payload incompleto (`{pedido_id}`) al endpoint que requiere 7 campos. La requirement original genera ruido y código muerto.

**Migration**:

- El folder `features/payments/` sigue existiendo y se mantienen `services/payments.service.ts` (con `createInlinePayment` y `getInlinePaymentStatus`), `hooks/usePaymentByOrder.ts`, `types/payments.types.ts` y `components/PaymentForm.tsx` + `SecureCardForm.tsx`.
- Se ELIMINAN: `hooks/useInitPayment.ts` (completo), la función `initiatePayment` de `services/payments.service.ts` (manda payload incompleto), y la `interface PagoCreate { pedido_id: number }` legacy de `types/payments.types.ts`.
- El nuevo contrato del backend (`PagoCreateResponse` con `pago_id`) queda reflejado en `PaymentResponse` (que ya existe) con el campo `pago_id?: number` agregado.

### Requirement: PaymentPage initiates MercadoPago payment

**Reason**: La requirement original describía el flow Checkout Pro con redirect a `init_point`. El flow actual es Checkout API inline (`SecureCardForm` que genera `card_token`, `POST /api/v1/pagos/` con el token, sin redirect). El behaviour declarado (llamar POST con `{pedido_id}` y redirigir a `init_point`) ya no es válido.

**Migration**: el behaviour vigente de `PaymentPage` queda cubierto por la nueva requirement "PaymentPage maneja onPending mostrando un estado en revisión" y por las requirements existentes del Checkout API inline (resultado approved → onSuccess → confirmación). Cualquier referencia a `init_point` queda obsoleta y se elimina junto con el `interface PagoCreate` legacy.

### Requirement: useInitPayment redirects on success

**Reason**: Sub-scenario de "Payments feature folder" — el hook `useInitPayment` se elimina por completo. No queda código que redirija a `init_point`.

**Migration**: ninguna acción adicional — el flow Checkout API inline no usa `init_point`. El éxito se maneja vía `onSuccess` de `PaymentForm` y la navegación la decide `PaymentPage`.
