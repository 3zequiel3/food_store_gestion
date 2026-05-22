<!--
STRICT TDD: every implementation task is preceded by its test task (red → green).
Backend test runner: pytest. Frontend test runner: vitest.
Phasing follows design.md D11 (foundation-first). Each phase = one chained PR.
-->

## Review Workload Forecast

- **Estimated changed lines**: ~2,300–3,000 (new websocket module, FSM edits, checkout path + validation, kitchen recipe join + UI, realtime consumers, ingredient `activo` flag + `HistorialDisponibilidadIngrediente` + 2 migrations, report/resolution services + UoW, FSM availability guard, admin navbar inbox + "Faltantes" view + cook trigger, frontend WS client/hook). The refined ingredient-availability design grew Phase 6 from ~9 to ~24 tasks.
- **400-line single-PR budget**: **High** risk — far exceeds 400 lines.
- **Chained PRs recommended**: **Yes** — one PR per phase (6 PRs), in dependency order. Each phase is independently shippable; Phase 1 is parity-only (no behavior change) to de-risk the extraction. Phase 6 is now the largest slice — if it alone exceeds the 400-line budget, split it along the 6a–6e sub-sections (data model+migrations → services → FSM guard → inbound/endpoints → frontend) into chained sub-PRs.
- **Decision needed before apply**: Yes — confirm chained-PR delivery and chain strategy; decide whether Phase 6 ships as one PR or sub-chained (6a–6e).
- **Suggested PR boundaries**: PR1 = Phase 1, PR2 = Phase 2, PR3 = Phase 3, PR4 = Phase 4, PR5 = Phase 5, PR6 = Phase 6 (optionally sub-chained 6a–6e).

## 1. Phase 1 — WebSocket module foundation (PR1, parity-only)

- [x] 1.1 Characterization tests (pytest): capture CURRENT KDS behavior — `publish_transition_event` enqueues for CONFIRMADO/EN_PREPARACION/TERMINADO/CANCELADO*, broadcast fan-out, best-effort swallow. (red against not-yet-moved code = baseline)
- [x] 1.2 Test: `EventPublisher` port contract — `publish(DomainEvent)` is best-effort and never raises; emits versioned `{v,type,topic,payload,ts}`.
- [x] 1.3 Implement `backend/features/websocket/` skeleton: `EventPublisher` Protocol + `DomainEvent` + versioned contract types.
- [x] 1.4 Test: connection manager registers/disconnects and broadcasts only to a topic's subscribers.
- [x] 1.5 Implement the connection manager with topic indexing (move logic out of `features/cocina/ws_manager.py`).
- [x] 1.6 Test: `InProcessEventPublisher` enqueues onto the asyncio queue; drain task broadcasts each event.
- [x] 1.7 Implement drain/broadcast service + `InProcessEventPublisher` (relocate from `features/cocina/service.py`).
- [x] 1.8 Test: topic/room scope derived from JWT at handshake; CLIENT scope = owned `order:{id}`, ADMIN/PEDIDOS = `orders:all`, COCINA/ADMIN = `kitchen:all`; client-declared scope is ignored.
- [x] 1.9 Implement WS handshake auth + scope binding + `/ws` endpoint in the module (relocate from `features/cocina/router.py`).
- [x] 1.10 Test: `GET /ws/health` returns 200 with drain-task/connection status.
- [x] 1.11 Implement `/ws/health`.
- [x] 1.12 Test: `register_realtime(app)` mounts routes, starts drain task, binds publisher; `main.py` has exactly one realtime touchpoint and no manager/queue references.
- [x] 1.13 Implement `register_realtime(app)`; wire it into `main.py` lifespan; remove inline cocina drain wiring (`main.py:108-115`).
- [x] 1.14 Test: `orders/service.py` publishes a domain event via the port and has no `from features.cocina` import; transition still succeeds when publish fails.
- [x] 1.15 Invert the coupling — replace `from features.cocina.service import publish_transition_event` (`orders/service.py:296-301`) with port-based `publish`.
- [x] 1.16 Test: KDS parity — COCINA on `kitchen:all` still receives confirmadо/preparación/terminado/cancelado updates as before.
- [x] 1.17 Make cocina a consumer of the shared transport; remove the kitchen-owned manager + `/ws` route.
- [x] 1.18 Run full backend suite green; confirm KDS behavior parity.

## 2. Phase 2 — FSM fixes (PR2)

