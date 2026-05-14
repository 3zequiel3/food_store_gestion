# Design: Payment API Integration, Order State Guards & UI Fixes

## Technical Approach

### 1. Checkout API Migration

Extend the existing `PaymentService` with a parallel `crear_pago_api()` method that calls `sdk.payment().create()` instead of `sdk.preference().create()`. The router inspects `PagoCreate` for the new fields (`card_token`, `payment_method_id`, `installments`) and branches: if present → API flow; if absent → legacy Pro flow (backward compat). A new `MetodoPagoUsuario` SQLModel stores saved cards linked to `mp_customer_id`. On the frontend, `@mercadopago/sdk-js` Secure Fields render iframes for card data; on submit the SDK produces a token that the backend consumes.

### 2. Order State Transitions (FSM Enforcement)

The FSM already exists in `backend/features/orders/state_machine.py` with `ALLOWED_TRANSITIONS` and `TRANSITION_ROLES`. What's missing is:
- A public API endpoint to trigger transitions (`POST /pedidos/{id}/transicionar`)
- Frontend UI that shows only valid next states per the FSM + user role
- The webhook handler already calls `transicionar_estado(actor_id=None)` to do PENDIENTE→CONFIRMADO (SISTEMA actor)

The endpoint will:
1. Lookup order by ID
2. Call `validate_transition(current_state, target_state, user_role)` from `state_machine.py`
3. Execute the transition via the service
4. Append to `HistorialEstadoPedido` (already exists)
5. Return the new state + full history

Frontend:
- Admin orders page: Show state timeline + buttons for valid transitions (role-gated)
- Client orders page: Show read-only timeline + "Cancelar" button only when PENDIENTE→CANCELADO is valid

### 3. Modal Visual Fix

The "grey gradient" issue is caused by `bg-glass backdrop-blur-xl` on modal surfaces. `bg-glass` is a semi-transparent custom property that blends with the background, creating a dark/grey appearance. The fix: replace `bg-glass backdrop-blur-xl border border-glass-border` → `bg-white border border-gray-200` on:
- `AddressModal` (delivery addresses)
- `OrderDetailModal` (order detail)
- `PasswordModal` (user profile)

Keep the backdrop overlay (`bg-black/60 backdrop-blur-sm`) — that's the dimmed background behind the modal, not the modal surface itself.

### 4. Local Webhook Tunnel (ngrok)

MercadoPago webhooks require HTTPS. For local development:
- ngrok creates a public HTTPS tunnel → `localhost:8000`
- Script `scripts/dev-tunnel.sh` starts ngrok, captures the HTTPS URL
- Set `MP_WEBHOOK_URL` in `.env` to the ngrok URL
- Configure the ngrok URL in the MP dashboard as the webhook endpoint
- MP sends POST → ngrok → `http://localhost:8000/api/v1/pagos/webhook/mercadopago`

### 5. Procfile Verification

The Procfile already has:
```
release: alembic upgrade head
web: python -m uvicorn main:app --host 0.0.0.0 --port $PORT
```
This is confirmed correct. The `release:` step runs migrations before the web dyno starts. No changes needed — just documentation in the design.

## Architecture Decisions

### Decision: Branching strategy in router

| Option | Tradeoff | Decision |
|--------|----------|----------|
| Separate endpoint `POST /pagos/api` | Clean separation but doubles route surface, breaks existing client contract | ❌ |
| Single endpoint, branch by field presence | Minimal API surface change, backward compatible, one router method grows | ✅ |

**Choice**: Single endpoint with conditional branching. `PagoCreate` gains optional fields. When `card_token` is present, call `crear_pago_api()`; otherwise fall back to `crear_preferencia()`.

### Decision: Where to store idempotency key

| Option | Tradeoff | Decision |
|--------|----------|----------|
| Client-generated UUID4 sent in body | Client controls key, simple backend | ✅ |
| Backend-generated from `pedido_id` + timestamp | No client dependency, but retry within same second could collide | ❌ |
| DB column `idempotency_key` on `Pago` | Audit trail, but adds migration for existing table | ❌ (defer) |

**Choice**: Client generates UUID4 `idempotency_key`, sends in request body. Backend passes it as `X-Idempotency-Key` header to `RequestOptions`. No DB storage this iteration — MP de-duplicates server-side.

### Decision: Saved cards storage model

| Option | Tradeoff | Decision |
|--------|----------|----------|
| New table `metodo_pago_usuario` | Clean separation, own CRUD, flexible schema | ✅ |
| Columns on existing `usuario` table | Simpler but pollutes user model, hard to have multiple cards | ❌ |
| JSON field on `usuario` | No migration, but no relational integrity, hard to query | ❌ |

**Choice**: New `metodo_pago_usuario` table with FK to `usuario`.

### Decision: Order state transition endpoint

