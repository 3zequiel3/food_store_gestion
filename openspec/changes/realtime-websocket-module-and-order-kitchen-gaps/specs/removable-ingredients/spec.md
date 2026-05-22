## ADDED Requirements

### Requirement: Pre-checkout removable-ingredients review step

The system SHALL provide a dedicated step before checkout where the client reviews and toggles only the removable (`es_removible = true`) ingredients of each cart item. Non-removable ingredients MUST NOT be toggleable. The resulting exclusions become the order line's customization.

#### Scenario: Client toggles a removable ingredient before checkout
- **GIVEN** a cart item whose product has a removable ingredient "onion"
- **WHEN** the client reaches the pre-checkout review step and removes "onion"
- **THEN** "onion" is recorded as an exclusion for that cart item's customization

#### Scenario: Non-removable ingredients are not toggleable
- **GIVEN** a cart item whose product has a non-removable ingredient "bun"
- **WHEN** the client views the pre-checkout review step
- **THEN** "bun" is shown as fixed and cannot be removed

#### Scenario: Step shows ingredients per cart item
- **GIVEN** a cart with two different products
- **WHEN** the client reaches the review step
- **THEN** each product's removable ingredients are listed under its own item

### Requirement: es_removible is a global ingredient property

The system SHALL treat `es_removible` as a global property of the ingredient, not a per-product-association field. The frontend product-ingredient assignment MUST NOT send `es_removible` as part of the association; it MUST manage `es_removible` only on the ingredient entity.

#### Scenario: Frontend stops sending per-association es_removible
- **WHEN** the admin assigns an ingredient to a product
- **THEN** the request does NOT include an `es_removible` field on the association

#### Scenario: es_removible edited on the ingredient applies everywhere
- **WHEN** an admin sets an ingredient's `es_removible` flag
- **THEN** that flag applies to the ingredient across every product that uses it

### Requirement: es_removible and activo are distinct ingredient concerns

The system SHALL treat `es_removible` (client-removability) and `activo` (kitchen availability) as two distinct, orthogonal global properties of an ingredient. `es_removible` governs whether a CLIENT may exclude the ingredient via `personalizacion`; `activo` governs whether the KITCHEN currently has the ingredient. `activo` MUST NOT model numeric stock and MUST default to `true`. The two flags MUST NOT be conflated: customization validation reads `es_removible`, while the FSM availability guard reads `activo`. An ingredient MAY be `es_removible=true, activo=false` (removable but currently out), or `es_removible=false, activo=true`, etc. — all four combinations are valid.

#### Scenario: A removable ingredient can be unavailable
- **GIVEN** an ingredient with `es_removible=true`
- **WHEN** the kitchen marks it unavailable
- **THEN** `activo` becomes `false` while `es_removible` stays `true` — the two flags are independent

#### Scenario: The guard reads activo, not es_removible
- **GIVEN** an order line requiring an ingredient with `es_removible=true` and `activo=false`, not excluded in that line
- **WHEN** the order attempts to advance to the kitchen
- **THEN** it is blocked by the availability guard because `activo=false`, regardless of `es_removible`

#### Scenario: Excluding a removable ingredient relies on personalizacion, availability relies on activo
- **GIVEN** a line that excluded a removable ingredient in its `personalizacion`
- **WHEN** that ingredient is `activo=false`
- **THEN** that line does not block (the guard reads `personalizacion` exclusions against `activo`), because the excluded ingredient is not required by the line
