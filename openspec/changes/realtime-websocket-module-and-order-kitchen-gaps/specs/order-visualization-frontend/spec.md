## ADDED Requirements

### Requirement: Client and admin order-detail views auto-update in real time

The system SHALL update the client and admin order-detail views in real time when an order's state changes, by subscribing to the WebSocket transport. A CLIENT view MUST subscribe to its own `order:{id}` topic; an ADMIN view MUST subscribe to all order events. The existing 30-second polling fallback MUST be preserved for when the WebSocket is unavailable.

#### Scenario: Client view updates on state change
- **GIVEN** a CLIENT viewing their own order's detail with a live WebSocket
- **WHEN** the order transitions to `EN_PREPARACION`
- **THEN** the client's view reflects the new state without a manual refresh

#### Scenario: Admin view updates on state change
- **GIVEN** an ADMIN viewing an order's detail with a live WebSocket
- **WHEN** the order transitions
- **THEN** the admin's view reflects the new state without a manual refresh

#### Scenario: Polling fallback when WebSocket is down
- **GIVEN** an order-detail view whose WebSocket is disconnected
- **WHEN** the state changes on the server
- **THEN** the view picks up the change via the 30-second polling fallback

#### Scenario: Client cannot observe another client's order
- **GIVEN** a CLIENT viewing their own order
- **WHEN** a different client's order changes state
- **THEN** the first client receives no update for that other order
