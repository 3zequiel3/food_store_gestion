## ADDED Requirements

### Requirement: Cook can flag an order ingredient as unavailable

The system SHALL allow a COCINA or ADMIN user, while viewing an order in `CONFIRMADO` or `EN_PREPARACION`, to mark a specific ingredient of that order as unavailable. The action MUST be authorized for COCINA/ADMIN only and MUST identify the order and the ingredient. Marking an ingredient unavailable MUST set the ingredient's global `activo` flag to `false` and MUST append one row to the `HistorialDisponibilidadIngrediente` log. Both writes MUST run inside a single Unit of Work.

#### Scenario: Cook flags an ingredient unavailable
- **GIVEN** a COCINA user viewing order 123 (in `CONFIRMADO` or `EN_PREPARACION`)
- **WHEN** they mark ingredient 7 of that order as unavailable
- **THEN** `Ingrediente(7).activo` becomes `false` AND a `HistorialDisponibilidadIngrediente` row is appended with `ingrediente_id=7`, `pedido_id=123`, `reportado_por=<cook>`, `resuelto_en=NULL`

#### Scenario: Client cannot flag ingredients
- **GIVEN** a CLIENT user
- **WHEN** they attempt to flag an ingredient unavailable
- **THEN** the system rejects the request as unauthorized and no row is created and `activo` is unchanged

### Requirement: Ingredient-availability reports are persisted as an append-on-report log

The system SHALL persist each ingredient-unavailable report as one row in `HistorialDisponibilidadIngrediente` (table `ingredient_availability_history`) with: `ingrediente_id`, `reportado_por` (cook user), `pedido_id` (order where detected), `creado_en`, `resuelto_en` (nullable), and `resuelto_por` (nullable). A report is `pendiente` when `resuelto_en IS NULL` and `resuelto` otherwise — there MUST NOT be a separate status column. There MUST NOT be any separate "messages" entity; this log IS the message/notification source. Reports MUST survive even when no admin is connected.

#### Scenario: Report persists when no admin is online
- **GIVEN** no ADMIN is connected to the WebSocket
- **WHEN** a cook flags an ingredient unavailable
- **THEN** a row is persisted in `ingredient_availability_history` and is available to an admin who connects later

#### Scenario: Pending vs resolved is derived from resuelto_en
- **WHEN** a report row has `resuelto_en IS NULL`
- **THEN** it is treated as `pendiente`; once `resuelto_en` is set it is treated as `resuelto`

#### Scenario: An ingredient can be reported many times over its lifecycle
- **GIVEN** ingredient 7 was reported unavailable, resolved, and later reported unavailable again
- **THEN** the log contains multiple rows for ingredient 7, the older ones with `resuelto_en` set and the latest pending

### Requirement: Admin inbox and Faltantes view surface kitchen reports

The system SHALL deliver ingredient-unavailable reports to the admin via a navbar inbox indicator AND a dedicated "Faltantes" view located in the comidas section of the admin sidebar. When a report is created, the system MUST publish an `ingredient_unavailable_reported` domain event (best-effort) so a connected admin's inbox updates in real time; an admin connecting later MUST be able to load open shortages (`resuelto_en IS NULL`) from persistence. A separate/filtered view MAY show resolved reports for audit.

#### Scenario: Live update for connected admin
- **GIVEN** an ADMIN connected
- **WHEN** a cook flags an ingredient unavailable
- **THEN** the admin's navbar inbox indicates the new report without a manual refresh, with a message like "El cocinero <Nombre> indicó que el ingrediente <Nombre> no se encuentra disponible para el pedido <ID>"

#### Scenario: Open shortages load in the Faltantes view
- **GIVEN** persisted reports with `resuelto_en IS NULL`
- **WHEN** an ADMIN opens the "Faltantes" view
- **THEN** the open shortages are listed; resolved reports do not appear in the open list

### Requirement: Admin resolves an ingredient shortage and notifies the cook

The system SHALL allow an ADMIN to resolve an ingredient shortage with a friendly action ("ingrediente comprado" / "solucionado"). Resolving MUST set the ingredient's `activo` flag to `true` and MUST bulk-close every open report row for that ingredient (set `resuelto_en` and `resuelto_por` on all rows where `resuelto_en IS NULL`). Both writes MUST run inside a single Unit of Work. On resolution the system MUST publish an `ingredient_availability_restored` domain event (best-effort) to the kitchen so the cook is notified. Resolved rows MUST be kept for audit.

#### Scenario: Resolution restores availability and closes open reports
- **GIVEN** ingredient 7 has `activo=false` and two open reports
- **WHEN** an ADMIN resolves it as "ingrediente comprado"
- **THEN** `Ingrediente(7).activo` becomes `true` AND both open rows get `resuelto_en` and `resuelto_por` set; no open report for ingredient 7 remains

#### Scenario: Cook is notified on resolution
- **GIVEN** a COCINA connection subscribed to the kitchen topic
- **WHEN** an ADMIN resolves the shortage for ingredient 7
- **THEN** an `ingredient_availability_restored` event for ingredient 7 is delivered to the kitchen

#### Scenario: Resolved reports are retained for audit
- **WHEN** a shortage is resolved
- **THEN** its report rows remain in `ingredient_availability_history` with `resuelto_en`/`resuelto_por` populated and are visible in the resolved/audit view
