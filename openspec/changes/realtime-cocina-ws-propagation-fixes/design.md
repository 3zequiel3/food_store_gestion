## Context

`realtime-websocket-module-and-order-kitchen-gaps` (status: complete, not yet archived) introduced the `features/websocket/` module, the `EventPublisher` port, the in-process drain loop, and the kitchen↔admin realtime flows. On commit `bf4a109` a post-implementation audit (Engram #3374 exploration + #3375 root-cause) found three concrete delivery defects that this change closes.

Current state (post `bf4a109`):

- `backend/features/availability/service.py:147-154` — `_publish_restore_event(...)` is called inside `resolve_availability`, which the router (`backend/features/availability/router.py:127-132`) runs inside `with UnitOfWork():`. The publish fires post-flush but pre-commit. `report_unavailable` exhibits the same pattern.
- `backend/features/orders/service.py:432-436` — `_publish_order_state_event` is called AFTER the `with UnitOfWork():` block in `transicionar_estado`. This is the canonical pattern. Availability must mirror it.
- `backend/features/websocket/registration.py:71` — uses `asyncio.get_event_loop()` (deprecated since 3.10). Under uvicorn `--reload` this can yield a loop that is not the one running the drain.
- `frontend/src/features/cocina/hooks/useCocinaWebSocket.ts:79` — `await getToken()` runs before every `new WebSocket(...)`. The reconnect window is wide enough to drop broadcasts.
- `backend/features/websocket/router.py` — `_handle_subscribe` sends a `subscribe_ack` envelope on success but does NOT send any synthetic event to trigger a refetch by the consumer.
- `frontend/src/pages/admin/AdminFaltantesPage.tsx` — renders two distinct buttons ("ingrediente comprado", "solucionado") that POST to the same `POST /api/v1/availability/faltantes/{ingrediente_id}/resolver` endpoint with different `accion` strings. `backend/features/availability/schemas.py:40` defines `accion: str = "solucionado"`.

Constraints:

- Strict TDD is the project default. Every backend change is preceded by a failing test.
- Multi-table writes stay inside `with UnitOfWork():`.
- No contract break: `connection_resynced` is additive on the wire; frontend handlers that ignore unknown types continue to work.
- `pnpm`, not npm.
- The `realtime-websocket-module-and-order-kitchen-gaps` change is NOT archived yet, so the modified capabilities (`realtime-websocket`, `kitchen-admin-messaging`) live in that change's `specs/`. The delta requirements in this change copy the full block from that source.

Stakeholders: cocinero (KDS), administrador (Faltantes inbox + resolver UI), system reliability (no missed events on reconnect, no stale REST after WS).

## Goals / Non-Goals

**Goals:**

- Cocina sees state transitions and ingredient-availability restores on the first WS event, with no manual reload and no race against a pre-commit transaction.
- After every (re)connect or explicit subscribe, the connection is brought up-to-date by a server-emitted `connection_resynced` event that triggers a deterministic `invalidateAndRefresh()` on the consumer side.
- The drain task is anchored to the loop that actually runs it, with a regression test that fails if anyone reintroduces `asyncio.get_event_loop()`.
- Admin sees ONE "Resolver" control in Faltantes; the audit label (`comprado` / `solucionado`) is a discreet selector, not a duplicated CTA.

**Non-Goals:**

- No singleton `OrdersWsProvider` refactor (audit Gap B — duplicate ADMIN WS connections). Deferred.
- No `FaltantesBadge` cold-start seeding from REST (audit Gap D). Deferred.
- No changes to the MercadoPago webhook flow.
- No changes to the order FSM, `_KITCHEN_STATES`, topic naming, or scope-derivation rules.
- No changes to the `AvailabilityResolveRequest` schema or the `/resolver` endpoint signature.
- No aggressive token caching as the primary fix for reconnect races. Token cache is an optional optimization, not the safety mechanism — the synthetic resync is the safety mechanism.

## Decisions

### Decision 1 — Move availability publishes to the router, AFTER the UoW commits

**What**: `report_unavailable` and `resolve_availability` return small DTOs (e.g. `ReportResult { ingrediente_id, pedido_id, reportado_por, history_id, ... }` and `ResolveResult { ingrediente_id, resolved_count, ... }`). The router calls them inside `with UnitOfWork():`, then exits the `with` block (commit happens here), then invokes the publish helper with the DTO data. The private `_publish_report_event` / `_publish_restore_event` helpers stay in the service module (so the topic/payload contract has one home) but are invoked by the router, not by the service body.

**Why over alternatives**:

- *Option A (chosen)* — publish from the router after `with UoW()`. Minimal blast radius, exact mirror of the working pattern in `OrderService.transicionar_estado` (which is called from `orders/router.py` post-UoW in `transicionar_estado` itself; the order service moved publish OUT of the UoW block in its own body — same idea applied here, just at the router layer because availability already has `UoW` at the router layer).
- *Option B (rejected)* — `post_commit_callbacks` list on `UnitOfWork`. Larger surface area, touches every UoW caller, and the abstraction (deferred-side-effect queue per UoW) is overkill for two callsites.
- *Option C (rejected)* — call `uow.commit()` manually then publish inside the `with` block. Breaks the context-manager contract; the `__exit__` would then double-commit or no-op depending on implementation.

**Consequence**: `_publish_*` helpers become small DTO-fed functions; the router gains 1–2 lines per endpoint. The service is decoupled from the publisher concern, which is also a design win.

### Decision 2 — Synthetic `connection_resynced` envelope on auto-subscribe AND explicit subscribe-ack

**What**: After the server adds a connection to a topic (via `default_topic` at handshake OR via a successful `_handle_subscribe`), it sends, to that specific socket only, a JSON envelope:

```json
{ "v": 1, "type": "connection_resynced", "topic": "<topic>", "payload": { "topic": "<topic>", "server_ts": "<iso8601>" } }
```

Frontend handlers (`useCocinaWebSocket.handleEvent`, `useOrderWebSocket.handleEvent`) add a branch `if (event.type === "connection_resynced") { invalidateAndRefresh(); return; }`. The existing `onopen → invalidateAndRefresh` stays as a belt-and-braces fallback for the very first connection (where the server emit may race with `onopen` registration on the client).

**Why over alternatives**:

- *Aggressive token caching alone (rejected)* — reduces the probability of a missed broadcast but never eliminates it. A 1-RTT cached `getToken()` can still lose to a broadcast that fires between `decode_access_token` accepting the JWT and `manager.subscribe(...)` actually inserting the connection. The synthetic resync converts a probabilistic race into a deterministic invariant: "after every successful subscribe, the consumer refetches once."
- *Server-side event replay buffer (rejected for now)* — would let us replay the last N events on resubscribe. Higher complexity (per-topic ring buffer, ordering guarantees), and `invalidateAndRefresh()` already converges to truth via REST. The synthetic resync is the minimal fix that achieves the same observable behaviour.

**Cost**: one extra WS frame per (re)connect and per explicit subscribe (typically 1–3 frames per session). One REST refetch per resync. Acceptable.

**Consequence**: `connection_resynced` MUST be sent only to the originating socket, never broadcast. It MUST be sent AFTER the connection is registered in the manager (otherwise the client may not have its handler attached yet — but since `connection_resynced` is delivered on its own WS, the handler IS attached by the time the frame arrives, by virtue of `ws.onmessage` being a property of the same socket).

### Decision 3 — `asyncio.get_running_loop()` from inside the lifespan

**What**: Replace `asyncio.get_event_loop()` in `backend/features/websocket/registration.py:71` with `asyncio.get_running_loop()`. The call site moves into (or is invoked from) the FastAPI lifespan async function, which guarantees a running loop. Add a pytest-asyncio regression test that fails if `asyncio.get_event_loop` is called from `registration` (via monkeypatch / source assertion) so a future refactor cannot regress.

**Why over alternatives**:

- *Pass the loop explicitly into `register_realtime(app, loop=...)`* (rejected) — forces every caller (including tests) to know about the loop. `get_running_loop()` is the modern idiomatic equivalent and is what the FastAPI/Starlette docs recommend.
- *`asyncio.new_event_loop()`* (rejected) — would create a second loop and the drain task would run on the wrong one.

### Decision 4 — Single resolver button + `<select>` audit label in `AdminFaltantesPage`

**What**: Replace the two CTAs ("Ingrediente comprado", "Solucionado") with one primary "Resolver" button and a small native `<select>` immediately adjacent. Default value: `solucionado`. Other option: `comprado`. On click, the mutation POSTs to the same `/resolver` endpoint with the selected `accion`. The selector is `<select>` not a custom Combobox to keep the UI tight and zero-dependency.

**Why**: the `accion` field is informational (audit / future analytics), not a state-changer. Two buttons implied two endpoints / two different effects. One button + label is honest UX.

**Trade-off**: a tiny extra click for the most common case (open select → choose comprado). Mitigated by sensible default. The audit data quality improves because admins now consciously choose the label rather than tapping the first button they see.

### Decision 5 — Test strategy

- **Bug 1 (post-commit publish)**: integration test in `tests/features/availability/` that registers a fake `EventPublisher` whose `publish(event)` queries the DB synchronously. If `activo` is not committed at publish time, the test asserts via `SELECT ... FROM ingrediente WHERE id=...` (using a separate connection / `READ COMMITTED` semantics) that the row has the new value. Replicates the user-observed race.
- **Bug 2a (resync emit)**: backend test that opens a WS, asserts the first non-ack frame is `connection_resynced` for the auto-subscribed topic. Second test sends an explicit `subscribe` and asserts a `connection_resynced` frame follows the `subscribe_ack` (or replaces it — design decides; current direction is that `subscribe_ack` stays and `connection_resynced` is sent immediately after).
- **Bug 2b (asyncio modernization)**: a pytest-asyncio test that imports `registration` and asserts `asyncio.get_event_loop` is NOT referenced in its source (or, alternatively, monkeypatches `asyncio.get_event_loop` to raise and confirms `register_realtime` still works).
- **Bug 3 (UX)**: vitest component test that renders `AdminFaltantesPage` with mocked queries, asserts exactly one "Resolver" button + one `<select>` are rendered per row, switches the select to `comprado`, clicks, and verifies the mutation was called with `accion: "comprado"`.
- Frontend handler test: vitest test for `useCocinaWebSocket` that pushes a `connection_resynced` event into the hook and asserts `queryClient.invalidateQueries` was called with `["cocina","pedidos"]`.

## Risks / Trade-offs

- **[Risk]** The `connection_resynced` envelope doubles the refetches on first connect (existing `onopen → invalidateAndRefresh` PLUS the new server-emitted event) → **Mitigation**: keep the `onopen` invalidate as a fallback (it costs one extra REST GET on the very first connection, which is acceptable; subsequent reconnects gain correctness). Alternative mitigation if cost matters: gate the client `onopen` invalidate behind `if (firstConnect) ...` and rely solely on the server resync from then on.
- **[Risk]** Some pre-existing tests assert publish-from-service behaviour (i.e. that `report_unavailable` ALONE publishes) → **Mitigation**: update those tests in the same task that moves the publish; failing test on purpose first (TDD).
- **[Risk]** The synthetic resync arrives BEFORE the client's `onmessage` handler is attached → **Mitigation**: a WS frame is queued by the browser until the handler is registered (the WS API delivers messages that arrived between `onopen` and `onmessage` registration to the next-registered handler), but the safer pattern is to send `connection_resynced` ONLY after the server has confirmed the subscription is fully registered in `ConnectionManager`, which is naturally the case in `_handle_subscribe`. For the handshake/`default_topic` path, send it from inside `websocket_endpoint` right after `default_topic` registration.
- **[Risk]** The DTO refactor in `availability/service.py` ripples into callers (router only, but tests may import the service directly) → **Mitigation**: keep return types explicit and typed; existing private `_publish_*` helpers stay reachable from the router so a single import in the router covers both endpoints.
- **[Trade-off]** Single endpoint + selector for resolver dropdown: simpler UI, slightly worse glanceability of "what action did this admin take?" — mitigated by the fact that the audit log row still carries `accion` and admins now choose it deliberately.

## Migration Plan

- **Deploy order**: backend first (DTO refactor + resync emit + asyncio modernization), then frontend (handler + button consolidation). Backend changes are backwards-compatible with the current frontend (the new `connection_resynced` frame is ignored by a frontend that doesn't know about it). Frontend changes are forwards-compatible with the old backend (no `connection_resynced` arrives, the existing `onopen` fallback still works).
- **Rollback**: each Phase commit is independently revertable. Phase 5 (UX) is pure frontend and can be reverted without touching backend.
- **No DB migration**: no schema changes.

## Open Questions

- Should the existing `subscribe_ack` envelope be merged with `connection_resynced` to save one frame? Current direction: keep them separate (ack = "your subscribe succeeded", resync = "now go refetch") for clarity. Revisit if frame count becomes a concern.
- Should we add the `connection_resynced` handler in `useOrderWebSocket` too, so admin Faltantes and FaltantesBadge benefit from the same guarantee? Current direction: yes, add it as a parallel one-liner; it costs nothing and closes the same gap for admins. Confirmed in Phase 4 tasks.
