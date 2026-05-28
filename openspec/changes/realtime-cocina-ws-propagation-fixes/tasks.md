## 1. Phase 1 — Backend: publish-after-commit for availability (Bug 1)

- [x] 1.1 Write failing pytest in `backend/tests/features/availability/test_publish_after_commit.py` that uses a fake `EventPublisher` whose `publish(event)` opens an independent DB connection and asserts `Ingrediente.activo == true` (resolve path) and the corresponding `ingredient_availability_history` rows are committed; assert the test FAILS against the current code path.
- [x] 1.2 Refactor `backend/features/availability/service.py`: change `report_unavailable` to return a `ReportResult` DTO (ingrediente_id, pedido_id, reportado_por, timestamp, history_id) and STOP calling `_publish_report_event` from inside the service body. Same for `resolve_availability` → returns `ResolveResult` (ingrediente_id, resolved_count, resolved_at, resuelto_por). Keep the private `_publish_*` helpers in the module so the topic/payload contract has one home.
- [x] 1.3 Update `backend/features/availability/router.py`: in `reportar_faltante` and `resolver_faltante`, capture the DTO inside `with UnitOfWork():`, exit the `with` block, THEN call the publish helper with the DTO. Mirror the pattern in `backend/features/orders/router.py` / `orders/service.py:transicionar_estado`.
- [x] 1.4 Update any existing unit tests in `backend/tests/features/availability/` that asserted publish-from-service behaviour so they now assert publish-from-router.
- [x] 1.5 Run the failing test from 1.1 → assert it PASSES. Re-run the full `availability` test module to confirm no regressions.

## 2. Phase 2 — Backend: drain task uses `get_running_loop` (Bug 2b)

- [x] 2.1 Write failing pytest-asyncio test in `backend/tests/features/websocket/test_registration_running_loop.py` that imports `backend/features/websocket/registration.py` source as text and asserts the substring `asyncio.get_event_loop(` is NOT present outside comments/docstrings. Confirm the test FAILS against current code.
- [x] 2.2 Replace the `asyncio.get_event_loop()` call in `backend/features/websocket/registration.py:71` with `asyncio.get_running_loop()`. Ensure the call site is reached only from within the FastAPI lifespan async context (lifespan IS the natural caller of `register_realtime`).
- [x] 2.3 Run the regression test from 2.1 → PASSES. Run the existing websocket test suite to confirm no behavioural regression.

## 3. Phase 3 — Backend: synthetic `connection_resynced` envelope (Bug 2a, server side)

- [x] 3.1 Write failing pytest in `backend/tests/features/websocket/test_resync_on_subscribe.py` that opens a WS connection as COCINA, waits for the first non-handshake frame, and asserts it is `{ "v": 1, "type": "connection_resynced", "topic": "kitchen:all", "payload": { "topic": "kitchen:all", "server_ts": <iso8601> } }`. Confirm it FAILS.
- [x] 3.2 Write a second failing test in the same module: open as ADMIN, send `{ "v": 1, "type": "subscribe", "topic": "orders:all" }`, assert the server returns `subscribe_ack` followed by `connection_resynced` for `orders:all`. Confirm FAIL.
- [x] 3.3 Write a third failing test: open as CLIENT not owning order 99, send `subscribe` for `order:99`, assert NO `connection_resynced` envelope is emitted (only the rejection). Confirm FAIL or PASS-by-accident — adjust test to be reliable.
- [x] 3.4 In `backend/features/websocket/router.py` (or wherever `websocket_endpoint` and `_handle_subscribe` live), after the connection is added to `ConnectionManager` for the auto-subscribed `default_topic`, send the `connection_resynced` envelope to that single websocket. After every successful `_handle_subscribe`, send the same envelope (immediately after the existing `subscribe_ack`).
- [x] 3.5 Re-run tests 3.1, 3.2, 3.3 → all PASS. Run the broader websocket test suite to confirm no regression in subscribe/unsubscribe/broadcast paths.
- [x] 3.6 Add a fourth test asserting the resync is delivered ONLY to the originating socket (two pre-existing connections C1 and C2 on the same topic do NOT receive the resync emitted for a third connection C3).

