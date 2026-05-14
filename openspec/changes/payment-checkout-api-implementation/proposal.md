# Proposal: Payment API Integration, Order State Guards & UI Fixes

## Intent

1. **Migrate MercadoPago Checkout Pro → Checkout API**: Current flow redirects users away from the domain. We need inline payment via `sdk.payment().create()` with saved cards and Secure Fields.
2. **Order state transition enforcement**: Add backend and frontend guards so orders can only move through valid states (PENDIENTE → CONFIRMADO → EN_PREPARACION → EN_CAMINO → ENTREGADO). The FSM exists but the UI allows invalid jumps (e.g., PENDIENTE → ENTREGADO directly).
3. **Fix modal visual issues**: AddressModal and OrderDetailModal use `bg-glass backdrop-blur-xl` which creates a dark semi-transparent surface that looks like a "grey gradient" on most backgrounds. Switch to opaque `bg-white` surfaces.
4. **Local webhook testing with ngrok**: MercadoPago requires HTTPS for webhook notifications. Add ngrok tunnel setup so the local backend can receive real MP webhooks during development.

## Scope

### In Scope
- Backend: Replace `sdk.preference().create()` with `sdk.payment().create(data, request_options)` in `PaymentService`.
- Backend: Accept `card_token`, `payment_method_id`, `installments` in `POST /api/v1/pagos`.
- Backend: New `MetodoPagoUsuario` table + endpoints to save/list saved cards.
- Backend: Expose FSM transitions via `POST /api/v1/pedidos/{id}/transicionar` endpoint with role validation.
- Frontend: Install `@mercadopago/sdk-js`, build `SecureCardForm` component using MP.js Secure Fields.
- Frontend: Update `PaymentPage` to tokenize card inline → send token → handle synchronous `status: 'approved'` response.
- Frontend: Show saved cards list + "New Card" option in checkout.
- Frontend: Order detail page shows state timeline with valid next-actions only.
- Frontend: Fix modal surfaces from `bg-glass` → `bg-white` (AddressModal, OrderDetailModal, PasswordModal).
- DevOps: ngrok tunnel script + config for local webhook testing.
- Idempotency: Pass `x-idempotency-key` header to `sdk.payment().create()`.
- Procfile verification: Confirm `release: alembic upgrade head` runs on Railway deploy.

### Out of Scope
- Subscription/recurring auto-charging (saved cards enable it, but auto-charge is deferred).
- Multiple payment providers (Stripe, PayPal, etc.).
- Refund flow via Checkout API.
- 3D Secure / authentication challenges (MP handles via Secure Fields).
- Production HTTPS setup (separate change).

## Capabilities

### New Capabilities
- `saved-payment-methods`: Store and list user's saved MercadoPago cards (`MetodoPagoUsuario` table, CRUD endpoints, frontend card selector).
- `checkout-api-payment`: Server-side payment creation via `sdk.payment().create()` with card tokenization, synchronous approval handling, and idempotency.
- `order-state-transitions`: FSM-enforced state transitions with RBAC, exposed via API endpoint + frontend timeline UI showing only valid next actions.
- `local-webhook-tunnel`: ngrok setup script + documentation for local MP webhook testing.

### Modified Capabilities
- `payment-mercadopago-frontend`: PaymentPage changes from redirect-to-MP flow → inline card form + immediate approval/rejection handling.
- `order-detail-ui`: OrderDetailModal switches from `bg-glass` → `bg-white`, fixes readability.
- `delivery-address-ui`: AddressModal switches from `bg-glass` → `bg-white`, fixes readability.

## Approach

