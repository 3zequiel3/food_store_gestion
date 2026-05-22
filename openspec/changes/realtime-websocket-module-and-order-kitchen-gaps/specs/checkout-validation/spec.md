## ADDED Requirements

### Requirement: Customization IDs must be removable ingredients of the product

The system SHALL reject a checkout (and order creation) whose customization (excluded ingredient) IDs are not `es_removible = true` ingredients associated with the ordered product. The validation MUST run server-side at the checkout/order-creation boundary and MUST raise a business-rule error (HTTP 422) on violation. Accepting any positive integer as a customization ID is no longer permitted.

#### Scenario: Valid removable exclusion is accepted
- **GIVEN** a product whose ingredient "onion" has `es_removible = true`
- **WHEN** the client checks out excluding "onion"
- **THEN** the order is created with that exclusion

#### Scenario: Non-removable ingredient exclusion is rejected
- **GIVEN** a product whose ingredient "bun" has `es_removible = false`
- **WHEN** the client checks out excluding "bun"
- **THEN** the system returns HTTP 422 (business rule error)

#### Scenario: Ingredient not on the product is rejected
- **GIVEN** an ingredient that is NOT associated with the ordered product
- **WHEN** the client checks out excluding that ingredient
- **THEN** the system returns HTTP 422 (business rule error)

#### Scenario: Arbitrary integer ID is rejected
- **WHEN** a checkout request includes a customization ID that is not a removable ingredient of the product
- **THEN** the system rejects it with HTTP 422 rather than silently accepting it
