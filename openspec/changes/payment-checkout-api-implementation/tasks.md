# Tasks: Payment API Integration, Order State Guards & UI Fixes

> Format: `[ ]` = pending, `[x]` = done. Each task is a reviewable work unit.

## Phase 1: DB & Schema

[ ] **Task 1.1**: Create `MetodoPagoUsuario` SQLModel in `backend/features/payments/models.py`
- Fields: `id`, `usuario_id` (FK), `mp_customer_id`, `mp_card_id`, `last_four`, `expiration_month`, `expiration_year`, `payment_method_id`, `card_brand`, `created_at`
- Table name: `metodo_pago_usuario`

[ ] **Task 1.2**: Create `MetodoPagoUsuario` schemas in `backend/features/payments/schemas.py`
- `MetodoPagoUsuarioCreate` (for POST)
- `MetodoPagoUsuarioRead` (for GET, excludes sensitive fields)

[ ] **Task 1.3**: Create Alembic migration for `metodo_pago_usuario` table
- File: `backend/alembic/versions/YYYYMMDD_HHMM_add_metodo_pago_usuario.py`
- Verify with `alembic upgrade head` and `alembic downgrade -1`

[ ] **Task 1.4**: Add repository CRUD for `MetodoPagoUsuario` in `backend/features/payments/repository.py`
- Methods: `create()`, `list_by_user()`, `get_by_mp_card_id()`, `delete()`
- Include user ownership filter on all reads

## Phase 2: Backend — Checkout API Core

[ ] **Task 2.1**: Add `crear_pago_api()` to `PaymentService`
- Accept `PagoCreate` with `card_token`, `payment_method_id`, `installments`
- Build `payment_data` dict and call `sdk.payment().create(payment_data, request_options)`
- Pass `X-Idempotency-Key` header via `RequestOptions.custom_headers`
- Map MP response → `PagoResponse` (mp_status, mp_id, status_detail)

[ ] **Task 2.2**: Wire payment approval → order state CONFIRMADO
- After `sdk.payment().create()` returns `status == 'approved'`, call `OrderService.transicionar_estado(actor_id=None)` to move PENDIENTE → CONFIRMADO
- Handle `BusinessRuleError` if order is not in PENDIENTE state

[ ] **Task 2.3**: Extend `PagoCreate` schema in `backend/features/payments/schemas.py`
- Add optional fields: `card_token: str | None`, `payment_method_id: str | None`, `installments: int | None`, `idempotency_key: str | None`
- Keep backward compatibility — existing fields unchanged

[ ] **Task 2.4**: Add saved cards service methods to `PaymentService`
- `guardar_metodo_pago(user_id, mp_customer_id, mp_card_id, card_data)` — creates or updates `MetodoPagoUsuario`
- `listar_metodos_pago(user_id)` — returns list of saved cards
- `eliminar_metodo_pago(user_id, metodo_id)` — deletes with ownership check

## Phase 3: Backend — Router Endpoints

[ ] **Task 3.1**: Update `POST /api/v1/pagos` router to branch API vs Pro flow
- If `card_token` present → call `crear_pago_api()`
- If absent → call `crear_preferencia()` (existing flow)
- Return unified `PagoResponse` shape

[ ] **Task 3.2**: Add `GET /api/v1/metodos-pago` router endpoint
- Requires auth, returns user's saved cards
- Use `PaymentService.listar_metodos_pago()`

[ ] **Task 3.3**: Add `POST /api/v1/metodos-pago` router endpoint
- Requires auth, accepts `MetodoPagoUsuarioCreate`
- Calls `PaymentService.guardar_metodo_pago()` with current user ID

[ ] **Task 3.4**: Add `DELETE /api/v1/metodos-pago/{id}` router endpoint
- Requires auth, verifies ownership before delete
- Calls `PaymentService.eliminar_metodo_pago()`

[ ] **Task 3.5**: Add `POST /api/v1/pedidos/{pedido_id}/transicionar` router endpoint
- Requires auth, accepts `{ estado_codigo_destino: str }`
- Calls `validate_transition()` from `state_machine.py` + `OrderService.transicionar_estado()`
- Returns `TransicionarResponse` with new state + history
- Handle 400 (invalid FSM transition) and 403 (insufficient role)

## Phase 4: Frontend — Payment Base

[ ] **Task 4.1**: Install `@mercadopago/sdk-js` in `frontend/package.json`
- Run `pnpm add @mercadopago/sdk-js`
- Verify import works in dev server

[ ] **Task 4.2**: Extend payment types in `frontend/src/features/payments/types/payments.types.ts`
- Add `PaymentCreateRequest` (pedido_id, monto, card_token?, payment_method_id?, installments?, idempotency_key?)
- Add `SavedCard` (id, last_four, expiration_month, expiration_year, payment_method_id, card_brand)
- Add `PaymentResponse` (mp_status, mp_id, status_detail, order_id?)

