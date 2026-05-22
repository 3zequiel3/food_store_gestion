# Design: Payment API Integration, Order State Guards & UI Fixes

## Technical Approach

### 1. Checkout API Migration

Replace `crear_preferencia()` (Checkout Pro) with `crear_pago_api()` that calls `sdk.payment().create()`. **No branching, no fallback** — Checkout Pro is removed entirely. Frontend uses `@mercadopago/sdk-js` Secure Fields (iframes) for PCI-compliant card tokenization: card data never touches our DOM or server.

**Idempotency**: The frontend generates `idempotency_key` via `crypto.randomUUID()` before each payment attempt and passes it in the request. The backend forwards this key to MP via `RequestOptions.custom_headers` and stores it in the `payments` table. This prevents double-charging on network retries — if the frontend resends the same request, MP sees the same key and ignores the duplicate.

**Saved cards (scope decision)**: The `MetodoPagoUsuario` table is created in the Alembic migration, but CRUD operations and saved-cards UI are **deferred to a future change**. This keeps the current change focused on the critical path: payment succeeds → order state updates correctly.

### 2. Payment Method Rename: MERCADOPAGO → TARJETA

Current `payment_methods` table has `MERCADOPAGO` as the online payment method. Since we're migrating to Checkout API (direct card processing), rename to `TARJETA`:

**Alembic data migration** (3 pasos, no borra `CANCELADO` del catálogo):
```python
def upgrade():
    # A) Rename MERCADOPAGO → TARJETA
    op.execute("UPDATE payment_methods SET codigo = 'TARJETA', descripcion = 'Pago con tarjeta (MercadoPago)' WHERE codigo = 'MERCADOPAGO'")
    op.execute("UPDATE orders SET forma_pago_codigo = 'TARJETA' WHERE forma_pago_codigo = 'MERCADOPAGO'")
    op.execute("UPDATE payments SET forma_pago_codigo = 'TARJETA' WHERE forma_pago_codigo = 'MERCADOPAGO'")

    # B) Add new order states (NO se borra CANCELADO del catálogo — se deja como legacy)
    op.execute("INSERT INTO order_states (codigo, descripcion, orden, es_terminal) VALUES ('CANCELADO_ADMIN', 'Pedido cancelado por el administrador', 6, true)")
    op.execute("INSERT INTO order_states (codigo, descripcion, orden, es_terminal) VALUES ('CANCELADO_CLIENTE', 'Pedido cancelado por el cliente', 7, true)")

    # C) Migrate existing CANCELADO orders → CANCELADO_ADMIN (todos, sin excepción)
    op.execute("UPDATE orders SET estado_codigo = 'CANCELADO_ADMIN' WHERE estado_codigo = 'CANCELADO'")
    op.execute("UPDATE historial_estado_pedido SET estado_nuevo_codigo = 'CANCELADO_ADMIN' WHERE estado_nuevo_codigo = 'CANCELADO'")
```

### 3. Order State Machine — New Flow

**New states added to `order_states`**:
- `CANCELADO_ADMIN` — Pedido cancelado por el administrador (requires `motivo`)
- `CANCELADO_CLIENTE` — Pedido cancelado por el cliente (requires `motivo`, blocked from EN_PREPARACION+)

**Data migration**: Existing `CANCELADO` orders all move to `CANCELADO_ADMIN`. `CANCELADO` stays in `order_states` catalog as legacy code — not deleted to avoid FK issues.

**Updated FSM transitions**:

```
PENDIENTE       → {CONFIRMADO (webhook only), CANCELADO_ADMIN (admin+motivo), CANCELADO_CLIENTE (client)}
CONFIRMADO      → {EN_PREPARACION (pedidos/admin), CANCELADO_ADMIN (admin+motivo)}
EN_PREPARACION  → {EN_CAMINO (pedidos/admin, delivery only), CANCELADO_ADMIN (admin only+motivo)}
EN_CAMINO       → {ENTREGADO (pedidos/admin)}
ENTREGADO       → {}  (terminal)
CANCELADO_ADMIN → {}  (terminal)
CANCELADO_CLIENTE → {} (terminal)
```

**Updated RBAC**:

| Transition | Allowed Roles | Motivo Required |
|------------|---------------|-----------------|
| PENDIENTE → CANCELADO_CLIENTE | CLIENT | No (optional) |
| PENDIENTE → CANCELADO_ADMIN | ADMIN, PEDIDOS | Yes |
| CONFIRMADO → EN_PREPARACION | PEDIDOS, ADMIN | No |
| CONFIRMADO → CANCELADO_ADMIN | PEDIDOS, ADMIN | Yes |
| EN_PREPARACION → EN_CAMINO | PEDIDOS, ADMIN | No (delivery only) |
| EN_PREPARACION → CANCELADO_ADMIN | ADMIN only | Yes (RN-RB08) |
| EN_CAMINO → ENTREGADO | PEDIDOS, ADMIN | No |

