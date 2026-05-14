# Proposal: Payment API Integration, Order State Guards & UI Fixes

## Intent

1. **Migrate MercadoPago Checkout Pro → Checkout API**: Current flow redirects users away from the domain. We need inline payment via `sdk.payment().create()` with saved cards and Secure Fields. Rename payment method from `MERCADOPAGO` → `TARJETA`.
2. **Refactor order state machine**: Replace current states with a flow that reflects real business logic — PENDIENTE waits for both admin confirmation AND payment, EN_PREPARACION means paid + confirmed, EN_CAMINO only for delivery orders. Add `CANCELADO_ADMIN` and `CANCELADO_CLIENTE` to distinguish who cancelled and why.
3. **Payment + delivery method validation**: Delivery orders only accept TARJETA or TRANSFERENCIA. Pickup orders accept all methods (TARJETA, EFECTIVO, TRANSFERENCIA).
4. **Order state transition enforcement**: Backend and frontend guards so orders can only move through valid states. The FSM exists but needs updating for the new state flow. `motivo_rechazo` already exists in `HistorialEstadoPedido` — expose it in the UI.
5. **Fix modal visual issues**: AddressModal and OrderDetailModal use `bg-glass backdrop-blur-xl` which creates a dark semi-transparent surface. Switch to opaque `bg-white`.
6. **Local webhook testing with ngrok**: MP requires HTTPS for webhooks. Add ngrok tunnel setup for local dev.

## Scope

### In Scope
- Backend: Replace `sdk.preference().create()` with `sdk.payment().create(data, request_options)`.
- Backend: Accept `card_token`, `payment_method_id`, `installments` in `POST /api/v1/pagos`.
- Backend: Rename payment method `MERCADOPAGO` → `TARJETA` in `payment_methods` table (data migration).
- Backend: New `MetodoPagoUsuario` table + endpoints for saved cards.
- Backend: New order states: `CANCELADO_ADMIN`, `CANCELADO_CLIENTE` (data migration).
- Backend: Update FSM transitions to reflect new state flow.
- Backend: Add delivery-mode validation — delivery orders block EFECTIVO.
- Backend: `POST /api/v1/pedidos/{id}/transicionar` endpoint with FSM + RBAC + `motivo` field.
- Frontend: `@mercadopago/sdk-js` SecureCardForm, inline payment.
- Frontend: Saved cards list + "New Card" option.
- Frontend: PaymentMethodSelector filters by delivery mode (delivery → no EFECTIVO).
- Frontend: Delivery mode selector (Envío del local / Retiro en local).
- Frontend: Order state timeline with valid next-actions, role-gated.
- Frontend: Cancel flow — client blocked from EN_PREPARACION+ with informative message.
- Frontend: Modal visual fix (`bg-glass` → `bg-white`) for AddressModal, OrderDetailModal, PasswordModal.
- DevOps: ngrok tunnel script + docs.

### Out of Scope
- Subscription/recurring auto-charging.
- Multiple payment providers.
- Refund flow via Checkout API.
- Production HTTPS setup (separate change).

## Capabilities

### New Capabilities
- `saved-payment-methods`: Store and list user's saved MercadoPago cards.
- `checkout-api-payment`: Server-side payment creation via `sdk.payment().create()`.
- `delivery-payment-validation`: Enforce payment method validity based on delivery mode.
- `local-webhook-tunnel`: ngrok setup for local MP webhook testing.

### Modified Capabilities
- `payment-mercadopago-frontend`: Redirect flow → inline card form.
- `order-state-machine-fsm`: New states (CANCELADO_ADMIN, CANCELADO_CLIENTE), updated transitions.
- `payment-methods-catalog`: Rename MERCADOPAGO → TARJETA.
- `order-detail-ui`: State timeline, modal visual fix, cancel reason display.
- `delivery-address-ui`: AddressModal visual fix, delivery mode selector.

## Approach

1. **Rename payment method**: Data migration `MERCADOPAGO` → `TARJETA` in `payment_methods` table. Update all references.
2. **New order states**: Data migration to add `CANCELADO_ADMIN` and `CANCELADO_CLIENTE` to `order_states`. Replace existing `CANCELADO` references.
3. **Updated FSM**:
   - `PENDIENTE` → `CONFIRMADO` (payment webhook), `CANCELADO_ADMIN` (admin with motivo), `CANCELADO_CLIENTE` (client)
   - `CONFIRMADO` → `EN_PREPARACION` (admin/pedidos) — means payment received + admin confirmed
   - `EN_PREPARACION` → `EN_CAMINO` (delivery only), `CANCELADO_ADMIN` (admin only with motivo)
   - `EN_CAMINO` → `ENTREGADO` (delivery only)
   - `ENTREGADO` / `CANCELADO_ADMIN` / `CANCELADO_CLIENTE` → terminal
   - Client CANCEL: blocked from `EN_PREPARACION` onwards (show "ya está en preparación" message)