[ ] **Task 4.3**: Extend payment service in `frontend/src/features/payments/services/payments.service.ts`
- Add `createPayment(data: PaymentCreateRequest)` → `POST /api/v1/pagos`
- Add `getSavedCards()` → `GET /api/v1/metodos-pago`
- Add `saveCard(data)` → `POST /api/v1/metodos-pago`
- Add `deleteCard(id)` → `DELETE /api/v1/metodos-pago/{id}`

[ ] **Task 4.4**: Add `transicionarEstado()` to orders service
- `transicionarEstado(pedidoId: number, estadoDestino: string)` → `POST /api/v1/pedidos/{id}/transicionar`
- Return `TransicionarResponse` type

## Phase 5: Frontend — Payment Components

[ ] **Task 5.1**: Create `SecureCardForm` component
- File: `frontend/src/features/payments/components/SecureCardForm.tsx`
- Use `@mercadopago/sdk-js` Secure Fields (iframes for card number, expiry, CVV)
- Props: `onSubmit(token, paymentMethodId)`, `onError(message)`, `isLoading?`
- Initialize MP SDK with `VITE_MP_PUBLIC_KEY`
- Handle tokenization errors with user-friendly messages

[ ] **Task 5.2**: Create `SavedCardsList` component
- File: `frontend/src/features/payments/components/SavedCardsList.tsx`
- Display saved cards as selectable radio options (show brand icon + last4 + expiry)
- Include "Add new card" option
- Delete button with confirmation
- Empty state: "No tenés tarjetas guardadas"

[ ] **Task 5.3**: Update `useInitPayment` hook
- File: `frontend/src/features/payments/hooks/useInitPayment.ts`
- Switch from preference creation (`sdk.preference().create()`) to payment creation (`createPayment()`)
- Handle synchronous `status: 'approved'` → navigate to confirmation
- Handle `status: 'rejected'` → show error
- Handle `status: 'pending'` → show pending state

[ ] **Task 5.4**: Update `PaymentPage` for inline flow
- Integrate `SavedCardsList` + `SecureCardForm`
- On card selection: if saved card → send `mp_card_id` + new token; if new card → use `SecureCardForm`
- Show loading state during payment processing
- Handle errors: network, MP decline, idempotency retry

## Phase 6: Frontend — Order State Timeline

[ ] **Task 6.1**: Create `OrderTimeline` component
- File: `frontend/src/features/orders/components/OrderTimeline.tsx`
- Display current order state as a step timeline (PENDIENTE → CONFIRMADO → EN_PREPARACION → EN_CAMINO → ENTREGADO/CANCELADO)
- Highlight current state, completed states, and future states
- Show valid next actions as buttons (role-gated)

[ ] **Task 6.2**: Update `OrderDetailModal` — visual fix + timeline
- Replace `bg-glass backdrop-blur-xl` → `bg-white border border-gray-200` for modal surface
- Keep backdrop overlay (`bg-black/60 backdrop-blur-sm`)
- Integrate `OrderTimeline` component
- Add transicionar buttons that call `transicionarEstado()` API
- Refetch order after successful transition

## Phase 7: Frontend — Modal Visual Fixes

[ ] **Task 7.1**: Fix `AddressModal` modal surface
- File: `frontend/src/features/delivery-addresses/components/AddressModal.tsx`
- Replace `bg-glass backdrop-blur-xl border border-glass-border` → `bg-white border border-gray-200 shadow-xl`
- Verify modal is readable on any background

[ ] **Task 7.2**: Fix `PasswordModal` modal surface
- File: `frontend/src/features/user-profile/components/PasswordModal.tsx`
- Same replacement: `bg-glass` → `bg-white`
- Verify modal is readable

## Phase 8: DevOps & Documentation

[ ] **Task 8.1**: Create ngrok tunnel script
- File: `scripts/dev-tunnel.sh`
- Starts ngrok on port 8000: `ngrok http 8000`
- Prints HTTPS URL
- Optionally sets `MP_WEBHOOK_URL` env var for the backend process
- Include instructions for ngrok auth token setup

[ ] **Task 8.2**: Create webhook testing documentation
- File: `docs/webhook-testing.md`
- Steps: start ngrok → copy HTTPS URL → configure in MP dashboard → trigger test payment → verify webhook received
- Include troubleshooting: ngrok reconnects (URL changes), MP sandbox vs production webhook URLs
- Document the 3 webhook formats the backend handles (modern, old IPN, classic query params)

[ ] **Task 8.3**: Verify Procfile for Railway migrations
- Confirm `release: alembic upgrade head` is present in `backend/Procfile`
- Add comment/doc note about migration behavior on deploy
- No code changes needed if already correct (it is)

## Review Workload Forecast

- **Estimated total tasks**: 24
- **Estimated changed lines**: ~900-1200 (backend ~400, frontend ~500-700, scripts/docs ~50)
- **Risk level**: High — payment flow + state machine + UI changes
- **Chained PRs recommended**: Yes (Phase 1-3 backend first, Phase 4-7 frontend, Phase 8 devops)
- **400-line budget risk**: High — recommend splitting into 2-3 PRs
- **Review strategy**: Review backend changes first (payment logic + FSM), then frontend (components + integration)
