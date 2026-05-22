# Delta Spec: Order State Transitions

## Capability
`order-state-transitions`

## Requirement: FSM-Enforced Order State Transitions

### Scenario: Valid transition by authorized role (PENDIENTE → CANCELADO_ADMIN)
- **Given** an order in state `PENDIENTE`
- **When** an admin calls `POST /api/v1/pedidos/{id}/transicionar` with `estado_codigo_destino: "CANCELADO_ADMIN"` and a valid `motivo`
- **Then** the order moves to `CANCELADO_ADMIN`
- **And** a `HistorialEstadoPedido` record is appended with the `motivo`
- **And** the response returns `TransicionarResponse` with the new state and full history

### Scenario: Invalid FSM transition blocked
- **Given** an order in state `EN_PREPARACION`
- **When** a user calls transicionar with `estado_codigo_destino: "ENTREGADO"`
- **Then** the request returns `400 Bad Request`
- **And** the error message indicates the transition is not allowed
- **And** the order state does NOT change

### Scenario: Unauthorized role blocked (EN_PREPARACION → CANCELADO_ADMIN by PEDIDOS)
- **Given** an order in state `EN_PREPARACION`
- **When** a `PEDIDOS` user calls transicionar with `estado_codigo_destino: "CANCELADO_ADMIN"`
- **Then** the request returns `403 Forbidden` (only ADMIN can cancel from EN_PREPARACION per RN-RB08)

### Scenario: Terminal state is immutable
- **Given** an order in state `ENTREGADO`
- **When** any user calls transicionar with any destination state
- **Then** the request returns `400 Bad Request`

### Scenario: CANCELADO_ADMIN is immutable
- **Given** an order in state `CANCELADO_ADMIN`
- **When** any user calls transicionar
- **Then** the request returns `400 Bad Request`

### Scenario: CANCELADO_CLIENTE is immutable
- **Given** an order in state `CANCELADO_CLIENTE`
- **When** any user calls transicionar
- **Then** the request returns `400 Bad Request`

### Scenario: SYSTEM transition (webhook payment approval)
- **Given** an order in state `PENDIENTE`
- **When** the MercadoPago webhook receives `status: "approved"`
- **Then** the system calls `transicionar_estado(actor_id=None)` to move to `CONFIRMADO`
- **And** the history record has `cambiado_por_id: NULL` (system actor)

### Scenario: Client can cancel from PENDIENTE
- **Given** an order in state `PENDIENTE` owned by the CLIENT user
- **When** the CLIENT calls transicionar with `estado_codigo_destino: "CANCELADO_CLIENTE"`
- **Then** the transition succeeds
- **And** the order state becomes `CANCELADO_CLIENTE`

### Scenario: Client cannot cancel from EN_PREPARACION or later
- **Given** an order in state `EN_PREPARACION` owned by the CLIENT user
- **When** the CLIENT calls transicionar with `estado_codigo_destino: "CANCELADO_CLIENTE"`
- **Then** the request returns `403 Forbidden`
- **And** the error message indicates: "Tu pedido ya está en preparación y no puede ser cancelado."

### Scenario: ADMIN cancel requires motivo
- **Given** any order not in terminal state
- **When** an admin calls transicionar with `estado_codigo_destino: "CANCELADO_ADMIN"` and empty `motivo`
- **Then** the request returns `400 Bad Request`
- **And** the error message: "Debes indicar el motivo del rechazo."

### Scenario: EN_CAMINO only for delivery orders
- **Given** an order with `direccion_entrega_id IS NULL` (pickup)
- **When** a user calls transicionar with `estado_codigo_destino: "EN_CAMINO"`
- **Then** the request returns `400 Bad Request`
- **And** the error message: "El estado EN_CAMINO solo aplica para pedidos con envío."

## Valid Transitions (FSM)

| From State | To States | Roles | Motivo Required |
|------------|-----------|-------|-----------------|
| PENDIENTE | CONFIRMADO | SISTEMA (webhook only) | No |
| PENDIENTE | CANCELADO_ADMIN | ADMIN, PEDIDOS | Yes |
| PENDIENTE | CANCELADO_CLIENTE | CLIENT (owner only) | No |
| CONFIRMADO | EN_PREPARACION | PEDIDOS, ADMIN | No |
| CONFIRMADO | CANCELADO_ADMIN | PEDIDOS, ADMIN | Yes |
| EN_PREPARACION | EN_CAMINO | PEDIDOS, ADMIN (delivery only) | No |
| EN_PREPARACION | CANCELADO_ADMIN | ADMIN only | Yes |
| EN_CAMINO | ENTREGADO | PEDIDOS, ADMIN | No |
| ENTREGADO | _(terminal)_ | — | — |
| CANCELADO_ADMIN | _(terminal)_ | — | — |
| CANCELADO_CLIENTE | _(terminal)_ | — | — |

## API Contract

### POST `/api/v1/pedidos/{pedido_id}/transicionar`

**Request:**
```json
{
  "estado_codigo_destino": "CANCELADO_ADMIN",
  "motivo": "Producto sin stock, cliente notificó que prefiere otro día"
}
```

**Success Response (200):**
```json
{
  "pedido_id": 1,
  "estado_anterior": "PENDIENTE",
  "estado_nuevo": "CANCELADO_ADMIN",
  "historial": [
    {
      "id": 1,
      "estado_anterior_codigo": null,
      "estado_nuevo_codigo": "PENDIENTE",
      "cambiado_por_id": 3,
      "motivo": null,
      "creado_en": "2026-05-14T10:00:00Z"
    },
    {
      "id": 2,
      "estado_anterior_codigo": "PENDIENTE",
      "estado_nuevo_codigo": "CANCELADO_ADMIN",
      "cambiado_por_id": 1,
      "motivo": "Producto sin stock, cliente notificó que prefiere otro día",
      "creado_en": "2026-05-14T10:05:00Z"
    }
  ]
}
```

**Error Response (400 — Invalid FSM):**
```json
{ "detail": "No se puede transicionar de EN_PREPARACION a ENTREGADO. Transiciones válidas: EN_CAMINO, CANCELADO_ADMIN" }
```

**Error Response (400 — Missing motivo):**
```json
{ "detail": "Debes indicar el motivo del rechazo." }
```

**Error Response (403 — Insufficient role):**
```json
{ "detail": "Tu pedido ya está en preparación y no puede ser cancelado. Contactanos si necesitás ayuda." }
```

**Error Response (404 — Order not found):**
```json
{ "detail": "Pedido no encontrado" }
```

## Frontend Requirements

### Order Timeline Display
- States: PENDIENTE → CONFIRMADO → EN_PREPARACION → EN_CAMINO → ENTREGADO
- Completed: checkmark icon, green
- Current: highlighted/active
- Future: greyed out
- CANCELADO_ADMIN / CANCELADO_CLIENTE: shown in red, replaces future states
- Show client-facing labels: "Pendiente de confirmación", "Pagado y confirmado", "En preparación", "En camino", "Entregado", "Cancelado (admin)", "Cancelado (cliente)"

### Transition Buttons (Admin/Pedidos)
- Show only valid next states per FSM + user role
- Button labels: "Confirmar" (webhook only, no button), "Preparar", "En camino", "Entregado", "Rechazar"
- "Rechazar" opens modal requiring `motivo` input
- "En camino" only shown if order has delivery (`direccion_entrega_id IS NOT NULL`)

### Cancel Button (Client)
- Show "Cancelar pedido" only when order is `PENDIENTE`
- For `EN_PREPARACION` and later: disabled button with tooltip message
- Confirmation modal before cancel (optional `motivo` field)