## 4. Phase 4 — Frontend: handle `connection_resynced` in cocina and order hooks (Bug 2a, client side)

- [ ] 4.1 Write failing vitest in `frontend/src/features/cocina/hooks/__tests__/useCocinaWebSocket.test.ts` (create if missing): push a synthetic `{ type: "connection_resynced", topic: "kitchen:all", payload: { ... } }` into the hook's `handleEvent` and assert `queryClient.invalidateQueries` was called with `["cocina","pedidos"]`. Confirm FAIL.
- [ ] 4.2 Add a `case "connection_resynced":` (or matching `if` branch) in `frontend/src/features/cocina/hooks/useCocinaWebSocket.ts:handleEvent` that calls the existing `invalidateAndRefresh()`. Leave the `onopen → invalidateAndRefresh` belt-and-braces fallback intact.
- [ ] 4.3 Re-run vitest 4.1 → PASS.
- [ ] 4.4 Write failing vitest for `frontend/src/features/orders/hooks/useOrderWebSocket.ts` asserting the same handler is added; then implement and confirm PASS.

## 5. Phase 5 — Frontend: single resolver button in Faltantes (Bug 3)

- [ ] 5.1 Write failing vitest in `frontend/src/pages/admin/__tests__/AdminFaltantesPage.test.tsx` rendering the page with one open shortage and asserting: exactly one element with role/name "Resolver" AND exactly one `<select>` with options `solucionado` and `comprado` are present per row. No second primary CTA for the same endpoint. Confirm FAIL.
- [ ] 5.2 Write a second failing vitest asserting that clicking "Resolver" with the selector set to `comprado` triggers the mutation with body `{ accion: "comprado" }`; and that the default click (selector untouched) sends `{ accion: "solucionado" }`. Confirm FAIL.
- [ ] 5.3 Refactor `frontend/src/pages/admin/AdminFaltantesPage.tsx`: replace the two buttons with one primary "Resolver" button + adjacent native `<select>` with two options, default `solucionado`. Wire the selected value into the existing `useResolverFaltante` mutation as the `accion` payload field.
- [ ] 5.4 Re-run vitests 5.1, 5.2 → PASS. Lint pass with `pnpm lint` to ensure no unused imports left from the removed second button.

## 6. Phase 6 — Verification + smoke

- [ ] 6.1 Run `pytest backend/tests/features/availability backend/tests/features/websocket` and assert all green.
- [ ] 6.2 Run `pnpm test --filter @app/frontend` (or the project's vitest command) for cocina hooks, order hooks, and admin pages — all green.
- [ ] 6.3 Manual smoke 1 (faltantes): with backend + frontend running, log in as admin, open Faltantes, open a second tab as cocina. Admin clicks Resolver (label `comprado`) on an open shortage. Cocina view unblocks the ingredient within 1 s with no manual reload. Confirm the order's blocked badge clears.
- [ ] 6.4 Manual smoke 2 (pedidos entrantes / reconnect): log in as cocina. Force a backend restart (or simulate by closing the WS via devtools). On reconnect, place a new order via the client checkout (EFECTIVO path). Confirm the new order appears in the KDS with no manual reload, even with the reconnect happening concurrently with the order publish.
- [ ] 6.5 Smoke 3 (UX): on the Faltantes page, confirm exactly ONE "Resolver" button + one `<select>` per row. Confirm default selector value is `solucionado`. Confirm switching to `comprado` and clicking sends the correct `accion`.
- [ ] 6.6 Confirm no `asyncio.get_event_loop` warning in backend logs during boot under uvicorn with `--reload`.
- [ ] 6.7 Update `openspec/changes/realtime-cocina-ws-propagation-fixes/tasks.md` checkboxes as work progresses (automatic during `/opsx:apply`). Do NOT archive until the user reviews.
