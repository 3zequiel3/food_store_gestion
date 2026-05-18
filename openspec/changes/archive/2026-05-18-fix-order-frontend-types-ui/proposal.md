# Proposal: Fix order frontend types and UI

## Intent

Frontend order and checkout contracts drifted after backend migration `20260514_1200` and the order FSM update. TypeScript unions still miss cancel subtypes, checkout still keys online payment off `MERCADOPAGO`, and some order UI renders stale labels or placeholder totals. This change realigns the frontend with the backend source of truth.

## Scope

### In Scope
- Align order/payment frontend types with backend states and payment codes.
- Fix checkout gating and order UI labels/variants that still assume legacy values.
- Show the real order total on confirmation and add targeted vitest regression coverage.

### Out of Scope
- Backend migrations, seed cleanup, or API/schema changes.
- New checkout support for `TRANSFERENCIA` or broader payment-flow redesign.

## Capabilities

### New Capabilities
- None.

### Modified Capabilities
- `order-creation-frontend`: checkout payment-code handling, confirmation summary, and idempotency typing must match backend contracts.
- `order-visualization-frontend`: order status types, labels, badges, filters, and modal payment labels must match migrated backend values.

## Approach

Use `backend/features/orders/state_machine.py`, `backend/features/catalog/models.py`, and migration `20260514_1200_payment_order_state_refactor.py` as the authority. Update shared frontend type unions first, then patch affected checkout/order components and tests. Verified note: `OrderTimeline` is already aligned with `CANCELADO_ADMIN` and `CANCELADO_CLIENTE`, so this change preserves it with regression coverage instead of rewriting it.

## Affected Areas

| Area | Impact | Description |
|------|--------|-------------|
| `frontend/src/features/orders/types/orders.types.ts` | Modified | Expand order/payment unions to migrated backend values. |
| `frontend/src/features/checkout/components/CheckoutPage.tsx` | Modified | Replace legacy `MERCADOPAGO` gating with `TARJETA`. |
| `frontend/src/features/orders/components/*` | Modified | Fix badge, filters, modal labels, and confirmation summary. |
| `frontend/src/features/checkout/components/__tests__/PaymentMethodSelector.test.tsx` | Modified | Update payment-code regression coverage. |
| `frontend/src/features/orders/components/__tests__/*` | Modified/New | Add regression coverage for cancel states and confirmation totals. |

## Risks

| Risk | Likelihood | Mitigation |
|------|------------|------------|
| Type widening exposes stale switch branches | Med | Audit every `EstadoCodigo`/payment-code consumer before apply. |
| Confirmation page adds fetch-dependent UI state | Low | Keep route-state fallback and fetch only authoritative detail by `pedido_id`. |

## Rollback Plan

Revert the frontend-only file changes in checkout/order features and restore the prior unions, labels, and confirmation rendering. No DB rollback is required.

## Dependencies

- Backend migration `20260514_1200_payment_order_state_refactor.py` already applied.
- Backend FSM in `backend/features/orders/state_machine.py` remains the source of truth.

## Success Criteria

- [ ] Frontend accepts `CANCELADO_ADMIN`, `CANCELADO_CLIENTE`, and `TARJETA` without type or UI drift.
- [ ] Order badges, filters, modal labels, checkout gating, and confirmation totals match backend data.
- [ ] Targeted vitest coverage protects the migrated contract from regressions.
