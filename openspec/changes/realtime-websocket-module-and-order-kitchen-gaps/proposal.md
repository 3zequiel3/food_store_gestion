## Why

The real-time transport lives **inside** `backend/features/cocina/` (`ws_manager.py`, the WS endpoint in `router.py`, the drain task and `publish_transition_event` in `service.py`). Because the WebSocket is nested under the kitchen feature, only the KDS gets live pushes — the client and admin order-detail views are left polling. Worse, `orders/service.py` reaches **into** the kitchen feature (`from features.cocina.service import publish_transition_event`) to broadcast, an inverted dependency: the order domain should not know a kitchen screen exists.

On top of that, a prior gap analysis (engram `sdd/order-kitchen-gap-analysis/explore`, with file:line evidence) confirmed several order/kitchen business-logic gaps that contradict the owner's intended flow: cash-on-delivery is hard-blocked, the cook only sees raw ingredient IDs, there is no kitchen→admin messaging, the FSM has an unreachable transition and two illegal shortcuts, and customizations accept arbitrary integers.

This change does both at once because the business-logic gaps (kitchen→admin messaging, real-time client/admin updates, bidirectional cook actions) **ride on** the realtime transport — fixing them cleanly requires the transport seam to exist first.

## What Changes

**Foundation — realtime transport extraction (must land first):**
- New module `backend/features/websocket/` owning: the WS endpoint (`/ws`) + `/ws/health`, a connection manager with **topic/room filtering**, an `EventPublisher` **port** defining the versioned event contract (event types + payload schema), and the drain/broadcast service.
- `backend/main.py` exposes a single `register_realtime(app)` call in its lifespan — the only realtime touchpoint in main. All init encapsulated in the module.
- **BREAKING (internal seam)**: invert the orders→cocina coupling. `orders/service.py` publishes **domain events** against the `EventPublisher` interface; it no longer imports `features.cocina.service.publish_transition_event`.
- Best-effort publish preserved (never breaks the HTTP response) + `/ws/health` so the frontend can show degraded/polling mode. The existing 30s polling fallback stays.
- Stays **in-process** (no Redis/broker) — consistent with the documented design (`docs/CHANGES.md:336`). The seam makes a future extraction mechanical, but no broker is introduced now.

**Business-logic gap fixes (mapped to gap IDs):**
- **P0.2** — Allow cash-on-delivery (pago al repartidor): remove the EFECTIVO+delivery hard block (`orders/service.py:129-136`) via a dedicated checkout path; order lands in `PENDIENTE`. Keep cash+pickup.
- **P0.1 / P0.3** — Kitchen→admin "ingredient unavailable" feature over a **bidirectional** WS: the cook, viewing an order in `CONFIRMADO` or `EN_PREPARACION`, marks one of that order's ingredients as unavailable. This sets a NEW global `Ingrediente.activo = false` flag (kitchen availability — distinct from `es_removible`, NOT stock; no numeric `cantidad`) AND appends one row per report event to a NEW audit/event log `HistorialDisponibilidadIngrediente` (follows the `HistorialEstadoPedido` precedent). The admin sees a NAVBAR inbox indicator and a dedicated "Faltantes" view in the comidas section of the sidebar; resolving ("ingrediente comprado" / "solucionado") sets `activo = true`, bulk-closes every open report row for that ingredient, and notifies the cook. The history log IS the message/notification source — there is NO separate message entity. Adds a client→server inbound message router and contract.
- **FSM availability guard** — an order is BLOCKED from advancing `CONFIRMADO → EN_PREPARACION` and `EN_PREPARACION → TERMINADO` while ANY of its order lines requires an ingredient with `activo = false` that is NOT excluded in that line's `personalizacion`. Exclusion-aware at the line level, evaluated at the order level. The block lifts automatically when the ingredient returns to `activo = true`.
- **P1.4** — Cook sees the FULL ingredient list (the existing `product_ingredients`) with **names**, not raw IDs.
- **P1.5** — Real-time auto-update of CLIENT and ADMIN order-detail views on state change, via topic/room (client → own order; admin → all).
- **P1.6** — Pre-checkout removable-ingredients step: review/toggle only `es_removible` ingredients per cart item before checkout.
- **P2.7** — Frontend stops sending `es_removible` as a per-association field (`ProductFormModal.tsx:209`); aligns to the global ingredient model.
- **P2.8** — Backend rejects customization (excluded ingredient) IDs that are not `es_removible=true` ingredients of that product.
- **P3.9** — Add the missing `TERMINADO → CANCELADO_ADMIN` RBAC entry for ADMIN (currently FSM-valid but always 403).
- **P3.10** — Remove the `CONFIRMADO → ENTREGADO` shortcut (bypasses kitchen).
- **P3.11** — Remove/guard the manual "Confirmar pedido" admin button for PENDIENTE orders (CONFIRMADO is webhook/payment-driven).

## Capabilities

### New Capabilities
- `realtime-websocket`: the transport module — WS endpoint + `/ws/health`, connection manager with topic/room filtering, `EventPublisher` port + versioned event contract, inbound message router, drain/broadcast service, in-process resilience model. Covers FOUNDATION + P0.3 transport.
- `kitchen-admin-messaging`: cook marks an order ingredient UNAVAILABLE → sets global `Ingrediente.activo=false` + appends a `HistorialDisponibilidadIngrediente` row (one per report event, derived `pendiente`/`resuelto` from `resuelto_en`) → admin navbar inbox + "Faltantes" view → explicit resolution sets `activo=true`, bulk-closes open rows, notifies the cook; rides bidirectional WS. Covers P0.1.
- `order-payment-methods`: cash-on-delivery (pago al repartidor) checkout path, alongside cash+pickup and online card. Covers P0.2.
- `removable-ingredients`: dedicated pre-checkout step where the client reviews/toggles only `es_removible` ingredients per cart item; global `es_removible` model alignment. Clarifies that `es_removible` (client-removability) and the NEW `activo` (kitchen availability) are **distinct, orthogonal** ingredient concerns. Covers P1.6 + P2.7.

