## ADDED Requirements

### Requirement: Kitchen payload exposes ingredient names and the full recipe list

The system SHALL include, for each product line in the kitchen payload, the product's full ingredient list with ingredient names (joining `product_ingredients → ingredients`), and SHALL resolve customization exclusion IDs to ingredient names. The payload MUST NOT force the kitchen to display raw ingredient IDs. This uses the existing `product_ingredients` relationship — no new recipes entity.

#### Scenario: Kitchen payload includes ingredient names
- **WHEN** the kitchen orders endpoint returns a product line
- **THEN** the line includes its ingredients with `nombre` (and `es_removible`), not only IDs

#### Scenario: Exclusions are resolved to names
- **GIVEN** an order line excluding ingredient 7 ("onion")
- **WHEN** the kitchen payload is built
- **THEN** the exclusion is presented as "onion", not "Ingrediente #7"

### Requirement: KDS consumes the shared realtime transport via topic

The system SHALL deliver kitchen real-time updates through the shared `backend/features/websocket/` transport on a kitchen topic (`kitchen:all`), rather than a kitchen-owned connection manager. Behavior parity with the prior KDS push (the same orders appear and update live) MUST be preserved.

#### Scenario: KDS still updates live after the transport move
- **GIVEN** a COCINA screen connected to the kitchen topic
- **WHEN** an order transitions to `EN_PREPARACION`
- **THEN** the KDS reflects the change in real time, as before the refactor

#### Scenario: Kitchen no longer owns the connection manager
- **WHEN** the kitchen feature is inspected
- **THEN** it subscribes to the shared transport and does not define its own WebSocket manager
