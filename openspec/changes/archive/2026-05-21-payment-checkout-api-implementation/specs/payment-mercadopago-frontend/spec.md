# Delta for payment-mercadopago-frontend

## ADDED Requirements

### Requirement: SecureCardForm component for inline card input

The system SHALL provide a `SecureCardForm` component that mounts MercadoPago.js Secure Fields (iframes) for card number, expiration date, and CVV. On submit, it calls `mp.cardToken.create()` and returns the token to the parent.

#### Scenario: Render Secure Fields iframes

- **GIVEN** the user selects "Nueva Tarjeta"
- **WHEN** `SecureCardForm` mounts
- **THEN** three iframe fields are rendered (card number, expiry, CVV)
- **AND** no raw card data enters the DOM or JavaScript context

#### Scenario: Tokenize card on submit

- **GIVEN** user has filled all Secure Fields
- **WHEN** user submits the form
- **THEN** `mp.cardToken.create()` is called
- **AND** on success, the `card_token` is passed to the parent callback

#### Scenario: Tokenization error

- **GIVEN** `mp.cardToken.create()` fails (invalid card, network error)
- **WHEN** the error is returned
- **THEN** `SecureCardForm` displays a user-facing error message
- **AND** the form remains editable for retry

### Requirement: Inline payment completion without redirect

When the backend returns `mp_status: 'approved'` from `POST /api/v1/pagos`, the system SHALL navigate directly to order confirmation WITHOUT redirecting to MercadoPago's domain.

#### Scenario: Approved payment navigates to confirmation

- **GIVEN** user submits payment with card_token
- **WHEN** `POST /api/v1/pagos` returns `201` with `mp_status: 'approved'`
- **THEN** PaymentPage navigates to `/cliente/pedidos/:id/confirmacion`
- **AND** no `window.location.href` redirect to external URL occurs

#### Scenario: Rejected payment shows error with retry

- **GIVEN** user submits payment with card_token
- **WHEN** `POST /api/v1/pagos` returns `mp_status: 'rejected'`
- **THEN** PaymentPage displays a rejection message
- **AND** provides a button to retry with a different card

#### Scenario: Pending payment shows waiting state

- **GIVEN** user submits payment with card_token
- **WHEN** `POST /api/v1/pagos` returns `mp_status: 'pending'`
- **THEN** PaymentPage displays a pending status message
- **AND** polls or waits for webhook-based status update

### Requirement: PaymentPage detects Checkout API vs Checkout Pro

PaymentPage SHALL detect whether the backend response contains `mp_status` (API flow) or `init_point` (Pro flow) and act accordingly.

#### Scenario: API response with mp_status

- **WHEN** `POST /api/v1/pagos` response contains `mp_status` field
- **THEN** PaymentPage handles the payment inline (no redirect)

#### Scenario: Pro response with init_point (backward compat)

- **WHEN** `POST /api/v1/pagos` response contains `init_point` and no `mp_status`
- **THEN** PaymentPage redirects to `init_point` via `window.location.href`

## MODIFIED Requirements

### Requirement: PaymentPage initiates MercadoPago payment

The system SHALL provide a `PaymentPage` at `/cliente/pedidos/:id/pago` that:
1. Loads saved cards via `GET /api/v1/metodos-pago`.
2. If saved cards exist, displays a card selector + "Nueva Tarjeta" option.
3. On "Nueva Tarjeta", renders `SecureCardForm` for inline tokenization.
4. On card selection or tokenization, calls `POST /api/v1/pagos` with `{ pedido_id, card_token, payment_method_id, installments }`.
5. Handles the synchronous response: approved → navigate to confirmation; rejected → show error; pending → show waiting state.
6. Falls back to redirect flow if backend returns `init_point` (backward compat).

(Previously: Page called `POST /api/v1/pagos` with `{ pedido_id }` and always redirected to `init_point`.)

#### Scenario: Payment with saved card

- **GIVEN** user has saved cards and selects one
- **WHEN** user confirms payment
- **THEN** PaymentPage calls `POST /api/v1/pagos` with the saved card's `card_token`
- **AND** handles the synchronous response inline

#### Scenario: Payment with new card

- **GIVEN** user selects "Nueva Tarjeta"
- **WHEN** `SecureCardForm` returns a card_token
- **THEN** PaymentPage calls `POST /api/v1/pagos` with the new `card_token`

#### Scenario: Loading state while awaiting response

- **WHEN** the `POST /api/v1/pagos` request is in flight
- **THEN** PaymentPage SHALL display a loading indicator and disable any interactive elements

#### Scenario: API error on payment creation

- **WHEN** `POST /api/v1/pagos` returns a non-2xx response
- **THEN** PaymentPage SHALL display an error message with the specific error reason
- **AND** provide a button to retry or navigate back

### Requirement: PaymentResultPage shows post-payment result

The system SHALL provide a `PaymentResultPage` at `/cliente/pago/resultado` that handles BOTH redirect-based results (via `collection_status` query param from Checkout Pro) AND direct navigation from inline Checkout API flow.

(Previously: Only handled redirect-based `collection_status` query parameter.)

#### Scenario: Approved payment result (redirect flow)

- **WHEN** MercadoPago redirects to `/cliente/pago/resultado?collection_status=approved`
- **THEN** PaymentResultPage SHALL display an approved confirmation message

#### Scenario: Direct navigation from inline approved payment

- **WHEN** user is navigated from inline payment with `mp_status: 'approved'`
- **THEN** PaymentResultPage SHALL display the same approved confirmation message

#### Scenario: Rejected payment result

- **WHEN** payment result is rejection (from redirect or inline)
- **THEN** PaymentResultPage SHALL display a rejection message and a button to retry or go to mis pedidos

## REMOVED Requirements

### Requirement: MercadoPago Checkout Pro research document

(Reason: The research document served its purpose during Checkout Pro exploration. With migration to Checkout API, the document becomes historical reference — no longer a system requirement. Can be kept in `docs/` as reference without being a spec requirement.)