### Modified Capabilities
- `kitchen-display-backend`: the kitchen payload joins `product_ingredients → ingredients` to expose ingredient **names** and the full recipe list; KDS becomes a topic/room consumer of the new transport. Covers P1.4 (backend) + P1.5 (KDS consumer).
- `kitchen-display-frontend`: `KitchenOrderDetail` shows ingredient names + full list instead of "Ingrediente #N"; cook UI gains the ingredient-unavailable trigger. Covers P1.4 (frontend) + P0.1 (cook trigger).
- `order-visualization-frontend`: client and admin order-detail views subscribe to the WS and auto-update on state change (preserving 30s polling fallback). Covers P1.5 (consumers).
- `order-state-machine`: add `TERMINADO → CANCELADO_ADMIN` RBAC for ADMIN (P3.9); remove the `CONFIRMADO → ENTREGADO` FSM edge (P3.10); validate customization IDs are removable ingredients of the product (P2.8); guard manual PENDIENTE→CONFIRMADO from the admin UI/endpoint per webhook-only intent (P3.11); **add the ingredient-availability guard** that blocks `CONFIRMADO → EN_PREPARACION` and `EN_PREPARACION → TERMINADO` while any non-excluded order line requires an `activo=false` ingredient (exclusion-aware per line, evaluated per order).
- `checkout-validation`: customization IDs accepted by checkout MUST be `es_removible=true` ingredients of the ordered product (P2.8 enforcement at the checkout boundary).

## Impact

**Backend**
- New module: `backend/features/websocket/` (manager, port/contract, inbound router, drain service, `register_realtime`, `/ws` + `/ws/health`).
- `backend/main.py`: replace the inline cocina drain-task wiring with `register_realtime(app)`; mount the websocket router.
- `backend/features/orders/service.py`: publish domain events via `EventPublisher`; drop the cocina import; FSM edits.
- `backend/features/orders/state_machine.py`: `ALLOWED_TRANSITIONS` + `TRANSITION_ROLES` edits (P3.9, P3.10). The availability guard logic stays in the service layer (it needs DB reads of order lines + ingredient `activo`); `state_machine.py` remains pure.
- `backend/features/catalog/models.py`: NEW `Ingrediente.activo: bool` column (default true) + Alembic migration. Does NOT touch stock/catalog; no `cantidad`.
- New persistence: `HistorialDisponibilidadIngrediente` (`ingredient_availability_history`) audit/event log — `ingrediente_id`, `reportado_por`, `pedido_id`, `creado_en`, `resuelto_en` (nullable), `resuelto_por` (nullable). Append-on-report; `resuelto_en`/`resuelto_por` set on resolution (bulk-close). `pendiente`/`resuelto` derived from `resuelto_en`. Alembic migration; UoW wraps the report write (`activo` toggle + row insert) and the resolution write (`activo` toggle + bulk close).
- `backend/features/cocina/`: `ws_manager.py` removed/migrated; `service.py` becomes a KDS consumer + recipe-name join; `router.py` WS endpoint migrates to the websocket module.
- `backend/features/checkout/` (service + schemas + router): cash-on-delivery path; customization validation (P2.8).
- `backend/features/orders/service.py` (or a kitchen-availability service): the report path (toggle `activo=false` + insert history row, UoW), the resolution path (toggle `activo=true` + bulk-close open rows, UoW), the "Faltantes" open-shortage query, and the FSM availability guard invoked from `avanzar_estado` before `validate_transition`.

**Frontend**
- `frontend/src/features/cocina/components/KitchenOrderDetail.tsx`: ingredient names + full list; ingredient-unavailable trigger.
- `frontend/src/features/orders/components/OrderDetailModal.tsx`: WS subscription (client + admin) with polling fallback.
- `frontend/src/features/orders/components/OrderStateActions.tsx`: remove/guard manual "Confirmar pedido" for PENDIENTE (P3.11).
- `frontend/src/pages/client/ProductDetailPage.tsx` + new pre-checkout step component: removable-ingredients review (P1.6).
- `frontend/src/features/products/components/admin/ProductFormModal.tsx`: stop sending per-association `es_removible` (P2.7).
- New admin **navbar inbox indicator** + dedicated **"Faltantes" view** in the comidas section of the admin sidebar (table of OPEN shortages where `resuelto_en IS NULL`, with a filtered/resolved audit view); resolution action ("ingrediente comprado" / "solucionado"). Shared WS client/hook with topic/room subscription + `/ws/health`-driven degraded mode.

**Dependencies / systems**: no new runtime dependencies (no Redis/broker). In-process WS only — single-instance limitation documented in `design.md` (matches `docs/CHANGES.md:336`).

**Out of scope**:
- The formal recipes module (a dedicated `ingredients↔products` entity with quantities/instructions). P1.4 only surfaces the existing `product_ingredients` list with names.
- Numeric stock / `cantidad` for ingredients — `activo` is a boolean availability flag only; it does NOT touch stock or catalog quantities.
- **Notifying the CLIENT** that an ingredient is unavailable, and offering an **ingredient-swap** or an **admin-cancel-with-reason** flow — deferred, to be designed carefully later. This change stops at kitchen→admin signalling and the FSM advance-block; the client-facing resolution UX is a separate future change.
