## MODIFIED Requirements

### Requirement: Outbound ingredient-availability notifications

The system SHALL publish, over the versioned event contract, an `ingredient_unavailable_reported` event to the admin scope when a cook reports an ingredient unavailable, and an `ingredient_availability_restored` event to the `kitchen:all` topic when an admin resolves a shortage. Both publishes MUST be best-effort and MUST NOT break the originating request. Both publishes MUST occur AFTER the database transaction that mutates the underlying `ingrediente` and `ingredient_availability_history` rows has COMMITTED — never inside the open `UnitOfWork` and never between `session.flush()` and `__exit__`. A consumer receiving the WS event and immediately issuing a REST GET for the affected resource MUST observe the committed state.

#### Scenario: Report emits an admin-scoped event

- **WHEN** a cook reports ingredient 7 of order 123 unavailable
- **THEN** an event `{ "v": 1, "type": "ingredient_unavailable_reported", "topic": "orders:all", "payload": { "ingrediente_id": 7, "pedido_id": 123, ... } }` is published to the admin scope

#### Scenario: Resolution emits a kitchen-scoped event

- **WHEN** an admin resolves the shortage for ingredient 7
- **THEN** an event `{ "v": 1, "type": "ingredient_availability_restored", "topic": "kitchen:all", "payload": { "ingrediente_id": 7, ... } }` is published to the kitchen topic

#### Scenario: Publishes happen post-commit, not pre-commit

- **GIVEN** an admin resolves the shortage for ingredient 7 inside a `UnitOfWork`
- **WHEN** the `ingredient_availability_restored` event reaches the drain task
- **THEN** a fresh database read from an independent transaction observes `Ingrediente(7).activo == true` AND every previously open `ingredient_availability_history` row for ingredient 7 has `resuelto_en` populated

#### Scenario: Consumer refetch after the event sees the committed state

- **GIVEN** a cocina consumer subscribed to `kitchen:all`
- **WHEN** it receives an `ingredient_availability_restored` event for ingredient 7 and immediately fetches `GET /api/v1/cocina/pedidos`
- **THEN** the response reflects `activo == true` for ingredient 7 with no need for a second fetch or page reload

## ADDED Requirements

### Requirement: Synthetic connection_resynced event on subscription registration

The system SHALL emit a single-recipient `connection_resynced` event to a WebSocket connection IMMEDIATELY AFTER that connection has been registered as a subscriber to a topic — both for the implicit auto-subscription performed at handshake time (via `default_topic`) AND for every successful explicit `subscribe` message handled by the inbound router. The event MUST NOT be broadcast to other connections. The event carries the topic and a server-side timestamp so the consumer can deterministically refetch its REST view and recover from any missed broadcast during the connection (re)establishment window.

#### Scenario: Auto-subscription at handshake emits resync to the new connection

- **GIVEN** a COCINA client opens `WS /ws?token=<valid-jwt>` and is auto-subscribed to `kitchen:all` via `default_topic`
- **WHEN** the connection has been added to `ConnectionManager`
- **THEN** the server sends to this connection (and to no other) `{ "v": 1, "type": "connection_resynced", "topic": "kitchen:all", "payload": { "topic": "kitchen:all", "server_ts": "<iso8601>" } }`

#### Scenario: Explicit subscribe emits resync after the ack

- **GIVEN** an ADMIN connection with scope `orders_all=true`
- **WHEN** the client sends `{ "v": 1, "type": "subscribe", "topic": "orders:all" }` and the server accepts the subscription
- **THEN** the server sends, to this connection only, a `subscribe_ack` envelope followed by `{ "v": 1, "type": "connection_resynced", "topic": "orders:all", "payload": { "topic": "orders:all", "server_ts": "<iso8601>" } }`

#### Scenario: Rejected subscribe does NOT emit a resync

- **GIVEN** a CLIENT connection that does not own order 99
- **WHEN** the client sends `{ "v": 1, "type": "subscribe", "topic": "order:99" }`
- **THEN** the server rejects the subscribe and emits NO `connection_resynced` event for `order:99`

#### Scenario: Resync targets only the originating socket

- **GIVEN** two COCINA connections C1 and C2 already subscribed to `kitchen:all`
- **WHEN** a third COCINA connection C3 connects and is auto-subscribed to `kitchen:all`
- **THEN** the `connection_resynced` envelope is delivered to C3 only; C1 and C2 receive no such envelope

### Requirement: Drain task uses the running asyncio loop bound by the FastAPI lifespan

The system SHALL bind the in-process event drain task to the asyncio loop that is currently running inside the FastAPI lifespan context. Implementations MUST call `asyncio.get_running_loop()` (or the equivalent obtained via `asyncio.create_task` from within an async context) and MUST NOT call `asyncio.get_event_loop()`. A regression test MUST fail if the deprecated `asyncio.get_event_loop()` is reintroduced in `backend/features/websocket/registration.py`.

#### Scenario: Lifespan registration uses the running loop

- **WHEN** `register_realtime(app)` is invoked from the FastAPI lifespan
- **THEN** the drain task is scheduled on `asyncio.get_running_loop()` and the deprecated `asyncio.get_event_loop()` is NOT called

#### Scenario: Regression guard catches reintroduction of the deprecated call

- **WHEN** the regression test inspects `backend/features/websocket/registration.py`
- **THEN** the test fails if the source contains `asyncio.get_event_loop` outside of comments or docstrings
