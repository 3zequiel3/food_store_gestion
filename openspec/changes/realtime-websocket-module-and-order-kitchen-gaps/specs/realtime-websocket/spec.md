## ADDED Requirements

### Requirement: WebSocket transport lives in its own module

The system SHALL host the real-time transport in `backend/features/websocket/`, owning the WS endpoint, the connection manager, the `EventPublisher` port, the event contract, the inbound message router, and the drain/broadcast service. No other feature module SHALL own WebSocket connection state.

#### Scenario: Connection manager is not under the kitchen feature
- **WHEN** the codebase is inspected after this change
- **THEN** the connection manager, `/ws` endpoint, and drain task live under `backend/features/websocket/` and `backend/features/cocina/` no longer defines `ws_manager` nor a `/ws` route

#### Scenario: Kitchen consumes the shared transport
- **WHEN** the KDS receives a real-time order update
- **THEN** the update is delivered through the `backend/features/websocket/` transport, not a kitchen-owned manager

### Requirement: Single register_realtime touchpoint in main

The system SHALL expose `register_realtime(app)` from the websocket module as the ONLY realtime touchpoint in `backend/main.py`. The call MUST mount the WS routes, start the drain/broadcast task, and bind the `EventPublisher` implementation.

#### Scenario: main.py calls register_realtime once
- **WHEN** `backend/main.py` is inspected
- **THEN** the lifespan invokes `register_realtime(app)` exactly once and contains no direct references to the connection manager, the event queue, or the drain task

#### Scenario: WS routes are available after startup
- **WHEN** the application has started
- **THEN** `/ws` (WebSocket) and `/ws/health` (HTTP) are both routable

### Requirement: EventPublisher port defines the versioned event contract

The system SHALL define an `EventPublisher` port (interface) that the order domain depends on instead of importing any kitchen module. Published events MUST carry a version field `v`, a domain `type`, a routing `topic`, a `payload`, and a timestamp `ts`. The port's `publish` method MUST be best-effort and MUST NOT raise to its caller.

#### Scenario: Orders publish through the port, not the kitchen
- **WHEN** `backend/features/orders/service.py` is inspected after this change
- **THEN** it publishes via the `EventPublisher` port and contains no `from features.cocina` import

#### Scenario: Published event carries the versioned contract
- **WHEN** an order state transition publishes an event
- **THEN** the event is `{ "v": 1, "type": "order_state_changed", "topic": "order:<id>", "payload": {...}, "ts": <iso8601> }`

#### Scenario: Publish never breaks the HTTP response
- **WHEN** the drain task or broadcast fails while a state transition is committing
- **THEN** the HTTP response for the transition still succeeds and the failure is swallowed (best-effort), logged at debug level

### Requirement: Topic/room subscription with server-side scope validation

The system SHALL filter broadcasts by topic so a connection only receives events for topics within its JWT-derived scope. A CLIENT connection MAY subscribe only to `order:{id}` topics for orders it owns; ADMIN/PEDIDOS MAY subscribe to `orders:all`; COCINA/ADMIN MAY subscribe to `kitchen:all`. The server MUST validate any client-requested topic against the JWT scope and MUST NOT trust a client-declared scope.

