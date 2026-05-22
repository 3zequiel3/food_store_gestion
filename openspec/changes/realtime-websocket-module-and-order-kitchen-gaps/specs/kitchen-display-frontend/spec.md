## ADDED Requirements

### Requirement: Kitchen order detail shows ingredient names and full list

The system SHALL render, in the kitchen order detail, each product's full ingredient list using ingredient names, and SHALL show exclusions by name. The view MUST NOT display "Ingrediente #N".

#### Scenario: Full ingredient list with names
- **WHEN** a cook opens an order's detail
- **THEN** each product shows its ingredients by name and indicates which are excluded

#### Scenario: No raw IDs displayed
- **WHEN** an order line excludes an ingredient
- **THEN** the exclusion is shown by ingredient name, not as "Ingrediente #N"

### Requirement: Cook can trigger ingredient-unavailable from the kitchen view

The system SHALL provide a control in the kitchen order detail for a cook to flag a specific ingredient of an order as unavailable, available while the order is in `CONFIRMADO` or `EN_PREPARACION`. The action MUST be sent over the WebSocket transport as a `kitchen.ingredient_unavailable` message carrying `order_id` and `ingredient_id`. The cook MUST also receive an `ingredient_availability_restored` notification when an admin later resolves the shortage.

#### Scenario: Cook flags an ingredient from the UI
- **WHEN** a cook selects "mark unavailable" on an ingredient of an order in `CONFIRMADO` or `EN_PREPARACION`
- **THEN** the client sends a `kitchen.ingredient_unavailable` message (with `order_id` and `ingredient_id`) over the WebSocket and shows confirmation

#### Scenario: Cook is notified when the shortage is resolved
- **GIVEN** a cook who previously flagged an ingredient unavailable
- **WHEN** an admin resolves the shortage
- **THEN** the kitchen view receives an `ingredient_availability_restored` notification for that ingredient
