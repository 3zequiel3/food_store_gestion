# Tasks: Payment API Integration, Order State Guards & UI Fixes

> Format: `[ ]` = pending, `[x]` = done. Each task is a reviewable work unit.

## Phase 0: Data Migrations (DB & Catalog)

[ ] **Task 0.1**: Create Alembic migration for payment method rename + new order states + metodo_pago_usuario table
- Single migration file: `backend/alembic/versions/YYYYMMDD_HHMM_payment_order_state_refactor.py`
- Step A: Rename `MERCADOPAGO` → `TARJETA` in `payment_methods`, cascade to `orders.forma_pago_codigo` and `payments.forma_pago_codigo`
- Step B: Add `CANCELADO_ADMIN` (descripcion: "Pedido cancelado por el administrador", orden: 6, es_terminal: true) and `CANCELADO_CLIENTE` (descripcion: "Pedido cancelado por el cliente", orden: 7, es_terminal: true) to `order_states`
- Step C: Migrate existing `CANCELADO` orders: if `cambiado_por_id IS NULL` in history → `CANCELADO_ADMIN`, else → `CANCELADO_CLIENTE`
- Step D: Create `metodo_pago_usuario` table (id, usuario_id FK, mp_customer_id, mp_card_id, last_four, expiration_month, expiration_year, payment_method_id, card_brand, created_at)
- Verify with `alembic upgrade head` and `alembic downgrade -1`

## Phase 1: Order State Machine & Validation

[ ] **Task 1.1**: Update FSM transitions in `backend/features/orders/state_machine.py`
- `ALLOWED_TRANSITIONS`:
  - `PENDIENTE` → {CONFIRMADO, CANCELADO_ADMIN, CANCELADO_CLIENTE}
  - `CONFIRMADO` → {EN_PREPARACION, CANCELADO_ADMIN}
  - `EN_PREPARACION` → {EN_CAMINO, CANCELADO_ADMIN}
  - `EN_CAMINO` → {ENTREGADO}
  - `ENTREGADO` → {}
  - `CANCELADO_ADMIN` → {}
  - `CANCELADO_CLIENTE` → {}
- Note: CONFIRMADO is webhook-only, not exposed via manual endpoint

[ ] **Task 1.2**: Update RBAC rules in `backend/features/orders/state_machine.py`
- `TRANSITION_ROLES`:
  - `PENDIENTE → CANCELADO_CLIENTE`: CLIENT
  - `PENDIENTE → CANCELADO_ADMIN`: ADMIN, PEDIDOS
  - `CONFIRMADO → EN_PREPARACION`: PEDIDOS, ADMIN
  - `CONFIRMADO → CANCELADO_ADMIN`: PEDIDOS, ADMIN
  - `EN_PREPARACION → EN_CAMINO`: PEDIDOS, ADMIN
  - `EN_PREPARACION → CANCELADO_ADMIN`: ADMIN only (RN-RB08)
  - `EN_CAMINO → ENTREGADO`: PEDIDOS, ADMIN

[ ] **Task 1.3**: Add delivery-mode validation to `OrderService.crear_pedido()`
- If `direccion_id IS NOT NULL` (delivery) and `forma_pago_codigo == "EFECTIVO"` → raise `ValidationError("El pago en efectivo no está disponible para envíos. Elegí tarjeta o transferencia.")`
- Add delivery mode detection method: `_is_delivery(pedido) → bool`

[ ] **Task 1.4**: Add `motivo` enforcement to `OrderService.avanzar_estado()` / `transicionar_estado()`
- If transition is to `CANCELADO_ADMIN` and `motivo` is empty → raise `ValidationError("Debes indicar el motivo del rechazo.")`
- `motivo` already exists in `HistorialEstadoPedido` — just need to enforce at service level

## Phase 2: Backend — Order State Transition API

[ ] **Task 2.1**: Create `TransicionarRequest` and `TransicionarResponse` schemas in `backend/features/orders/schemas.py`
- `TransicionarRequest`: `estado_codigo_destino: str`, `motivo: str | None = None` (max 500)
- `TransicionarResponse`: `pedido_id: int`, `estado_anterior: str`, `estado_nuevo: str`, `historial: list[HistorialItem]`

[ ] **Task 2.2**: Add `POST /api/v1/pedidos/{pedido_id}/transicionar` endpoint in `backend/features/orders/router.py`
- Requires auth (dynamic RBAC)
- Validates via `validate_transition()` + delivery-mode check for EN_CAMINO
- Enforces `motivo` requirement for CANCELADO_ADMIN
- Returns `TransicionarResponse` with full history
- Handle 400 (invalid FSM), 403 (insufficient role), 404 (not found)

