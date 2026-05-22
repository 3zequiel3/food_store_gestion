## ADDED Requirements

### Requirement: Cash on delivery is allowed

The system SHALL allow creating an order with payment method `EFECTIVO` together with a delivery address (pago al repartidor). The order MUST be created in `PENDIENTE` with `costo_envio` applied for delivery, and MUST NOT create a `Pago` row at creation time (cash is collected on delivery). The prior hard block that rejected EFECTIVO + delivery MUST be removed.

#### Scenario: Cash-on-delivery order is created
- **WHEN** a CLIENT submits a cash order with a valid delivery address
- **THEN** the order is created in `PENDIENTE`, with the delivery shipping cost applied and no `Pago` row

#### Scenario: Old hard block no longer fires
- **WHEN** a CLIENT submits `EFECTIVO` with a `direccion_id`
- **THEN** the system does NOT return `invalid_payment_for_delivery`

### Requirement: Cash on pickup remains supported

The system SHALL continue to support `EFECTIVO` with in-store pickup (no delivery address). The order MUST be created in `PENDIENTE` with zero shipping cost and no `Pago` row.

#### Scenario: Cash-pickup order is created
- **WHEN** a CLIENT submits a cash pickup order
- **THEN** the order is created in `PENDIENTE` with `costo_envio = 0.00` and no `Pago` row

### Requirement: Cash-on-delivery has its own checkout path

The system SHALL expose a dedicated checkout request/response schema and endpoint for cash-on-delivery, distinct from the online (card) checkout, accepting the cart items, the delivery address, and optional notes.

#### Scenario: Endpoint accepts a delivery address for cash
- **WHEN** a CLIENT calls the cash-on-delivery checkout endpoint with items and a delivery address
- **THEN** the request is accepted and an order is created

#### Scenario: Online card checkout is unchanged
- **WHEN** a CLIENT completes an online card checkout
- **THEN** the existing MercadoPago flow behaves as before (order in `PENDIENTE`, `Pago` row created on approval)