4. **Delivery + payment validation**: Backend service checks `direccion_id` (null = pickup, set = delivery). If delivery + EFECTIVO → reject with 400.
5. **Order state API**: `POST /pedidos/{id}/transicionar` with `estado_codigo_destino` + optional `motivo`.
6. **ngrok tunnel**: `scripts/dev-tunnel.sh` for local webhook testing.

## Affected Areas

| Area | Impact | Description |
|------|--------|-------------|
| `payment_methods` table | Data migration | Rename MERCADOPAGO → TARJETA |
| `order_states` table | Data migration | Add CANCELADO_ADMIN, CANCELADO_CLIENTE; update CANCELADO references |
| `backend/features/orders/state_machine.py` | Modified | New FSM transitions, RBAC rules for new states |
| `backend/features/orders/service.py` | Modified | Delivery + payment validation, motivo handling |
| `backend/features/orders/router.py` | Modified | Add transicionar endpoint, accept motivo in body |
| `backend/features/orders/schemas.py` | Modified | `motivo` field in transition request |
| `backend/features/payments/` | Modified | Checkout API integration, saved cards |
| `frontend/src/features/payments/` | Modified | SecureCardForm, saved cards, inline payment |
| `frontend/src/features/checkout/` | Modified | Delivery mode selector, payment filtering |
| `frontend/src/features/orders/` | Modified | Timeline, cancel flow, modal fix |
| `frontend/src/features/delivery-addresses/` | Modified | AddressModal visual fix |
| `scripts/dev-tunnel.sh` | New | ngrok tunnel script |
| `docs/webhook-testing.md` | New | Local webhook testing guide |

## Risks

| Risk | Likelihood | Mitigation |
|------|------------|------------|
| Double charge without idempotency key | Medium | Always generate UUID4 `x-idempotency-key` per payment attempt |
| MP API error format differs | Medium | Build explicit error mapper |
| PCI compliance regression | Low | Secure Fields (iframes) maintains SAQ-A |
| Invalid state transitions | Medium | Frontend only shows valid next actions; backend enforces FSM |
| Payment method rename breaks existing orders | Low | Only `codigo` changes; FK references update via data migration |
| Existing orders with CANCELADO state | High | Data migration maps CANCELADO → CANCELADO_ADMIN or CANCELADO_CLIENTE based on `historial.cambiado_por_id` (null = admin/system, set = client) |

## Rollback Plan

1. Revert payment method rename: TARJETA → MERCADOPAGO.
2. Remove new order states from `order_states`.
3. Revert FSM to previous transitions.
4. Revert `router.py` to always call `crear_preferencia()`.
5. Revert modal CSS changes.
6. Stop ngrok tunnel, remove script.
7. Drop `metodo_pago_usuario` table via Alembic downgrade.

## Dependencies

- `payment-mercadopago-backend` (#15) — already archived.
- `order-state-machine-fsm` (#16) — already archived, needs update.
- `MP_ACCESS_TOKEN` and `VITE_MP_PUBLIC_KEY` — already configured.

## Success Criteria

- [ ] `POST /api/v1/pagos` with `card_token` returns `201` with `mp_status: 'approved'`.
- [ ] Payment completes without leaving the Food Store domain.
- [ ] User can save a card and see it on subsequent checkouts.
- [ ] Idempotency: same key creates only one payment.
- [ ] Webhook handler continues to work for async notifications.
- [ ] Delivery orders block EFECTIVO → 400 error.
- [ ] Pickup orders accept all payment methods.
- [ ] Frontend shows only valid next state transitions based on FSM + role.
- [ ] Client cannot cancel from EN_PREPARACION+ (blocked with message).
- [ ] Cancel reason (motivo) required and displayed for admin cancellations.
- [ ] Modals show opaque white surfaces — no grey gradient.
- [ ] ngrok tunnel runs locally, MP webhook reaches backend.
- [ ] Payment method table renamed to TARJETA, all references updated.
- [ ] Order states include CANCELADO_ADMIN and CANCELADO_CLIENTE.
