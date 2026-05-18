# Tasks: Fix order frontend types and UI

## Review Workload Forecast

| Field | Value |
|-------|-------|
| Estimated changed lines | 220-320 |
| 400-line budget risk | Medium |
| Chained PRs recommended | No |
| Suggested split | Single PR |
| Delivery strategy | ask-on-risk |
| Chain strategy | pending |

Decision needed before apply: No
Chained PRs recommended: No
Chain strategy: pending
400-line budget risk: Medium

### Suggested Work Units

| Unit | Goal | Likely PR | Notes |
|------|------|-----------|-------|
| 1 | Contract + UI sync for order/checkout frontend | PR 1 | Single review slice with tests included |

## Phase 1: Contract alignment

- [x] 1.1 Update `frontend/src/features/orders/types/orders.types.ts` to include `CANCELADO_ADMIN` and `CANCELADO_CLIENTE`, while preserving legacy `CANCELADO`.
- [x] 1.2 Update `frontend/src/features/checkout/types/checkout.types.ts` so `idempotency_key` uses an explicit semantic UUID string alias.
- [x] 1.3 Replace legacy `MERCADOPAGO` checks in `frontend/src/features/checkout/components/CheckoutPage.tsx` with migrated `TARJETA` handling.

## Phase 2: Order UI sync

- [x] 2.1 Update `frontend/src/features/orders/components/OrderStatusBadge.tsx` so all cancel variants render destructive labels instead of neutral fallback.
- [x] 2.2 Update `frontend/src/features/orders/components/OrderDetailModal.tsx` with a `TARJETA` payment label and keep cancel messaging aligned.
- [x] 2.3 Update `frontend/src/features/orders/components/OrderFilters.tsx` so filter options stay consistent with the expanded state union.

## Phase 3: Confirmation summary

- [x] 3.1 Update `frontend/src/features/orders/components/OrderConfirmationPage.tsx` to render the real order total from authoritative detail data, not `$Pagado/$Pendiente` placeholders.
- [x] 3.2 Keep route-state success context for UX, but recover total/details by `pedido_id` on refresh or direct navigation.

## Phase 4: Targeted regression tests

- [x] 4.1 Update `frontend/src/features/checkout/components/__tests__/PaymentMethodSelector.test.tsx` fixtures/assertions from `MERCADOPAGO` to `TARJETA`.
- [x] 4.2 Add or extend tests for `OrderStatusBadge` and `OrderTimeline` covering `CANCELADO_ADMIN` and `CANCELADO_CLIENTE` scenarios from the spec.
- [x] 4.3 Create `frontend/src/features/orders/components/__tests__/OrderConfirmationPage.test.tsx` to verify actual total rendering and refresh fallback behavior.