[ ] **Task 2.3**: Update `AvanzarEstadoRequest` schema — rename or deprecate in favor of `TransicionarRequest`
- Keep backward compat or mark old endpoint as deprecated
- `motivo` field added (was already optional, now required for CANCELADO_ADMIN)

## Phase 3: Backend — Checkout API Core

[ ] **Task 3.1**: Add `MetodoPagoUsuario` schemas in `backend/features/payments/schemas.py`
- `MetodoPagoUsuarioCreate` (for POST)
- `MetodoPagoUsuarioRead` (for GET, excludes sensitive fields)

[ ] **Task 3.2**: Add repository CRUD for `MetodoPagoUsuario` in `backend/features/payments/repository.py`
- Methods: `create()`, `list_by_user()`, `get_by_mp_card_id()`, `delete()`
- Include user ownership filter on all reads

[ ] **Task 3.3**: Add `crear_pago_api()` to `PaymentService`
- Accept `PagoCreate` with `card_token`, `payment_method_id`, `installments`
- Build `payment_data` dict and call `sdk.payment().create(payment_data, request_options)`
- Pass `X-Idempotency-Key` header via `RequestOptions.custom_headers`
- Map MP response → `PagoResponse` (mp_status, mp_id, status_detail)

[ ] **Task 3.4**: Wire payment approval → order state CONFIRMADO
- After `sdk.payment().create()` returns `status == 'approved'`, call `OrderService.transicionar_estado(actor_id=None)` to move PENDIENTE → CONFIRMADO
- Handle `BusinessRuleError` if order is not in PENDIENTE state

[ ] **Task 3.5**: Add saved cards service methods to `PaymentService`
- `guardar_metodo_pago(user_id, mp_customer_id, mp_card_id, card_data)`
- `listar_metodos_pago(user_id)`
- `eliminar_metodo_pago(user_id, metodo_id)` — ownership check

## Phase 4: Backend — Router Endpoints (Payments)

[ ] **Task 4.1**: Update `POST /api/v1/pagos` router to branch API vs Pro flow
- If `card_token` present → call `crear_pago_api()`
- If absent → call `crear_preferencia()` (existing flow)

[ ] **Task 4.2**: Add `GET /api/v1/metodos-pago` router endpoint
- Requires auth, returns user's saved cards

[ ] **Task 4.3**: Add `POST /api/v1/metodos-pago` router endpoint
- Requires auth, accepts `MetodoPagoUsuarioCreate`

[ ] **Task 4.4**: Add `DELETE /api/v1/metodos-pago/{id}` router endpoint
- Requires auth, verifies ownership before delete

## Phase 5: Frontend — Payment Base

[ ] **Task 5.1**: Install `@mercadopago/sdk-js` in `frontend/package.json`
- Run `pnpm add @mercadopago/sdk-js`

[ ] **Task 5.2**: Extend payment types in `frontend/src/features/payments/types/payments.types.ts`
- `PaymentCreateRequest` (pedido_id, monto, card_token?, payment_method_id?, installments?, idempotency_key?)
- `SavedCard` (id, last_four, expiration_month, expiration_year, payment_method_id, card_brand)
- `PaymentResponse` (mp_status, mp_id, status_detail, order_id?)
- `TransicionarRequest` (estado_codigo_destino, motivo?)
- `TransicionarResponse` (pedido_id, estado_anterior, estado_nuevo, historial)

[ ] **Task 5.3**: Extend payment service in `frontend/src/features/payments/services/payments.service.ts`
- `createPayment(data: PaymentCreateRequest)` → `POST /api/v1/pagos`
- `getSavedCards()` → `GET /api/v1/metodos-pago`
- `saveCard(data)` → `POST /api/v1/metodos-pago`
- `deleteCard(id)` → `DELETE /api/v1/metodos-pago/{id}`

[ ] **Task 5.4**: Add `transicionarEstado()` to orders service
- `transicionarEstado(pedidoId: number, estadoDestino: string, motivo?: string)` → `POST /api/v1/pedidos/{id}/transicionar`

## Phase 6: Frontend — Payment Components

[ ] **Task 6.1**: Create `SecureCardForm` component
- File: `frontend/src/features/payments/components/SecureCardForm.tsx`
- Use `@mercadopago/sdk-js` Secure Fields (iframes for card number, expiry, CVV)
- Props: `onSubmit(token, paymentMethodId)`, `onError(message)`, `isLoading?`
- Initialize MP SDK with `VITE_MP_PUBLIC_KEY`

[ ] **Task 6.2**: Create `SavedCardsList` component
- File: `frontend/src/features/payments/components/SavedCardsList.tsx`
- Display saved cards as selectable radio options (brand icon + last4 + expiry)
- Include "Add new card" option, delete button with confirmation

