## MODIFIED Requirements

### Requirement: Admin resolves an ingredient shortage and notifies the cook

The system SHALL allow an ADMIN to resolve an ingredient shortage with a friendly action ("ingrediente comprado" / "solucionado"). Resolving MUST set the ingredient's `activo` flag to `true` and MUST bulk-close every open report row for that ingredient (set `resuelto_en` and `resuelto_por` on all rows where `resuelto_en IS NULL`). Both writes MUST run inside a single Unit of Work. On resolution the system MUST publish an `ingredient_availability_restored` domain event (best-effort) to the kitchen so the cook is notified; the publish MUST occur AFTER the Unit of Work commits. Resolved rows MUST be kept for audit.

The admin UI for resolving a shortage SHALL expose ONE primary action control per row ("Resolver"), accompanied by a single audit-label selector offering exactly two values (`solucionado`, default; `comprado`). The UI MUST NOT render two separate primary buttons for the same endpoint. The selected label MUST be POSTed as the `accion` field to `POST /api/v1/availability/faltantes/{ingrediente_id}/resolver`.

#### Scenario: Resolution restores availability and closes open reports

- **GIVEN** ingredient 7 has `activo=false` and two open reports
- **WHEN** an ADMIN resolves it as "ingrediente comprado"
- **THEN** `Ingrediente(7).activo` becomes `true` AND both open rows get `resuelto_en` and `resuelto_por` set; no open report for ingredient 7 remains

#### Scenario: Cook is notified on resolution

- **GIVEN** a COCINA connection subscribed to the kitchen topic
- **WHEN** an ADMIN resolves the shortage for ingredient 7
- **THEN** an `ingredient_availability_restored` event for ingredient 7 is delivered to the kitchen AFTER the database commit

#### Scenario: Resolved reports are retained for audit

- **WHEN** a shortage is resolved
- **THEN** its report rows remain in `ingredient_availability_history` with `resuelto_en`/`resuelto_por` populated and are visible in the resolved/audit view

#### Scenario: Admin UI renders one resolver button per row

- **GIVEN** the Faltantes page lists three open shortages
- **WHEN** the page renders
- **THEN** exactly one "Resolver" button and exactly one audit-label selector are rendered per row; no row contains a second primary CTA pointing to the same `/resolver` endpoint

#### Scenario: Resolver POSTs the selected accion

- **GIVEN** an ADMIN on the Faltantes page with the audit-label selector set to `comprado`
- **WHEN** the ADMIN clicks "Resolver" for ingredient 7
- **THEN** the request body sent to `POST /api/v1/availability/faltantes/7/resolver` contains `{ "accion": "comprado" }`

#### Scenario: Default audit label is solucionado

- **GIVEN** an ADMIN opens the Faltantes page and does not change the selector
- **WHEN** the ADMIN clicks "Resolver" for any row
- **THEN** the request body contains `{ "accion": "solucionado" }`