1. **Backend service**: Add `crear_pago_api()` method to `PaymentService`. On approval, call `OrderService.transicionar_estado()` with `actor_id=None` (SISTEMA) → PENDIENTE → CONFIRMADO.
2. **Order state API**: New `POST /api/v1/pedidos/{id}/transicionar` endpoint. Receives `estado_codigo_destino`, validates via FSM + RBAC, appends to `HistorialEstadoPedido`.
3. **Frontend order timeline**: Replace static status badge with interactive timeline. Shows current state + valid next actions as buttons. Role-gated (client only sees CANCELAR from PENDIENTE).
4. **Modal fix**: Replace `bg-glass backdrop-blur-xl` → `bg-white shadow-xl` in AddressModal, OrderDetailModal, PasswordModal.
5. **ngrok tunnel**: Script `scripts/dev-tunnel.sh` starts ngrok on port 8000, prints HTTPS URL. Webhook URL configured dynamically or via `.env`.
6. **Saved cards**: New `MetodoPagoUsuario` table + CRUD endpoints. Frontend shows selector in checkout.

## Affected Areas

| Area | Impact | Description |
|------|--------|-------------|
| `backend/features/payments/service.py` | Modified | Add `crear_pago_api()`, saved cards methods |
| `backend/features/payments/router.py` | Modified | New fields in `PagoCreate`, branch API/Pro flow, add `/metodos-pago` routes |
| `backend/features/payments/schemas.py` | Modified | Add `card_token`, `payment_method_id`, `installments` |
| `backend/features/payments/models.py` | New | `MetodoPagoUsuario` table |
| `backend/features/orders/router.py` | Modified | Add `POST /pedidos/{id}/transicionar` endpoint |
| `backend/features/orders/service.py` | Modified | Expose `transicionar_estado()` for router |
| `frontend/src/features/orders/` | Modified | Order detail with timeline, state transition buttons |
| `frontend/src/features/delivery-addresses/` | Modified | AddressModal visual fix |
| `frontend/src/features/user-profile/` | Modified | PasswordModal visual fix |
| `frontend/src/features/payments/` | Modified | SecureCardForm, saved cards UI, inline payment |
| `scripts/dev-tunnel.sh` | New | ngrok tunnel script |
| `docs/webhook-testing.md` | New | ngrok + MP webhook local testing guide |

## Risks

| Risk | Likelihood | Mitigation |
|------|------------|------------|
| Double charge without idempotency key | Medium | Always generate UUID4 `x-idempotency-key` per payment attempt |
| MP API error format differs from Preferences | Medium | Build explicit error mapper for `sdk.payment().create()` responses |
| PCI compliance regression | Low | Secure Fields (iframes) ensures card data never touches our server |
| Invalid state transitions in frontend | Medium | Frontend only shows valid next actions; backend enforces FSM |
| Webhook not received during local dev | High | ngrok tunnel provides HTTPS URL; configure in MP dashboard |

## Rollback Plan

1. Revert `router.py` to always call `crear_preferencia()` (remove API branch).
2. Revert `orders/router.py` to remove transicionar endpoint.
3. Revert modal CSS changes (harmless, but revert for cleanliness).
4. Stop ngrok tunnel, remove script.
5. Drop `metodo_pago_usuario` table via Alembic downgrade.
6. Redeploy — users return to Checkout Pro redirect flow. No data loss.

## Dependencies

- `payment-mercadopago-backend` (#15) — already archived, provides base payment infrastructure.
- `order-state-machine-fsm` (#16) — already archived, provides `state_machine.py` with FSM + RBAC.
- `MP_ACCESS_TOKEN` and `VITE_MP_PUBLIC_KEY` — already configured in `.env`.

## Success Criteria

- [ ] `POST /api/v1/pagos` with `card_token` returns `201` with `mp_status: 'approved'` within 3 seconds.
- [ ] Payment completes without leaving the Food Store domain.
- [ ] User can save a card and see it listed on subsequent checkouts.
- [ ] Idempotency: same `card_token` + `pedido_id` with same key creates only one payment.
- [ ] Webhook handler continues to work for async notifications.
- [ ] Frontend shows only valid next state transitions based on FSM + user role.
- [ ] Modals (AddressModal, OrderDetailModal) show opaque white surfaces — no grey gradient.
- [ ] ngrok tunnel runs locally, MP webhook reaches backend successfully.
- [ ] Procfile `release:` step confirmed to run `alembic upgrade head` on Railway.