- [x] 2.1 Test: `validate_transition("TERMINADO","CANCELADO_ADMIN",{"ADMIN"})` passes; with `{"PEDIDOS"}` → 403.
- [x] 2.2 Implement P3.9 — add `("TERMINADO","CANCELADO_ADMIN"): {"ADMIN"}` to `TRANSITION_ROLES`.
- [x] 2.3 Test: `validate_transition("CONFIRMADO","ENTREGADO",{"ADMIN"})` raises `BusinessRuleError`; `("CONFIRMADO","ENTREGADO")` absent from `TRANSITION_ROLES`.
- [x] 2.4 Implement P3.10 — remove `ENTREGADO` from `ALLOWED_TRANSITIONS["CONFIRMADO"]` and the RBAC entry.
- [ ] 2.5 Test (vitest): `OrderStateActions` for `PENDIENTE` does NOT render a "Confirmar pedido" / CONFIRMADO action; reject/cancel still present.
- [ ] 2.6 Implement P3.11 — remove the CONFIRMADO transition from the PENDIENTE set in `OrderStateActions.tsx`.
- [ ] 2.7 Run backend FSM/RBAC suite + frontend orders suite green.

## 3. Phase 3 — Business logic: payment + customization + removable step (PR3)

- [x] 3.1 Test: customization IDs that are not `es_removible=true` ingredients of the product → 422 (P2.8); valid removable exclusion accepted.
- [x] 3.2 Implement P2.8 — server-side validation joining `product_ingredients`+`Ingrediente.es_removible` at the checkout/order-creation boundary.
- [x] 3.3 Test: cash-on-delivery (`EFECTIVO` + `direccion_id`) creates a `PENDIENTE` order with shipping cost and no `Pago`; old `invalid_payment_for_delivery` block no longer fires; cash+pickup still works.
- [x] 3.4 Implement P0.2 — remove the hard block (`orders/service.py:129-136`); add cash-on-delivery schema + service path + router endpoint (mirror `crear_pedido_pickup_efectivo`).
- [ ] 3.5 Test (vitest): product-ingredient assignment request omits per-association `es_removible` (P2.7).
- [ ] 3.6 Implement P2.7 — drop the `es_removible` argument from `addProductIngredient` calls in `ProductFormModal.tsx:209`; manage `es_removible` only on the ingredient entity.
- [ ] 3.7 Test (vitest): pre-checkout review step lists removable ingredients per cart item; non-removable shown fixed; toggling records exclusions (P1.6).
- [ ] 3.8 Implement P1.6 — pre-checkout removable-ingredients step component wired before checkout.
- [ ] 3.9 Run backend checkout/orders suite + frontend products/checkout suite green.

## 4. Phase 4 — Realtime order-detail consumers (PR4)

- [ ] 4.1 Test (vitest): a shared WS client/hook subscribes to a topic, handles `order_state_changed`, and falls back to 30s polling when disconnected (read `/ws/health`).
- [ ] 4.2 Implement the shared frontend WS client/hook (subscribe, reconnect, degraded mode).
- [ ] 4.3 Test (vitest): client `OrderDetailModal` subscribes to its own `order:{id}` and auto-updates on state change; does not receive other clients' orders.
- [ ] 4.4 Implement P1.5 (client) — wire `OrderDetailModal` as an `order:{id}` consumer, preserving polling fallback.
- [ ] 4.5 Test (vitest): admin `OrderDetailModal` subscribes to all order events and auto-updates.
- [ ] 4.6 Implement P1.5 (admin) — wire the admin view as an `orders:all` consumer.
- [x] 4.7 Test: backend publishes `order_state_changed` to the correct topic (`order:{id}`) so both consumer classes receive it appropriately.
- [x] 4.8 Implement/verify topic routing for order events end-to-end; run suites green.

## 5. Phase 5 — Kitchen recipe view + bidirectional inbound (PR5)

- [x] 5.1 Test: kitchen payload includes each product's full ingredient list with `nombre`+`es_removible` and resolves exclusion IDs to names (P1.4 backend).
- [x] 5.2 Implement P1.4 backend — join `product_ingredients → ingredients` in the kitchen payload builder; resolve exclusions to names.
- [ ] 5.3 Test (vitest): `KitchenOrderDetail` renders ingredient names + full list; no "Ingrediente #N".
- [ ] 5.4 Implement P1.4 frontend — render names + full list in `KitchenOrderDetail.tsx` (replace `:73` raw-ID rendering).
- [x] 5.5 Test: inbound message router dispatches by `type`; unknown/malformed frames return an error frame without crashing; `subscribe` honored only within JWT scope.
- [x] 5.6 Implement P0.3 — replace the disconnect-only `receive_text()` loop with the typed inbound router.
- [x] 5.7 Test: `kitchen.ingredient_unavailable` is authorized for COCINA/ADMIN only (CLIENT rejected) and routes to the messaging service handler.
- [x] 5.8 Implement the inbound `kitchen.ingredient_unavailable` handler (auth re-check + handoff to Phase 6 service stub).
- [ ] 5.9 Run backend websocket/kitchen suite + frontend cocina suite green.

## 6. Phase 6 — Ingredient availability + kitchen→admin signalling (PR6)