[ ] **Task 6.3**: Update `useInitPayment` hook
- Switch from preference creation to `createPayment()` API call
- Handle synchronous `status: 'approved'` → navigate to confirmation
- Handle `status: 'rejected'` → show error

[ ] **Task 6.4**: Update `PaymentPage` for inline flow
- Integrate `SavedCardsList` + `SecureCardForm`
- Show loading state during payment processing
- Handle errors: network, MP decline, idempotency retry

## Phase 7: Frontend — Checkout Refactor (Delivery + Payment)

[ ] **Task 7.1**: Update `PaymentMethodSelector` to filter by delivery mode
- File: `frontend/src/features/checkout/components/PaymentMethodSelector.tsx`
- Accept prop `isDelivery: boolean`
- If `isDelivery` → filter out EFECTIVO from the list
- Show message: "Para envíos, aceptamos tarjeta o transferencia bancaria"

[ ] **Task 7.2**: Update `CheckoutPage` to pass delivery mode to PaymentMethodSelector
- File: `frontend/src/features/checkout/components/CheckoutPage.tsx`
- `isDelivery = selectedAddressId !== null`
- Pass `isDelivery` to `PaymentMethodSelector`
- If user had EFECTIVO selected and switches to delivery → reset payment selection

## Phase 8: Frontend — Order State Timeline & Cancel Flow

[ ] **Task 8.1**: Create `OrderTimeline` component
- File: `frontend/src/features/orders/components/OrderTimeline.tsx`
- Display states in order: PENDIENTE → CONFIRMADO → EN_PREPARACION → EN_CAMINO → ENTREGADO
- CANCELADO_ADMIN / CANCELADO_CLIENTE shown in red, replace future states
- Completed states: checkmark + green; current: highlighted; future: greyed

[ ] **Task 8.2**: Add state transition buttons to order detail (Admin/Pedidos)
- Show buttons only for valid next states per FSM + user role
- Labels: "Confirmar", "Preparar", "En camino", "Entregado", "Rechazar"
- "Rechazar" button opens modal to enter `motivo` (required for CANCELADO_ADMIN)
- After transition: refetch order, update timeline

[ ] **Task 8.3**: Add client cancel button with block logic
- Show "Cancelar pedido" button only for PENDIENTE orders
- For EN_PREPARACION+: show button as disabled with tooltip
- Tooltip text: "Tu pedido ya está en preparación y no puede ser cancelado. Contactanos si necesitás ayuda."
- On cancel: confirmation modal with optional `motivo` field → call transicionar(CANCELADO_CLIENTE)

[ ] **Task 8.4**: Display cancel reason in order detail
- When order is CANCELADO_ADMIN or CANCELADO_CLIENTE, show the `motivo` from the last history entry
- Label: "Motivo: {motivo}"
- If no motivo: "Sin motivo especificado"

## Phase 9: Frontend — Modal Visual Fixes

[ ] **Task 9.1**: Fix `AddressModal` modal surface
- File: `frontend/src/features/delivery-addresses/components/AddressModal.tsx`
- Replace `bg-glass backdrop-blur-xl border border-glass-border` → `bg-white border border-gray-200 shadow-xl`

[ ] **Task 9.2**: Fix `OrderDetailModal` modal surface
- File: `frontend/src/features/orders/components/OrderDetailModal.tsx`
- Same replacement for outer panel AND sticky header
- Sticky header: `bg-white` instead of `bg-glass backdrop-blur-xl`

[ ] **Task 9.3**: Fix `PasswordModal` modal surface
- File: `frontend/src/features/user-profile/components/PasswordModal.tsx`
- Same replacement: `bg-glass` → `bg-white`

## Phase 10: DevOps & Documentation

[ ] **Task 10.1**: Create ngrok tunnel script
- File: `scripts/dev-tunnel.sh`
- Starts ngrok on port 8000, prints HTTPS URL
- Include instructions for ngrok auth token setup

[ ] **Task 10.2**: Create webhook testing documentation
- File: `docs/webhook-testing.md`
- Steps: start ngrok → copy HTTPS URL → configure in MP dashboard → trigger test payment
- Document the 3 webhook formats the backend handles

[ ] **Task 10.3**: Verify Procfile for Railway migrations
- Confirm `release: alembic upgrade head` is present (it is)
- Add doc note about migration behavior on deploy

## Review Workload Forecast

- **Estimated total tasks**: 30
- **Estimated changed lines**: ~1200-1500 (backend ~500, frontend ~600-800, migrations ~100)
- **Risk level**: High — payment flow + state machine + catalog data migration
- **Chained PRs recommended**: Yes (Phase 0-4 backend first, Phase 5-9 frontend, Phase 10 devops)
- **400-line budget risk**: High — recommend splitting into 2-3 PRs
