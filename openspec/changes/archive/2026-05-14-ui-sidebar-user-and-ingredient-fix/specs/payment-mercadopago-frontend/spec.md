# Delta Spec: payment-mercadopago-frontend (ADDED Requirement)

### Requirement: MercadoPago Checkout Pro research document
The system SHALL include a research document at `docs/mercadopago-checkout-pro-research.md` that covers: preference creation flow, webhook IPN format, return URL behavior, notification polling strategy, and current integration gaps. The document SHALL be dated and link to official MercadoPago documentation.

(No behavior change — research artifact only. Existing `payment-mercadopago-frontend` spec requirements are unchanged.)

##### Scenario: Research document exists and is findable
- **WHEN** a developer looks for MercadoPago integration documentation
- **THEN** `docs/mercadopago-checkout-pro-research.md` exists and covers preference creation, webhooks, return URLs, and polling

##### Scenario: Document links to official MP docs
- **WHEN** the research document is read
- **THEN** it contains at least one link to the official MercadoPago Checkout Pro documentation
