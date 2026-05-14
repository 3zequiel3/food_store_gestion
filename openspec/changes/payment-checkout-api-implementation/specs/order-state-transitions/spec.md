# Delta Spec: Order State Transitions

## Capability
`order-state-transitions`

## Requirement: FSM-Enforced Order State Transitions

### Scenario: Valid transition by authorized role
- **Given** an order in state `PENDIENTE`
- **When** an admin or pedidos user calls `POST /api/v1/pedidos/{id}/transicionar` with `estado_codigo_destino: "CONFIRMADO"`
- **Then** the order moves to `CONFIRMADO`
- **And** a `HistorialEstadoPedido` record is appended with `estado_anterior_codigo: "PENDIENTE"`, `estado_nuevo_codigo: "CONFIRMADO"`, `cambiado_por_id: <user_id>`, timestamp
- **And** the response returns `TransicionarResponse` with the new state and full history

### Scenario: Invalid FSM transition blocked
- **Given** an order in state `EN_PREPARACION`
- **When** a user calls `POST /api/v1/pedidos/{id}/transicionar` with `estado_codigo_destino: "ENTREGADO"`
- **Then** the request returns `400 Bad Request`
- **And** the error message indicates the transition is not allowed (e.g., "No se puede transicionar de EN_PREPARACION a ENTREGADO")
- **And** the order state does NOT change

### Scenario: Unauthorized role blocked
- **Given** an order in state `EN_PREPARACION`
- **When** a `PEDIDOS` user calls transicionar with `estado_codigo_destino: "CANCELADO"`
- **Then** the request returns `403 Forbidden` (only ADMIN can cancel from EN_PREPARACION per RN-RB08)
- **And** the order state does NOT change

### Scenario: Terminal state is immutable
- **Given** an order in state `ENTREGADO` (terminal)
- **When** any user calls transicionar with any destination state
- **Then** the request returns `400 Bad Request`
- **And** the order state does NOT change

### Scenario: Cancelled state is immutable
- **Given** an order in state `CANCELADO` (terminal)
- **When** any user calls transicionar with any destination state
- **Then** the request returns `400 Bad Request`
- **And** the order state does NOT change

### Scenario: SYSTEM transition (webhook payment approval)
- **Given** an order in state `PENDIENTE`
- **When** the MercadoPago webhook receives a payment notification with `status: "approved"`
- **Then** the system calls `transicionar_estado(actor_id=None)` to move to `CONFIRMADO`
- **And** the `HistorialEstadoPedido` record has `cambiado_por_id: NULL` (system actor)
- **And** the order state becomes `CONFIRMADO`

### Scenario: Client can only cancel from PENDIENTE
- **Given** an order in state `PENDIENTE`
- **When** the order owner (CLIENT role) calls transicionar with `estado_codigo_destino: "CANCELADO"`
- **Then** the transition succeeds (CLIENT is allowed per TRANSITION_ROLES)
- **And** the order state becomes `CANCELADO`

### Scenario: Client cannot cancel after CONFIRMADO
- **Given** an order in state `CONFIRMADO`
- **When** the order owner (CLIENT role) calls transicionar with `estado_codigo_destino: "CANCELADO"`
- **Then** the request returns `403 Forbidden` (CLIENT is not in the allowed roles for CONFIRMADO→CANCELADO)

## API Contract

### POST `/api/v1/pedidos/{pedido_id}/transicionar`

**Request:**
```json
{
  "estado_codigo_destino": "CONFIRMADO"
}
```

**Success Response (200):**
```json
{
  "pedido_id": 1,
  "estado_anterior": "PENDIENTE",
  "estado_nuevo": "CONFIRMADO",
  "historial": [
    {
      "id": 1,
      "estado_codigo": "CONFIRMADO",
      "estado_anterior_codigo": "PENDIENTE",
      "cambiado_por_id": 5,
      "cambiado_en": "2026-05-14T12:00:00Z",
      "motivo": null
    }
  ]
}
```

**Error Response (400 — Invalid FSM):**
```json
{
  "detail": "No se puede transicionar de EN_PREPARACION a ENTREGADO. Transiciones válidas: EN_CAMINO, CANCELADO"
}
```

**Error Response (403 — Insufficient role):**
```json
{
  "detail": "No tenés permisos para transicionar de EN_PREPARACION a CANCELADO."
}
```

**Error Response (404 — Order not found):**
```json
{
  "detail": "Pedido no encontrado"
}
```

## Valid Transitions (FSM)

| From State | To States |
|------------|-----------|
| PENDIENTE | CONFIRMADO (webhook only), CANCELADO (client/pedidos/admin) |
| CONFIRMADO | EN_PREPARACION (pedidos/admin), CANCELADO (pedidos/admin) |
| EN_PREPARACION | EN_CAMINO (pedidos/admin), CANCELADO (admin only) |
| EN_CAMINO | ENTREGADO (pedidos/admin) |
| ENTREGADO | _(terminal)_ |
| CANCELADO | _(terminal)_ |

## Frontend Requirements

### Order Timeline Display
- Show ordered states: PENDIENTE → CONFIRMADO → EN_PREPARACION → EN_CAMINO → ENTREGADO
- Completed states: checkmark icon, green color
- Current state: highlighted/active
- Future states: greyed out
- CANCELADO: shown in red, replaces future states when applicable

### Transition Buttons (Admin/Pedidos)
- Show buttons only for valid next states per FSM + user role
- Button labels: "Confirmar", "Preparar", "En camino", "Entregado", "Cancelar"
- Disable buttons for states the user role cannot perform
- After successful transition: refetch order, update timeline

### Cancel Button (Client)
- Show "Cancelar pedido" button only when order is in `PENDIENTE`
- Hide/disable for all other states
- Confirmation modal before cancel