| Option | Tradeoff | Decision |
|--------|----------|----------|
| PATCH /pedidos/{id} with `estado_codigo` | Simple but conflates general update with state transition | ❌ |
| POST /pedidos/{id}/transicionar | Explicit action, clear intent, audit-friendly | ✅ |
| Separate state machine service | Clean architecture but overkill for this scope | ❌ |

**Choice**: `POST /api/v1/pedidos/{id}/transicionar` with body `{ "estado_codigo_destino": "CONFIRMADO" }`. The endpoint validates via FSM + RBAC, executes via existing `transicionar_estado()` service method.

### Decision: Frontend card tokenization approach

| Option | Tradeoff | Decision |
|--------|----------|----------|
| MP.js Secure Fields (iframes) | PCI SAQ-A compliant, card data never hits our server | ✅ |
| Custom form + manual tokenization | Full control but PCI scope expands to SAQ-D | ❌ |
| Redirect to MP hosted form | Simplest but kills inline UX (current problem) | ❌ |

**Choice**: MP.js Secure Fields.

### Decision: Modal surface styling

| Option | Tradeoff | Decision |
|--------|----------|----------|
| `bg-glass backdrop-blur-xl` (current) | Frosted glass, but creates grey/dark appearance | ❌ |
| `bg-white` (opaque) | Clean, readable, consistent with CartValidationModal | ✅ |
| `bg-card` (Tailwind custom) | Theme-aware but needs to be verified as opaque | ⚠️ (use bg-white for certainty) |

**Choice**: `bg-white border border-gray-200` for all modal surfaces. Keep backdrop dimming on the overlay.

## Data Flow — Checkout API

```
┌─────────────────────────────────────────────────────────────────────┐
│ FRONTEND                                                            │
│                                                                     │
│  PaymentPage                                                        │
│    ├─ GET /metodos-pago → saved cards list                          │
│    ├─ [Saved Card selected] → use mp_card_id + new token            │
│    └─ [New Card] → SecureCardForm (MP.js iframes)                   │
│          └─ mp.createCardToken({cardNumber, expMonth, expYear, cvv})│
│              └─ card_token (one-time token)                         │
│                                                                     │
│  POST /api/v1/pagos {                                               │
│    pedido_id, monto, card_token, payment_method_id,                 │
│    installments, idempotency_key                                    │
│  }                                                                  │
└──────────────────────────────┬──────────────────────────────────────┘
                               │
                               ▼
┌─────────────────────────────────────────────────────────────────────┐
│ BACKEND (PaymentService)                                            │
│                                                                     │
│  1. Validate PagoCreate fields                                      │
│  2. Build payment_data = {                                          │
│       transaction_amount, token, description, installments,         │
│       payment_method_id, external_reference                         │
│     }                                                               │
│  3. request_options = RequestOptions(                                │
│       x_idempotency_key = body.idempotency_key                      │
│     )                                                               │
│  4. sdk.payment().create(payment_data, request_options)              │
│  5. Map MP response → PagoResponse                                  │
│  6. If status == 'approved' → trigger pedido CONFIRMADO transition  │
│     via OrderService.transicionar_estado(actor_id=None)             │
│  7. Return {mp_status, mp_id, status_detail}                        │
└──────────────────────────────┬──────────────────────────────────────┘
                               │
                               ▼
┌─────────────────────────────────────────────────────────────────────┐
│ MercadoPago API                                                     │
│  - Validates card token (one-time use)                              │
│  - Processes payment                                                │
│  - Returns synchronous status (approved/rejected/pending)           │
│  - Sends webhook notification (async backup)                        │
└─────────────────────────────────────────────────────────────────────┘
```

## Data Flow — Order State Transitions

```
┌─────────────────────────────────────────────────────┐
│ FRONTEND (Admin Orders Page)                        │
│                                                     │
│  OrderTimeline shows:                               │
│    PENDIENTE ✓                                      │
│    ┌─────────────┐                                  │
│    │ Confirmar   │ ← Button (PEDIDOS/ADMIN only)    │
│    └─────────────┘                                  │
│                                                     │
│  onClick → POST /api/v1/pedidos/{id}/transicionar   │
│    { estado_codigo_destino: "CONFIRMADO" }          │
└────────────────────────┬────────────────────────────┘
                         │
                         ▼
┌─────────────────────────────────────────────────────┐
│ BACKEND (Orders Router → Service → FSM)             │
│                                                     │
│  1. GET /pedidos/{id} → find order                  │
│  2. GET current user role                           │
│  3. validate_transition("PENDIENTE", "CONFIRMADO",  │
│     user_role) → checks FSM + RBAC                  │
│  4. If valid → update order.estado_codigo           │
│  5. Append HistorialEstadoPedido record             │
│  6. Return new state + full history                 │
│                                                     │
│  If invalid → 400 (FSM) or 403 (RBAC)               │
└─────────────────────────────────────────────────────┘
```

## File Changes

