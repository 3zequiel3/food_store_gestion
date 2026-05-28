## Why

The previous change `realtime-websocket-module-and-order-kitchen-gaps` (status: complete, 77/77 tasks) shipped the WebSocket transport module and the kitchen↔admin realtime flows, but a post-commit audit on `bf4a109` surfaced three concrete, user-visible breakages in the delivery:

1. **Stale REST refetch after resolver** — `IngredientAvailabilityService.resolve_availability` publishes `ingredient_availability_restored` while the `UnitOfWork` is still open. Cocina receives the WS event, invalidates the `["cocina","pedidos"]` query, refetches `/cocina/pedidos`, and reads `activo=False` because the UoW has not committed yet. The ingredient stays blocked in the kitchen view until the next 30 s poll. `IngredientAvailabilityService.report_unavailable` exhibits the same pre-commit publish pattern on the admin side. The publish-after-commit pattern is already used correctly in `orders/service.py:432-436` — availability must mirror it.
2. **Missed broadcasts on WS reconnect** — `useCocinaWebSocket` does `await getToken()` (an HTTP round-trip) before each `new WebSocket(...)`. During that async window the connection is not in `connection_manager`, so any `kitchen:all` broadcast is silently dropped. There is no server-side replay on (re)subscribe, so the kitchen can stay desynchronized until a manual page reload. Compounded by `backend/features/websocket/registration.py:71` using `asyncio.get_event_loop()` (deprecated ≥ 3.10), which under `uvicorn --reload` can pin the drain task to a dead loop and silently swallow the entire queue.
3. **Duplicated resolver buttons** — `AdminFaltantesPage` renders two distinct buttons ("ingrediente comprado" and "solucionado") that hit the same `POST /api/v1/availability/faltantes/{ingrediente_id}/resolver` endpoint with different `accion` strings. The admin spec already treats this as a single action whose label is informational/audit-only.

This is post-archive cleanup of `realtime-websocket-module-and-order-kitchen-gaps`, not a new feature on the roadmap (`docs/CHANGES.md` is untouched).

## What Changes

- **Availability service — publish-after-commit (BUG 1)**: move `_publish_report_event` AND `_publish_restore_event` out of the service-internal flow and into the router, called AFTER the `with UnitOfWork():` block exits. Service methods return a small DTO (e.g. `ReportResult`, `ResolveResult`) carrying the data the router needs to emit the event. Mirrors the post-commit pattern already used in `orders/service.py:transicionar_estado`.
- **WS drain task — modern asyncio (BUG 2b)**: replace `asyncio.get_event_loop()` in `registration.py` with `asyncio.get_running_loop()`, invoked from inside the FastAPI lifespan async context where a running loop is guaranteed. Add a regression test under `pytest-asyncio` that fails if the deprecated call returns.
- **WS replay-on-subscribe — `connection_resynced` (BUG 2a)**: when a connection auto-subscribes at handshake (via `default_topic`) OR when it sends an explicit `subscribe` and is granted access, the server SHALL emit a synthetic `connection_resynced` event to that single connection. Payload carries `{ topic, server_ts }`. The frontend handler triggers `invalidateAndRefresh()` for that topic, closing any reconnect-race gap deterministically. This is safer than aggressive token caching alone because it converts a probabilistic race into a guaranteed resync.
- **Cocina hook — handles `connection_resynced` (BUG 2a, frontend)**: `useCocinaWebSocket.handleEvent` adds a branch for `type === "connection_resynced"` that calls the existing `invalidateAndRefresh()`. The existing `onopen → invalidateAndRefresh` stays as a belt-and-braces fallback.
- **Admin Faltantes — single resolver button (BUG 3)**: `AdminFaltantesPage` collapses the two buttons into one "Resolver" action + a small native `<select>` defaulting to `solucionado`, with `comprado` as the secondary option. The `accion` string is still POSTed to the same endpoint (informational/audit). No backend change in this slice — the `AvailabilityResolveRequest.accion` field already accepts both values.

## Capabilities

### New Capabilities

_None._

### Modified Capabilities

- `realtime-websocket`: tightens the publish contract (publish-after-commit) for the availability publishes referenced in the existing "Outbound ingredient-availability notifications" requirement, adds a new requirement for the synthetic `connection_resynced` replay event on auto-subscribe and explicit subscribe-ack, and adds a requirement that the drain task lifecycle uses `asyncio.get_running_loop()` from within the FastAPI lifespan.
- `kitchen-admin-messaging`: tightens the existing "Admin resolves an ingredient shortage" requirement so the admin UI presents ONE resolver control (a button plus a label selector for the audit `accion`), not two separate buttons. Backend behaviour (single endpoint, both `accion` strings accepted) is unchanged.

## Impact

- **Backend**:
  - `backend/features/availability/service.py` — return DTOs from `report_unavailable` and `resolve_availability`; remove the inline `_publish_*` calls (or keep them as private helpers invoked only by the router).
  - `backend/features/availability/router.py` — call publish helpers AFTER the `with UnitOfWork()` block in both `reportar_faltante` and `resolver_faltante`.
  - `backend/features/websocket/registration.py` — `get_running_loop()` migration.
  - `backend/features/websocket/router.py` (or `manager.py`) — emit the synthetic `connection_resynced` envelope to the single websocket on auto-subscribe at handshake and on each successful `_handle_subscribe`.
  - Backend tests: `tests/features/availability/` (post-commit assertion via DB-state at publish time), `tests/features/websocket/` (resync emit on both paths, `get_running_loop` regression).
- **Frontend**:
  - `frontend/src/features/cocina/hooks/useCocinaWebSocket.ts` — new `connection_resynced` branch in `handleEvent`.
  - `frontend/src/pages/admin/AdminFaltantesPage.tsx` — replace two buttons with one + `<select>`.
  - Frontend tests: vitest for the new dropdown behaviour and the `connection_resynced` handler.
- **APIs**: no contract change. The wire event `connection_resynced` is additive. The `AvailabilityResolveRequest` schema is unchanged.
- **Dependencies**: none new. Uses existing FastAPI lifespan + `pytest-asyncio` + `vitest`.
- **Out of scope**:
  - No changes to MercadoPago webhook flow.
  - No changes to the order FSM or `_KITCHEN_STATES`.
  - No redesign of the WS module structure, topic naming, or scope rules.
  - No singleton `OrdersWsProvider` refactor (Gap B from the audit) — deferred.
  - No badge cold-start seeding (Gap D from the audit) — deferred.
