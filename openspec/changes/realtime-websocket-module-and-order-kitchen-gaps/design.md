## Context

Today the real-time transport is physically nested inside the kitchen feature:

- `backend/features/cocina/ws_manager.py` — a `set()`-based singleton connection manager (server→client push only).
- `backend/features/cocina/router.py` — the `/ws` endpoint; its `receive_text()` loop is a pure disconnect detector ("KDS clients don't send messages").
- `backend/features/cocina/service.py` — the `asyncio.Queue` drain task, `_STATE_TO_EVENT` mapping, and `publish_transition_event`.
- `backend/features/orders/service.py:296-301` — after a transition commits, it does `from features.cocina.service import publish_transition_event` and calls it inside `try/except: pass` (best-effort).
- `backend/main.py:108-115` — the lifespan reaches into cocina to `start_drain_task`.

Two structural problems follow from "WS is owned by cocina":
1. **Only the KDS gets realtime.** Client and admin order-detail views (`OrderDetailModal.tsx`) poll. The frontend already falls back to 30s polling when disconnected — that resilience is real and must be preserved.
2. **Inverted dependency.** The order domain imports the kitchen feature to broadcast. The order domain should emit a domain event and not know any screen exists.

The owner also confirmed (engram `architecture/websocket-module`, decision #3306) that a separate WS microservice was **rejected**: the resilience goal already largely exists, and a broker would add failure surface, not remove it. The agreed path is **modularize, do not distribute**.

A prior gap analysis (engram `sdd/order-kitchen-gap-analysis/explore`, #3305) provides file:line evidence for every business-logic gap addressed here.

Project constraints that bound this design: FastAPI + SQLModel/SQLAlchemy, Alembic for schema, the Unit-of-Work pattern for any multi-table write, the import golden rule (no service↔router cycles; `state_machine.py` stays pure), `pnpm`, conventional commits, English for code/UI strings/comments. Live `order-state-machine` spec text references a `TERMINADO` rename that is **not** reflected in the current code (the running FSM still has `EN_CAMINO`); this change targets the **current code reality** and notes the divergence where relevant.

## Goals / Non-Goals

**Goals:**
- Extract the realtime transport into `backend/features/websocket/` with a clean port (`EventPublisher`) and a single `register_realtime(app)` touchpoint in `main.py`.
- Invert the orders→cocina coupling: orders emit domain events against the port.
- Add topic/room filtering so a client subscribes to **their own order**, an admin to **all orders**, and cocina to **all kitchen orders** — over one transport.
- Add a bidirectional inbound message router (client→server) with a defined contract; first inbound use case is the cook's ingredient-unavailable message.
- Fix the prioritized order/kitchen gaps (P0.1, P0.2, P0.3, P1.4, P1.5, P1.6, P2.7, P2.8, P3.9, P3.10, P3.11).
- Keep best-effort publish + add `/ws/health` for degraded-mode UX. Preserve 30s polling.

**Non-Goals:**
- No Redis / NATS / external broker. No separate WS service. Single-instance only (documented limitation).
- No formal recipes module (ingredients↔products entity with quantities/instructions). P1.4 only surfaces the existing `product_ingredients` list with names.
- No change to the MercadoPago online-checkout flow beyond what P0.2/P2.8 require.
- No multi-instance fan-out; horizontal scale would require a future change introducing a bus (out of scope).
- No numeric ingredient stock / `cantidad`. The new `activo` flag is boolean availability only — it does not model or touch stock.
- No client-facing unavailability UX: notifying the client, ingredient-swap, and admin-cancel-with-reason are explicitly deferred to a later, carefully-designed change. This change stops at kitchen→admin signalling + the FSM advance-block.

## Decisions

### D1 — In-process module, not a microservice
**Choice:** keep the WS inside `main:app`, same process/port, refactored into `backend/features/websocket/`.
**Why:** the resilience the user wanted is already present in two layers — best-effort publish wrapped in `except: pass` (`orders/service.py:300-301`) and the frontend's 30s polling fallback. A separate service forces a broker (Redis/NATS) and network hop = **more** failure surface for a uni-thesis project — the classic distributed-monolith trap. Modularizing instead gives a clean seam: a future extraction becomes mechanical (swap the in-process `EventPublisher` impl for a broker-backed one) without paying the distributed-systems tax now. Matches `docs/CHANGES.md:336` ("WebSocket en proceso… Sin Redis").
**Alternative considered:** Railway/Docker WS service with Redis Pub/Sub — rejected per #3306.
**Documented limitation:** works with a single backend instance only; multi-instance requires an external bus.

### D2 — `EventPublisher` port + versioned event contract
**Choice:** define `EventPublisher` as an interface (Python `Protocol` / ABC) in `backend/features/websocket/`. The order domain depends on this port, not on a concrete manager.

```python
class EventPublisher(Protocol):
    def publish(self, event: DomainEvent) -> None: ...  # sync, best-effort, never raises
```

The event payload is **versioned** so consumers can evolve:

```jsonc
{
  "v": 1,
  "type": "order_state_changed",   // domain event type (not a kitchen verb)
  "topic": "order:123",            // routing key (see D4)
  "payload": { "order_id": 123, "estado": "EN_PREPARACION", "...": "..." },
  "ts": "2026-05-21T23:00:00Z"
}
```

**Why versioned + domain-named:** the current `_STATE_TO_EVENT` map emits kitchen verbs (`pedido_en_preparacion`). That couples the contract to the kitchen view. The port emits **domain** events (`order_state_changed`, `order_created`, `kitchen_message_created`); each consumer interprets them. `v` lets us add fields without breaking older clients.
**Concrete impl:** `InProcessEventPublisher` enqueues onto the existing `asyncio.Queue` drained by the broadcast task — the proven mechanism, just relocated.
**Alternative:** orders calls the manager directly — rejected, that is the coupling we are removing.

### D3 — Single `register_realtime(app)` touchpoint
**Choice:** the module exposes `register_realtime(app)`; `main.py` lifespan calls it once. It mounts the WS router (`/ws`, `/ws/health`), starts the drain task, and binds the `InProcessEventPublisher` singleton.
**Why:** `main.py` should not know about queues, drain tasks, or managers. One call = the entire realtime surface. Replaces the current inline `start_drain_task` block (`main.py:108-115`) and the cocina router mount for `/ws`.

### D4 — Topic/room subscription model
**Choice:** each connection declares a **subscription scope** derived from its JWT at handshake, never trusted from the client:
- CLIENT → may subscribe only to `order:{id}` topics for orders they own (ownership checked server-side, anti-leak 404/close semantics like `orders/service.py`).
- ADMIN / PEDIDOS → `orders:all` (every `order:*`).
- COCINA / ADMIN → `kitchen:all` (kitchen-relevant orders).

The manager stores connections indexed by topic; `broadcast(event)` fans out only to connections subscribed to `event.topic`. The client may send a `subscribe` inbound message naming a topic, but the server **validates** the requested topic against the JWT scope before honoring it.
**Why:** one transport, three consumer classes, zero data leaks. A client must never receive another client's order events. This is exactly the seam missing today (gap #5): because WS was kitchen-owned, only `kitchen:all` existed.
**Alternative:** per-consumer endpoints (`/ws/kitchen`, `/ws/orders`) — rejected; duplicates auth + lifecycle and re-nests transport in features.

### D5 — Inbound message router (bidirectional, P0.3)
**Choice:** replace the disconnect-only `receive_text()` loop with a router that parses inbound JSON and dispatches by `type`:

```jsonc
// client → server
{ "v": 1, "type": "subscribe", "topic": "order:123" }
{ "v": 1, "type": "kitchen.ingredient_unavailable",
  "payload": { "order_id": 123, "ingredient_id": 7 } }
```

Unknown/invalid types are rejected with an error frame (never crash the socket). `kitchen.ingredient_unavailable` is authorized for COCINA/ADMIN only (re-checked against JWT), then handed to the kitchen-availability service (D6). The cook reports against an **order + ingredient** (the order where they detected the shortage); `activo` is a global ingredient flag, so a per-line `detalle_id` is not required to toggle it — the report row records `pedido_id` for traceability of where it was detected.

Outbound notifications the server emits (over the versioned contract, D2):

```jsonc
// server → admin (topic orders:all / admin scope) — fed by HistorialDisponibilidadIngrediente
{ "v": 1, "type": "ingredient_unavailable_reported",
  "topic": "orders:all",
  "payload": { "ingrediente_id": 7, "ingrediente_nombre": "cebolla",
               "pedido_id": 123, "reportado_por": 9, "reporte_id": 55 } }

// server → cocina (topic kitchen:all) — on admin resolution
{ "v": 1, "type": "ingredient_availability_restored",
  "topic": "kitchen:all",
  "payload": { "ingrediente_id": 7, "ingrediente_nombre": "cebolla", "resuelto_por": 2 } }
```
**Why:** the cook action must flow over the WS (P0.3), not only REST. A typed router keeps the contract explicit and lets future inbound types (e.g. heartbeats, presence) slot in.
**Note:** the service-layer write still goes through the normal sync UoW path (scheduled off the event loop) so the persistence model stays consistent; the WS is transport, not a second persistence path.

### D6 — Ingredient availability: `activo` flag + `HistorialDisponibilidadIngrediente` log (P0.1)

**Two DISTINCT, orthogonal ingredient attributes — do not conflate:**
- `es_removible` (ALREADY EXISTS, global on `Ingrediente`, `catalog/models.py:158`): whether the CLIENT may remove the ingredient from a product. Owned by the catalog/customization concern.
- `activo` (**NEW** boolean, default `true`, global on `Ingrediente`): KITCHEN availability — whether the kitchen currently has the ingredient. Owned by the kitchen-availability concern. **This is NOT stock**: there is no numeric `cantidad`, and it does not touch the catalog. Needs an Alembic migration adding the column with `server_default='true'`.

**NEW audit/event entity `HistorialDisponibilidadIngrediente`** (table `ingredient_availability_history`), following the `HistorialEstadoPedido` precedent (`orders/models.py:161`). **One row per report event**, append-on-report:

| Field | Type | Notes |
|-------|------|-------|
| `id` | PK | |
| `ingrediente_id` | FK `ingredients.id` | the unavailable ingredient |
| `reportado_por` | FK `users.id` | the cook who reported it |
| `pedido_id` | FK `orders.id` | the order where the cook detected the shortage (traceability) |
| `creado_en` | timestamptz | report timestamp (from base model) |
| `resuelto_en` | timestamptz, **nullable** | NULL ⇒ pending; set on resolution |
| `resuelto_por` | FK `users.id`, **nullable** | the admin who resolved it |

`pendiente` / `resuelto` is **DERIVED** from `resuelto_en` (`resuelto_en IS NULL` ⇒ pending) — there is **NO separate status column**. Because rows are mutated on resolution (`resuelto_en`, `resuelto_por`), this entity uses **`BaseModel`** (mutable), NOT `AppendOnlyBaseModel` — it diverges from `HistorialEstadoPedido` (which is append-only) precisely on this point: the log is append-on-report but close-on-resolve.

**This single log IS the message/notification source.** There is **NO third "messages" entity** (the previous `kitchen_admin_messages` table is dropped from this design). The history table holds the full lifecycle (an ingredient can go unavailable→available many times — many rows) AND feeds the admin inbox / "Faltantes" view / cook notifications.

**Report flow (cook → server):**
1. Cook viewing an order in `CONFIRMADO` or `EN_PREPARACION` marks one of that order's ingredients unavailable (cocina UI trigger → inbound WS `kitchen.ingredient_unavailable`).
2. Inside ONE **UnitOfWork**: set `Ingrediente.activo = false` (global) AND insert a `HistorialDisponibilidadIngrediente` row (`resuelto_en = NULL`).
3. On commit, publish `ingredient_unavailable_reported` (best-effort) to the admin scope → the navbar inbox updates live; an admin connecting later loads open shortages from persistence.

**Resolution flow (admin → server):**
1. Admin opens the "Faltantes" view (open shortages = `resuelto_en IS NULL`), resolves with a friendly label ("ingrediente comprado" / "solucionado").
2. Inside ONE UoW: set `Ingrediente.activo = true` AND **bulk-close** ALL open rows for that ingredient (`UPDATE … SET resuelto_en = now(), resuelto_por = :admin WHERE ingrediente_id = :id AND resuelto_en IS NULL`).
3. On commit, publish `ingredient_availability_restored` (best-effort) to `kitchen:all` → the cook is notified. The FSM block (D6b) lifts automatically because it reads `activo`.

**Why durable persist + push:** an admin may be offline when the cook flags an item — WS delivery alone is insufficient. Persist first, then push.
**Why bulk-close on resolve:** `activo` is global, so restoring it logically resolves every pending report for that ingredient at once; keeping per-report `resuelto_en` preserves the full audit trail.
**Why keep resolved rows:** lifecycle is EXPLICIT resolution tied to the `activo` toggle; resolved rows are KEPT (audit) and surfaced in a separate/filtered "resolved history" view.
**Alternative rejected:** a separate `kitchen_admin_messages` table plus a status column — rejected; it duplicated the audit log and split the source of truth. One append-on-report/close-on-resolve log is the single source.

### D6b — FSM ingredient-availability guard (NEW requirement, joins P3.9/P3.10/P3.11)

**Choice:** before `validate_transition`, `avanzar_estado` runs an **availability guard** for the two kitchen-advancing transitions only:
- `CONFIRMADO → EN_PREPARACION`
- `EN_PREPARACION → TERMINADO`

The order is BLOCKED (raise `BusinessRuleError`, 422) if ANY of its order lines requires an ingredient with `activo = false` that is **NOT excluded** in that line's `personalizacion`.

**Exclusion-aware, per line, evaluated per order** (the FSM operates at the order level):

```text
guard(order):
  for each linea in order.detalles:
    producto_ingredientes = ingredients of linea.producto   # product_ingredients join
    excluidos = set(linea.personalizacion)                  # excluded ingredient ids
    for ing in producto_ingredientes:
      if ing.activo == False and ing.id not in excluidos:
        raise BusinessRuleError(blocked, naming ing.nombre)  # whole order blocked
  # else: allowed
```

- If the unavailable ingredient is removable AND the client excluded it in that line → that line does not block.
- But if ANY OTHER line in the order requires it (not excluded) → the WHOLE order is blocked.
- The block lifts automatically once the ingredient returns to `activo = true` (the guard re-reads `activo` each attempt; no separate unblock action).

**Where it lives:** the guard needs DB reads (order lines + their products' ingredients + `activo`), so it stays in the **service layer** (`orders/service.py`), invoked from `avanzar_estado` before `validate_transition`. `state_machine.py` stays pure (no DB) — consistent with the import golden rule.
**Why service-level, not in `ALLOWED_TRANSITIONS`:** the FSM matrix is static; availability is dynamic data. Encoding it in the matrix is impossible. The guard is a dynamic precondition, like the existing webhook-only CONFIRMADO defence.

### D7 — Cash-on-delivery path (P0.2)
**Choice:** remove the hard block at `orders/service.py:129-136`; add a dedicated checkout path (mirrors `crear_pedido_pickup_efectivo`) that accepts `EFECTIVO` **with** a `direccion_id`, computes `costo_envio = 50.00`, and creates the order in `PENDIENTE` with no `Pago` row. Add the request/response schema + router endpoint.
**Why:** the owner's flow allows pago al repartidor. The frontend **already** renders "Pago al repartidor" (`OrderDetailModal.tsx:35-37` — EFECTIVO + `direccion_snapshot`), so the UI already assumes this exists; only the backend blocks it. Keep cash+pickup unchanged.
**Alternative:** relax the block inside the generic `crear_pedido` — rejected; a dedicated path keeps validation explicit and parallels the existing cash-pickup service method, easing tests.

### D8 — Customization validation = removable ingredients of the product (P2.8)
**Choice:** at the checkout boundary, every customization (excluded) ingredient ID MUST be an `es_removible=true` ingredient associated with the ordered product (`product_ingredients` join + `Ingrediente.es_removible`). Reject otherwise with `BusinessRuleError` (422). `es_removible` is a **global** column on `Ingrediente` (`catalog/models.py:158`), not per-association.
**Why:** today `CheckoutItem.personalizacion` accepts any integer ≥ 1 (`checkout/schemas.py:21-30`). That lets a client "exclude" an ingredient the product does not have, or a non-removable one.
**Frontend alignment (P2.7):** `ProductFormModal.tsx:209` still passes `es_removible` per association to `addProductIngredient`; the column moved globally (migration 20260514_0000) and the backend ignores it. Drop the per-association argument; manage `es_removible` only on the ingredient entity.

### D9 — FSM corrections (P3.9, P3.10, P3.11)
- **P3.9:** add `("TERMINADO", "CANCELADO_ADMIN"): {"ADMIN"}` to `TRANSITION_ROLES`. The FSM already allows `TERMINADO → CANCELADO_ADMIN` (`state_machine.py:26`) but the RBAC map lacks the entry, so `validate_transition` always 403s. Owner intent: ADMIN can cancel from TERMINADO.
- **P3.10:** remove `ENTREGADO` from `ALLOWED_TRANSITIONS["CONFIRMADO"]` (`state_machine.py:24`) and drop `("CONFIRMADO","ENTREGADO")` from `TRANSITION_ROLES` (`:48`). This shortcut bypasses the kitchen and is not in the owner's flow.
- **P3.11:** the admin UI offers "Confirmar pedido" → CONFIRMADO for PENDIENTE (`OrderStateActions.tsx:17`), but CONFIRMADO is webhook/payment-driven (`avanzar_estado` blocks manual CONFIRMADO, `service.py:458-461`). Remove that button from the PENDIENTE transition set so the UI matches backend intent; PENDIENTE admin actions become reject-only.
**Why grouped:** all three are small, surgical edits in two files (`state_machine.py`, `OrderStateActions.tsx`) and share the same risk surface (FSM/RBAC tests). Doing them together avoids three half-PRs touching the same matrix.

### D10 — Recipe name join for the kitchen payload (P1.4)
**Choice:** the kitchen payload builder joins `product_ingredients → ingredients` to attach `{id, nombre, es_removible}` for each product's full ingredient list, plus resolves the `personalizacion` exclusion IDs to names. `KitchenOrderDetail.tsx` renders names and the full list instead of "Ingrediente #N" (`KitchenOrderDetail.tsx:73`).
**Why:** the cook needs to read the recipe, not decode IDs. This uses the **existing** `Producto.ingredientes` relationship (`products/models.py:132`) — no new entity (recipes module stays out of scope).

### D11 — Phasing (foundation-first)
Foundation must land before the features that ride it:
1. **Phase 1 — WebSocket module foundation**: extract manager + port + contract + drain + `register_realtime`; invert orders→cocina; KDS keeps working through the new transport (parity, no behavior change yet). Topic/room model + `/ws/health`.
2. **Phase 2 — FSM fixes**: P3.9, P3.10, P3.11 (pure domain + small UI; independent, low-risk, lands early to de-risk the matrix). The dynamic availability guard (D6b) is NOT here — it depends on the `activo` flag introduced in Phase 6.
3. **Phase 3 — Business logic**: P0.2 cash-on-delivery; P2.8 customization validation; P2.7 frontend `es_removible` alignment; P1.6 pre-checkout removable step.
4. **Phase 4 — Realtime consumers**: P1.5 wire client + admin order-detail as topic/room consumers (polling fallback preserved).
5. **Phase 5 — Kitchen recipe view + bidirectional**: P1.4 recipe-name join + UI; P0.3 inbound message router.
6. **Phase 6 — Ingredient availability + kitchen→admin signalling**: P0.1 — the `Ingrediente.activo` column + migration; the `HistorialDisponibilidadIngrediente` model + migration; the report service (UoW: toggle `activo=false` + insert row) and resolution service (UoW: toggle `activo=true` + bulk-close); the FSM availability guard (D6b) wired into `avanzar_estado`; the admin navbar inbox + "Faltantes" view + resolution action; the cook mark-unavailable trigger; outbound `ingredient_unavailable_reported` / `ingredient_availability_restored` notifications. Depends on Phase 5 inbound router + Phase 4 admin consumer. The FSM guard is grouped here (not in Phase 2) because it needs `activo` to exist.

## Risks / Trade-offs

- **[Single-instance limitation]** → In-process WS only delivers within one backend process. Mitigation: documented explicitly here and in `docs/CHANGES.md:336`; the `EventPublisher` port makes a broker-backed impl a drop-in for a future scale-out change. No multi-instance promise made.
- **[Refactor regresses KDS during extraction]** → moving the manager could break live KDS pushes. Mitigation: Phase 1 is parity-only (KDS behavior unchanged); TDD — characterization tests on the current broadcast behavior run green before and after the move.
- **[Cross-client data leak via topics]** → a client could try to subscribe to another client's `order:{id}`. Mitigation: D4 validates every requested topic against JWT-derived scope server-side; ownership re-checked exactly like `orders/service.py` anti-leak 404.
- **[Inbound WS as an unguarded write path]** → bidirectional opens a new surface. Mitigation: typed router, per-type RBAC re-checked against JWT, persistence still via UoW; unknown frames rejected, never crash the socket.
- **[Best-effort publish hides failures]** → swallowing publish errors can mask a broken drain task. Mitigation: `/ws/health` surfaces drain-task/queue state; failures are logged at debug; the HTTP response is intentionally never coupled to publish success.
- **[Large change → review fatigue]** → exceeds a 400-line single PR by a wide margin. Mitigation: **chained PRs recommended** (one per phase); see tasks Review Workload Forecast.
- **[order-state-machine spec vs code divergence]** → live spec mentions a `TERMINADO` rename absent from running code. Mitigation: this change's delta targets the **current** code matrix and calls out the divergence; it does not re-litigate the rename.
- **[Availability guard read cost / N+1]** → the D6b guard reads each line's product ingredients per advance attempt. Mitigation: it only runs on the two kitchen-advancing transitions (not every transition), and the order's lines/products are already loaded in `avanzar_estado`'s context; eager-load `producto.ingredientes` to avoid N+1.
- **[`activo` vs `es_removible` conflation]** → the two flags are semantically close (both global booleans on `Ingrediente`) and could be mixed up in code/tests. Mitigation: distinct names, distinct concerns documented in D6 and the `removable-ingredients` spec; the guard reads `activo`, customization validation reads `es_removible`.
- **[Permanent block if admin never resolves]** → an order stays blocked while `activo=false`. Mitigation: this is intended (the kitchen genuinely lacks the ingredient); the navbar inbox + "Faltantes" view surface the pending shortage so the admin acts. Client-facing swap/cancel UX is deferred (out of scope).

## Migration Plan

- **Schema (Phase 6):** two Alembic migrations — (1) add `Ingrediente.activo BOOLEAN NOT NULL DEFAULT true` (`downgrade()` drops the column; existing rows backfill to `true` via the server default); (2) create `ingredient_availability_history` (`downgrade()` drops the table). No further data backfill needed. The previously-planned `kitchen_admin_messages` table is NO LONGER created (superseded by `HistorialDisponibilidadIngrediente`).
- **Code rollout order = phase order (D11).** Each phase is independently shippable behind the parity guarantee of Phase 1.
- **Rollback:** Phases 2–6 are additive or surgical and revert cleanly. Phase 1 rollback = restore the cocina-owned transport (kept in git history); because Phase 1 is parity-only, reverting it does not change observable behavior beyond module location.
- **No env/config changes**, no new services, no new runtime dependencies.

## Resolved Questions

- **Admin inbox surface — RESOLVED:** a NAVBAR inbox indicator (live badge on `ingredient_unavailable_reported`) PLUS a dedicated **"Faltantes" view** in the comidas section of the admin sidebar (table of open shortages, `resuelto_en IS NULL`), with a separate filtered "resolved history" view for audit. NOT a drawer.
- **Availability lifecycle — RESOLVED:** EXPLICIT resolution tied to the `activo` toggle. The admin resolves ("ingrediente comprado" / "solucionado") → `activo = true` → bulk-close all open report rows for that ingredient. Resolved rows are KEPT in `HistorialDisponibilidadIngrediente` (`resuelto_en`/`resuelto_por`) for audit. No auto-resolve on order state change.

## Open Questions

- Should `order_created` also push to the admin `orders:all` topic so the admin list updates live on new orders, or is that out of P1.5 scope? (Default: in scope for admin consumer; client only gets its own `order:{id}`.)