| File | Action | Description |
|------|--------|-------------|
| `backend/features/payments/schemas.py` | Modify | Add `card_token`, `payment_method_id`, `installments`, `idempotency_key` to `PagoCreate` |
| `backend/features/payments/models.py` | Modify | Add `MetodoPagoUsuario` SQLModel table |
| `backend/features/payments/service.py` | Modify | Add `crear_pago_api()`, saved cards CRUD methods |
| `backend/features/payments/router.py` | Modify | Branch logic in `crear_pago()`; add `GET/POST/DELETE /metodos-pago` routes |
| `backend/features/payments/repository.py` | Modify | Add CRUD operations for `MetodoPagoUsuario` |
| `backend/features/orders/router.py` | Modify | Add `POST /pedidos/{id}/transicionar` endpoint |
| `backend/alembic/versions/` | Create | Migration for `metodo_pago_usuario` table |
| `frontend/package.json` | Modify | Add `@mercadopago/sdk-js` dependency |
| `frontend/src/features/payments/components/SecureCardForm.tsx` | Create | MP.js Secure Fields card form |
| `frontend/src/features/payments/components/SavedCardsList.tsx` | Create | Display saved cards with select/delete |
| `frontend/src/features/payments/services/payments.service.ts` | Modify | Add `createPayment()`, `getSavedCards()`, `saveCard()`, `deleteCard()` |
| `frontend/src/features/payments/types/payments.types.ts` | Modify | Add `PaymentCreateRequest`, `SavedCard` types |
| `frontend/src/features/payments/hooks/useInitPayment.ts` | Modify | Switch from preference creation to API payment |
| `frontend/src/features/orders/components/OrderDetailModal.tsx` | Modify | Fix modal surface: `bg-white` instead of `bg-glass`, add state timeline |
| `frontend/src/features/delivery-addresses/components/AddressModal.tsx` | Modify | Fix modal surface: `bg-white` instead of `bg-glass` |
| `frontend/src/features/user-profile/components/PasswordModal.tsx` | Modify | Fix modal surface: `bg-white` instead of `bg-glass` |
| `scripts/dev-tunnel.sh` | Create | ngrok tunnel startup script |
| `docs/webhook-testing.md` | Create | Local webhook testing guide |

## Interfaces / Contracts

### Backend — `PagoCreate` schema (extended)

```python
class PagoCreate(BaseSchema):
    pedido_id: int
    monto: float
    # Checkout API fields (optional — presence triggers API flow)
    card_token: str | None = None
    payment_method_id: str | None = None
    installments: int | None = 1
    idempotency_key: str | None = None
```

### Backend — `MetodoPagoUsuario` model

```python
class MetodoPagoUsuario(SQLModel, table=True):
    __tablename__ = "metodo_pago_usuario"
    id: int = Field(primary_key=True)
    usuario_id: int = Field(foreign_key="usuario.id")
    mp_customer_id: str
    mp_card_id: str
    last_four: str
    expiration_month: int
    expiration_year: int
    payment_method_id: str
    card_brand: str
    created_at: datetime = Field(default_factory=utcnow)
```

### Backend — Order state transition endpoint

```python
# POST /api/v1/pedidos/{pedido_id}/transicionar
class TransicionarRequest(BaseSchema):
    estado_codigo_destino: str  # e.g. "CONFIRMADO"

class TransicionarResponse(BaseSchema):
    pedido_id: int
    estado_anterior: str
    estado_nuevo: str
    historial: list[HistorialEstadoRead]
```

### Frontend — `SecureCardForm` contract

```typescript
interface SecureCardFormProps {
  onSubmit: (token: string, paymentMethodId: string) => void;
  onError: (error: string) => void;
  isLoading?: boolean;
}
```

## Testing Strategy

| Layer | What to Test | Approach |
|-------|-------------|----------|
| Unit | `crear_pago_api()` with mocked SDK | Mock `sdk.payment().create()`, verify data mapping, idempotency header |
| Unit | `PagoCreate` schema validation | Test optional fields: with card_token → API path, without → Pro path |
| Unit | `MetodoPagoUsuario` CRUD | In-memory SQLite, test save/list/delete |
| Unit | FSM `validate_transition()` | Test all valid/invalid transitions + RBAC |
| Integration | `POST /api/v1/pagos` with card_token | TestClient + mocked MP SDK |
| Integration | `POST /pedidos/{id}/transicionar` | TestClient, verify FSM blocks invalid transitions |
| Integration | Webhook still works | Send webhook payload, verify order state transition |
| E2E | Full checkout with Secure Fields | Playwright: fill card form → submit → verify approval |
| Manual | ngrok tunnel + MP webhook | Start tunnel, trigger sandbox payment, verify webhook received |

## Migration / Rollout

1. **Alembic migration**: `metodo_pago_usuario` table.
2. **Feature flag**: None needed — new fields are optional in `PagoCreate`.
3. **Rollout order**: Backend first (deploy with new fields accepted but unused), then frontend (enable Secure Fields).
4. **Rollback**: Revert router to always call `crear_preferencia()`. Drop table via `alembic downgrade`.
5. **Procfile**: Already correct — `release: alembic upgrade head` runs on every Railway deploy.
