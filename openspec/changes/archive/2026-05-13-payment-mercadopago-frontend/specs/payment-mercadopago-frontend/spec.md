## ADDED Requirements

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

### Requirement: PaymentPage initiates MercadoPago payment
The system SHALL provide a `PaymentPage` at `/cliente/pedidos/:id/pago` that:
1. Calls `POST /api/v1/pagos` with `{ pedido_id: id }` on mount.
2. On success, redirects the browser to the `init_point` URL returned in `PagoRead`.
3. Shows a loading indicator while the request is in flight.
4. Shows an error message if the request fails or `init_point` is absent.

#### Scenario: Successful payment initiation
- **WHEN** user arrives at `/cliente/pedidos/42/pago`
- **THEN** the page SHALL call `POST /api/v1/pagos` with `{ pedido_id: 42 }`
- **THEN** on success, the browser SHALL redirect to the `init_point` URL via `window.location.href`

#### Scenario: Loading state while awaiting response
- **WHEN** the `POST /api/v1/pagos` request is in flight
- **THEN** PaymentPage SHALL display a loading indicator and disable any interactive elements

#### Scenario: API error on payment creation
- **WHEN** `POST /api/v1/pagos` returns a non-2xx response
- **THEN** PaymentPage SHALL display an error message and a button to navigate back to the pedido confirmation page

#### Scenario: init_point absent in response
- **WHEN** `POST /api/v1/pagos` returns 200 but `init_point` is null or undefined
- **THEN** PaymentPage SHALL display an error message and SHALL NOT redirect

### Requirement: PaymentResultPage shows post-payment result
The system SHALL provide a `PaymentResultPage` at `/cliente/pago/resultado` that reads the `collection_status` query parameter set by MercadoPago after checkout and displays the corresponding result to the client.

#### Scenario: Approved payment result
- **WHEN** MercadoPago redirects to `/cliente/pago/resultado?collection_status=approved`
- **THEN** PaymentResultPage SHALL display an approved confirmation message

#### Scenario: Pending payment result
- **WHEN** MercadoPago redirects to `/cliente/pago/resultado?collection_status=pending`
- **THEN** PaymentResultPage SHALL display a pending status message explaining the payment is being processed

#### Scenario: Rejected payment result
- **WHEN** MercadoPago redirects to `/cliente/pago/resultado?collection_status=rejected`
- **THEN** PaymentResultPage SHALL display a rejection message and a button to retry or go to mis pedidos

#### Scenario: Unknown or missing collection_status
- **WHEN** user navigates directly to `/cliente/pago/resultado` without query params
- **THEN** PaymentResultPage SHALL display a neutral fallback message and a link to `/cliente/pedidos`

### Requirement: Payments feature folder
The system SHALL have a `features/payments/` folder containing:
- `types/payments.types.ts` — mirrors `PagoRead` from backend schema
- `services/payments.service.ts` — wraps `POST /api/v1/pagos` and `GET /api/v1/pagos/pedido/:id`
- `hooks/useInitPayment.ts` — mutation hook for initiating payment
- `hooks/usePaymentByOrder.ts` — query hook for reading payment status by pedido id

#### Scenario: useInitPayment redirects on success
- **WHEN** `useInitPayment` mutation resolves with a `PagoRead` containing a valid `init_point`
- **THEN** `window.location.href` SHALL be set to `init_point`