### 6a. Data model + migrations
- [x] 6.1 Test: `Ingrediente.activo` defaults to `true` for new and existing rows; the column is NOT NULL.
- [x] 6.2 Implement the `Ingrediente.activo: bool` column (`catalog/models.py`) + Alembic migration adding `activo BOOLEAN NOT NULL DEFAULT true`; `downgrade()` drops the column.
- [x] 6.3 Test: `HistorialDisponibilidadIngrediente` model/migration — columns (`ingrediente_id`, `reportado_por`, `pedido_id`, `creado_en`, `resuelto_en` nullable, `resuelto_por` nullable); `pendiente`/`resuelto` derived from `resuelto_en`; `downgrade()` drops the table.
- [x] 6.4 Implement the `HistorialDisponibilidadIngrediente` model (table `ingredient_availability_history`, `BaseModel`-based since rows mutate on resolution, following the `HistorialEstadoPedido` precedent) + Alembic migration.

### 6b. Report + resolution services (UoW)
- [x] 6.5 Test: reporting an ingredient unavailable sets `Ingrediente.activo=false` AND appends one `HistorialDisponibilidadIngrediente` row (`resuelto_en=NULL`) inside ONE UoW; survives with no admin connected.
- [x] 6.6 Implement the report service — UoW: toggle `activo=false` + insert history row; on commit publish `ingredient_unavailable_reported` (best-effort) to the admin scope.
- [x] 6.7 Test: resolving sets `Ingrediente.activo=true` AND bulk-closes ALL open rows for that ingredient (`resuelto_en`+`resuelto_por` on every `resuelto_en IS NULL` row) inside ONE UoW; resolved rows retained.
- [x] 6.8 Implement the resolution service — UoW: toggle `activo=true` + bulk-close open rows; on commit publish `ingredient_availability_restored` (best-effort) to `kitchen:all`.
- [x] 6.9 Test: the "Faltantes" query returns only open shortages (`resuelto_en IS NULL`); a separate query returns resolved history.
- [x] 6.10 Implement the open-shortages + resolved-history queries.

### 6c. FSM availability guard (D6b)
- [ ] 6.11 Test: single-line order requiring an `activo=false` ingredient (not excluded) → `CONFIRMADO → EN_PREPARACION` raises `BusinessRuleError` (422) naming the ingredient.
- [ ] 6.12 Test: order where the `activo=false` ingredient is excluded in ALL lines → advance allowed.
- [ ] 6.13 Test: two-line order — line A excludes the `activo=false` ingredient, line B requires it → `EN_PREPARACION → TERMINADO` blocked (order-level).
- [ ] 6.14 Test: block lifts after the ingredient returns to `activo=true`; guard does NOT intervene on non-kitchen transitions (e.g. cancellation).
- [ ] 6.15 Implement the availability guard in the service layer (eager-load `producto.ingredientes` to avoid N+1), invoked from `avanzar_estado` before `validate_transition`, only for `CONFIRMADO → EN_PREPARACION` and `EN_PREPARACION → TERMINADO`. `state_machine.py` stays pure.

### 6d. Inbound WS handler + admin read/resolve endpoints
- [ ] 6.16 Test: the `kitchen.ingredient_unavailable` handler (Phase 5 stub) now invokes the report service with `order_id`+`ingredient_id`; CLIENT still rejected.
- [ ] 6.17 Implement the handler → report-service wiring (replacing the Phase 5 stub).
- [ ] 6.18 Test: admin "Faltantes" endpoint lists open shortages; resolve endpoint sets `activo=true` + bulk-closes + emits the restored event.
- [ ] 6.19 Implement the admin Faltantes list + resolve endpoints/service.

### 6e. Frontend
- [ ] 6.20 Test (vitest): cook trigger in `KitchenOrderDetail` (only for `CONFIRMADO`/`EN_PREPARACION`) sends `kitchen.ingredient_unavailable` with `order_id`+`ingredient_id`; cook receives `ingredient_availability_restored`.
- [ ] 6.21 Implement P0.1 frontend (cook) — "mark unavailable" trigger in `KitchenOrderDetail.tsx` + restored notification handling.
- [ ] 6.22 Test (vitest): navbar inbox indicator shows a live badge on `ingredient_unavailable_reported` and loads open shortages on open; the "Faltantes" view (comidas section of the admin sidebar) lists open shortages and resolves with a friendly label.
- [ ] 6.23 Implement P0.1 frontend (admin) — navbar inbox indicator + "Faltantes" view (open + resolved/audit) in the comidas sidebar section + resolve action.
- [ ] 6.24 Run full backend + frontend suites green; end-to-end smoke of cook report → admin Faltantes → resolve → cook notified → order advance unblocked.

## 7. Cross-cutting verification

- [ ] 7.1 Confirm `main.py` has exactly one realtime touchpoint (`register_realtime`) and no broker/Redis dependency was added.
- [ ] 7.2 Confirm `orders/service.py` has no `features.cocina` import and publishes only via the port.
- [ ] 7.3 Confirm no client receives another client's `order:{id}` events (anti-leak) across the full flow.
- [ ] 7.4 Confirm 30s polling fallback still works with the WS forced offline.