**Key rules**:
- `PENDIENTE → CONFIRMADO` is webhook-only (payment approved). Admin cannot manually confirm.
- `EN_PREPARACION → EN_CAMINO` only valid if `direccion_entrega_id IS NOT NULL` (delivery order).
- Client cancel from `EN_PREPARACION+` → blocked with message: "Tu pedido ya está en preparación y no puede ser cancelado. Contactanos si necesitás ayuda."
- `motivo` is stored in `HistorialEstadoPedido.motivo` (already exists, String(500)).
- `CANCELADO_ADMIN` transitions require `motivo` (enforced in service).

### 4. Delivery + Payment Validation

**Business rule**: Delivery orders (`direccion_entrega_id IS NOT NULL`) only accept `TARJETA` or `TRANSFERENCIA`. Pickup orders accept all methods.

**Backend enforcement** (in `OrderService.crear_pedido()`):
```python
is_delivery = payload.direccion_id is not None
if is_delivery and payload.forma_pago_codigo == "EFECTIVO":
    raise ValidationError("El pago en efectivo no está disponible para envíos. Elegí tarjeta o transferencia.")
```

**Frontend enforcement** (in `PaymentMethodSelector`):
```tsx
const isDelivery = selectedAddressId !== null;
const filteredMethods = isDelivery
  ? methods.filter(m => m.codigo !== "EFECTIVO")
  : methods;
```

### 5. Order State Transition API

**Endpoint**: `POST /api/v1/pedidos/{pedido_id}/transicionar`

**Request**:
```json
{
  "estado_codigo_destino": "CANCELADO_ADMIN",
  "motivo": "Cliente solicitó cancelación por error en dirección"
}
```

**Validation**:
1. Order exists and belongs to user (or admin/pedidos access)
2. FSM allows `current → destino`
3. RBAC allows user role for this transition
4. If `CANCELADO_ADMIN` → `motivo` required (400 if missing)
5. If `EN_CAMINO` → verify order is delivery (`direccion_entrega_id IS NOT NULL`)

**Response**:
```json
{
  "pedido_id": 1,
  "estado_anterior": "CONFIRMADO",
  "estado_nuevo": "EN_PREPARACION",
  "historial": [...]
}
```

### 6. Modal Visual Fix

Replace `bg-glass backdrop-blur-xl border border-glass-border` → `bg-white border border-gray-200 shadow-xl` on:
- `AddressModal`
- `OrderDetailModal`
- `PasswordModal`

Keep backdrop overlay unchanged (`bg-black/60 backdrop-blur-sm`).

### 7. Local Webhook Tunnel (ngrok)

Script `scripts/dev-tunnel.sh`:
```bash
#!/usr/bin/env bash
echo "Starting ngrok tunnel to localhost:8000..."
ngrok http 8000 &
sleep 3
NGROK_URL=$(curl -s http://localhost:4040/api/tunnels | jq -r '.tunnels[0].public_url')
echo "Webhook URL: ${NGROK_URL}/api/v1/pagos/webhook/mercadopago"
echo "Set this URL in your MercadoPago dashboard → Integrations → Webhooks"
```

## Data Flow — Checkout API + Order Confirmation

```
┌─────────────────────────────────────────────────────────────────────┐
│ FRONTEND (PaymentPage)                                              │
│                                                                     │
│  1. User selects payment method + delivery mode                     │
│  2. TARJETA → SecureCardForm tokenizes card (Secure Fields iframes) │
│  3. Frontend generates idempotency_key = crypto.randomUUID()        │
│  4. POST /api/v1/pagos {pedido_id, monto, card_token,               │
│       idempotency_key, payment_method_id, installments}             │
└──────────────────────────────┬──────────────────────────────────────┘
                               │
                               ▼
┌─────────────────────────────────────────────────────────────────────┐
│ BACKEND (PaymentService.crear_pago_api())                           │
│                                                                     │
│  1. Validate pedido exists, is PENDIENTE, owned by user             │
│  2. Check no active payment already exists                          │
│  3. Build payment_data + request_options (idempotency from client)  │
│  4. sdk.payment().create(payment_data, request_options)             │
│  5. If status == 'approved':                                        │
│     a. Record Pago in payments table                                │
│     b. Call OrderService.transicionar_estado(                       │
│          pedido_id, "CONFIRMADO", actor_id=None) → PENDIENTE→CONF.  │
│  6. Return {mp_status, mp_id, status_detail}                        │
└──────────────────────────────┬──────────────────────────────────────┘
                               │
                               ▼
┌─────────────────────────────────────────────────────────────────────┐
│ ORDER STATE: PENDIENTE → CONFIRMADO (payment approved)              │
│ Next: Admin clicks "Preparar" → CONFIRMADO → EN_PREPARACION         │
│ Order is now: PAID + CONFIRMED = Ready for kitchen                  │
└─────────────────────────────────────────────────────────────────────┘
```

