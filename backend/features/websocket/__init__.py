"""
WebSocket module — shared real-time transport for Food Store.

Owns:
- EventPublisher port (Protocol) + DomainEvent versioned contract
- ConnectionManager with topic indexing
- InProcessEventPublisher + drain/broadcast service
- WS endpoint + /ws/health + register_realtime(app)

Single-instance limitation: delivery is in-process only.
Multi-instance fan-out would require an external bus (out of scope, see design.md D1).
"""
