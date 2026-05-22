# Checkout API Payment — Specification

## Purpose

Server-side payment creation via MercadoPago's `sdk.payment().create()` with inline card tokenization, synchronous approval handling, and idempotency — replacing the redirect-based Checkout Pro flow.

## Requirements

### Requirement: Checkout API payment creation

The system SHALL accept `POST /api/v1/pagos` with optional fields `card_token`, `payment_method_id`, `installments` in `PagoCreate`. When `card_token` is present, the system SHALL use `sdk.payment().create()` instead of `sdk.preference().create()`.

#### Scenario: Create payment with card token

- **GIVEN** an authenticated user with a valid pedido
- **WHEN** `POST /api/v1/pagos` with `{ pedido_id, card_token, payment_method_id, installments }`
- **THEN** system calls `sdk.payment().create(payment_data, request_options)`
- **AND** responds `201 Created` with `PagoRead` containing `mp_status`

#### Scenario: Backward compat — no card_token falls back to Checkout Pro

- **GIVEN** an authenticated user
- **WHEN** `POST /api/v1/pagos` with `{ pedido_id }` (no card_token)
- **THEN** system calls `sdk.preference().create()` (existing Checkout Pro flow)
- **AND** responds with `init_point` for redirect

### Requirement: Payment data structure

The `crear_pago_api()` method SHALL build a payment dict with: `transaction_amount` (from pedido total), `token` (card_token), `description`, `installments`, `payment_method_id`, `external_reference` (pedido id).

#### Scenario: All required fields populated

- **WHEN** `crear_pago_api()` is called with valid inputs
- **THEN** the payment dict contains all 6 required fields
- **AND** `transaction_amount` matches the pedido's `total`

### Requirement: Idempotency key

The system SHALL generate a UUID4 `x-idempotency-key` for each payment attempt and pass it as `request_options` to `sdk.payment().create()`.

#### Scenario: Duplicate request with same idempotency key

- **GIVEN** a payment was created with idempotency key `abc-123`
- **WHEN** another request arrives with the same `pedido_id` and idempotency key `abc-123`
- **THEN** system returns the SAME payment (no duplicate charge)

#### Scenario: Different idempotency keys create separate payments

- **GIVEN** two payment attempts for the same pedido with different keys
- **WHEN** both are processed
- **THEN** each creates a distinct MP payment

### Requirement: Synchronous payment response

When `sdk.payment().create()` returns, the system SHALL map the MP response `status` to the pago's `mp_status` field and return it synchronously to the caller.

#### Scenario: Approved payment

- **WHEN** MP returns `status: 'approved'`
- **THEN** `PagoRead.mp_status` is `'approved'`
- **AND** pedido transitions to `CONFIRMADO` state

#### Scenario: Rejected payment

- **WHEN** MP returns `status: 'rejected'`
- **THEN** `PagoRead.mp_status` is `'rejected'`
- **AND** pedido state is NOT changed

#### Scenario: Pending payment

- **WHEN** MP returns `status: 'pending'`
- **THEN** `PagoRead.mp_status` is `'pending'`
- **AND** pedido state remains unchanged (webhook will handle later)

### Requirement: MP API error mapping

The system SHALL map MercadoPago payment API errors to appropriate HTTP responses with user-friendly messages.

#### Scenario: Invalid card token

- **WHEN** MP returns error code for invalid/expired token
- **THEN** responds `400 Bad Request` with message indicating the card token is invalid

#### Scenario: Insufficient funds

- **WHEN** MP returns rejection reason `cc_rejected_insufficient_amount`
- **THEN** responds `402 Payment Required` with message about insufficient funds

#### Scenario: Generic MP API error

- **WHEN** MP returns an unmapped error
- **THEN** responds `502 Bad Gateway` with the MP error detail

### Requirement: PCI compliance maintained

Card data (number, CVV) SHALL NEVER reach the backend. The frontend tokenizes via MP.js Secure Fields, and only the resulting `card_token` is sent to the server.

#### Scenario: Card number not in request payload

- **WHEN** frontend submits payment
- **THEN** the request body contains `card_token` (string), NOT raw card number or CVV