## Data Flow — Client Cancel Flow

```
┌─────────────────────────────────────────────────────────────────────┐
│ FRONTEND (Client Orders Page)                                       │
│                                                                     │
│  If order.estado_codigo == "PENDIENTE":                              │
│    → Show "Cancelar pedido" button                                  │
│    → On click: confirm dialog → POST transicionar (CANCELADO_CLIENTE)│
│                                                                     │
│  If order.estado_codigo >= "EN_PREPARACION":                         │
│    → Show "Cancelar pedido" button as DISABLED                      │
│    → Tooltip: "Tu pedido ya está en preparación y no puede          │
│                ser cancelado. Contactanos si necesitás ayuda."      │
└─────────────────────────────────────────────────────────────────────┘
```

## File Changes

| File | Action | Description |
|------|--------|-------------|
| `backend/features/orders/state_machine.py` | Modify | New FSM transitions + RBAC for CANCELADO_ADMIN, CANCELADO_CLIENTE |
| `backend/features/orders/service.py` | Modify | Delivery+payment validation, motivo enforcement |
| `backend/features/orders/router.py` | Modify | Add `POST /pedidos/{id}/transicionar` endpoint |
| `backend/features/orders/schemas.py` | Modify | Add `motivo` field in transition request |
| `backend/features/payments/schemas.py` | Modify | Add `card_token`, `payment_method_id`, `installments`, `idempotency_key` (required, generated by frontend) |
| `backend/features/payments/models.py` | Modify | Add `MetodoPagoUsuario` table (CRUD deferred to future change) |
| `backend/features/payments/service.py` | Modify | Add `crear_pago_api()`, remove `crear_preferencia()` |
| `backend/features/payments/router.py` | Modify | Replace `crear_preferencia()` call with `crear_pago_api()`, remove Checkout Pro flow |
| `backend/features/payments/repository.py` | No change | (CRUD for MetodoPagoUsuario deferred to future change) |
| `backend/alembic/versions/` | Create | Migration: rename MERCADOPAGO→TARJETA, add new order states, create metodo_pago_usuario table |
| `frontend/src/features/payments/` | Create | SecureCardForm, inline payment flow |
| `frontend/src/features/checkout/` | Modify | Delivery mode selector, payment filtering by mode |
| `frontend/src/features/orders/` | Modify | Timeline, cancel flow, modal visual fix |
| `frontend/src/features/delivery-addresses/` | Modify | AddressModal visual fix |
| `frontend/src/features/user-profile/` | Modify | PasswordModal visual fix |
| `scripts/dev-tunnel.sh` | Create | ngrok tunnel script |
| `docs/webhook-testing.md` | Create | Local webhook testing guide |

## Testing Strategy

| Layer | What to Test | Approach |
|-------|-------------|----------|
| Unit | `crear_pago_api()` with mocked SDK | Mock `sdk.payment().create()`, verify data mapping |
| Unit | FSM `validate_transition()` | Test all valid/invalid transitions + RBAC |
| Unit | Delivery + payment validation | Delivery+EFECTIVO → 400, Pickup+EFECTIVO → 200 |
| Unit | `PagoCreate` schema validation | `card_token` required, `idempotency_key` required (UUID format), `payment_method_id` required |
| Integration | `POST /api/v1/pagos` with card_token | TestClient + mocked MP SDK |
| Integration | `POST /pedidos/{id}/transicionar` | TestClient, verify FSM blocks invalid transitions |
| Integration | Client cancel blocked from EN_PREPARACION | TestClient, verify 403/400 response |
| Integration | Webhook → order CONFIRMADO transition | Send webhook payload, verify state change |
| E2E | Full checkout: delivery + TARJETA → payment → confirmation | Playwright flow |
| E2E | Pickup + EFECTIVO → order created successfully | Playwright flow |
| Manual | ngrok tunnel + MP webhook | Start tunnel, trigger sandbox payment, verify webhook |

## Migration / Rollout

1. **Alembic migration** (single file, 3 operations):
   - a. Rename `MERCADOPAGO` → `TARJETA` in `payment_methods` + cascade to orders/payments
   - b. Add `CANCELADO_ADMIN`, `CANCELADO_CLIENTE` to `order_states`; migrate existing `CANCELADO` → `CANCELADO_ADMIN` (all orders, `CANCELADO` stays in catalog as legacy)
   - c. Create `metodo_pago_usuario` table (CRUD endpoints deferred to future change)
2. **Checkout Pro removal**: `crear_preferencia()` is deleted from the service. The `POST /api/v1/pagos` endpoint now exclusively calls `crear_pago_api()`. No branching.
3. **Rollout order**: Backend first (migration + service), then frontend (SecureCardForm + inline flow).
4. **Procfile**: Already correct — `release: alembic upgrade head` runs on Railway deploy.