#### Scenario: Client receives only its own order events
- **GIVEN** a CLIENT connected and subscribed to `order:10` which it owns
- **WHEN** an event is published to `order:11` (a different client's order)
- **THEN** the first client does NOT receive that event

#### Scenario: Client cannot subscribe to another client's order
- **GIVEN** a CLIENT that does not own order 11
- **WHEN** it sends `{ "type": "subscribe", "topic": "order:11" }`
- **THEN** the server rejects the subscription (anti-leak) and does not deliver `order:11` events to it

#### Scenario: Admin receives all order events
- **GIVEN** an ADMIN subscribed to `orders:all`
- **WHEN** events are published to `order:10` and `order:11`
- **THEN** the admin receives both

#### Scenario: Cocina receives kitchen events
- **GIVEN** a COCINA connection subscribed to `kitchen:all`
- **WHEN** a kitchen-relevant order event is published
- **THEN** the COCINA connection receives it

### Requirement: Bidirectional inbound message router

The system SHALL parse inbound WebSocket messages and dispatch them by `type` through a router. Unknown or malformed inbound messages MUST be rejected with an error frame and MUST NOT close or crash the connection. Inbound message types that perform privileged actions MUST re-check authorization against the connection's JWT.

#### Scenario: Subscribe message is handled
- **WHEN** a client sends `{ "v": 1, "type": "subscribe", "topic": "order:10" }` for an order it owns
- **THEN** the connection is subscribed to `order:10`

#### Scenario: Unknown inbound type is rejected without crashing
- **WHEN** a client sends `{ "type": "definitely_not_a_real_type" }`
- **THEN** the server replies with an error frame and the connection stays open

#### Scenario: Cook ingredient-unavailable message requires COCINA/ADMIN
- **GIVEN** a connection whose JWT has only CLIENT
- **WHEN** it sends `{ "type": "kitchen.ingredient_unavailable", "payload": { "order_id": 123, "ingredient_id": 7 } }`
- **THEN** the server rejects it (unauthorized) and does not toggle `activo` nor create a report row

#### Scenario: Cook ingredient-unavailable carries order and ingredient
- **GIVEN** a COCINA connection
- **WHEN** it sends `{ "v": 1, "type": "kitchen.ingredient_unavailable", "payload": { "order_id": 123, "ingredient_id": 7 } }`
- **THEN** the router hands the payload (`order_id`, `ingredient_id`) to the kitchen-availability service handler

### Requirement: Outbound ingredient-availability notifications

The system SHALL publish, over the versioned event contract, an `ingredient_unavailable_reported` event to the admin scope when a cook reports an ingredient unavailable, and an `ingredient_availability_restored` event to the `kitchen:all` topic when an admin resolves a shortage. Both publishes MUST be best-effort and MUST NOT break the originating request.

#### Scenario: Report emits an admin-scoped event
- **WHEN** a cook reports ingredient 7 of order 123 unavailable
- **THEN** an event `{ "v": 1, "type": "ingredient_unavailable_reported", "topic": "orders:all", "payload": { "ingrediente_id": 7, "pedido_id": 123, ... } }` is published to the admin scope

#### Scenario: Resolution emits a kitchen-scoped event
- **WHEN** an admin resolves the shortage for ingredient 7
- **THEN** an event `{ "v": 1, "type": "ingredient_availability_restored", "topic": "kitchen:all", "payload": { "ingrediente_id": 7, ... } }` is published to the kitchen topic

### Requirement: WS health endpoint for degraded mode

The system SHALL expose `GET /ws/health` returning the transport status (drain task alive, current connection count) so the frontend can detect a degraded transport and fall back to polling. The frontend's existing 30-second polling fallback MUST be preserved.

#### Scenario: Health endpoint reports operational transport
- **WHEN** the drain task is running
- **THEN** `GET /ws/health` returns HTTP 200 with a body indicating the transport is healthy

#### Scenario: Frontend keeps polling when disconnected
- **GIVEN** a frontend consumer whose WebSocket is disconnected
- **WHEN** it cannot reach the WS transport
- **THEN** it continues to poll the relevant REST endpoint every 30 seconds

### Requirement: In-process transport with documented single-instance limitation

The system SHALL keep the transport in-process within `main:app` (no Redis, NATS, or separate service). The single-instance limitation MUST be documented: real-time delivery only spans one backend process; multi-instance fan-out would require an external bus and is out of scope.

#### Scenario: No external broker dependency is introduced
- **WHEN** the dependency manifest and runtime config are inspected after this change
- **THEN** no Redis/NATS/message-broker dependency or separate WS service is added

#### Scenario: Limitation is documented
- **WHEN** `design.md` of this change is read
- **THEN** it states that in-process WS only delivers within a single backend instance and that the `EventPublisher` port allows a future broker-backed implementation
