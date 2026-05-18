# Design: Fix order frontend types and UI

## Technical Approach

Realign the frontend contract to the backend migration/FSM without changing APIs. The implementation updates shared TypeScript order/checkout contracts first, then patches the small set of UI components still hardcoded to legacy values. The confirmation page will stop rendering placeholders and instead use authoritative order detail when a `pedido_id` exists.

## Architecture Decisions

### Decision: Backend files are the contract source

| Option | Tradeoff | Decision |
|--------|----------|----------|
| Trust current frontend unions/maps | Fast, but keeps drift | No |
| Use backend migration + FSM + catalog as authority | Requires touching several UI files | Yes |

**Rationale**: the bug exists because frontend copies diverged from backend reality. The change must start from `state_machine.py`, `models.py`, and migration `20260514_1200`.

### Decision: Keep the fix frontend-only

| Option | Tradeoff | Decision |
|--------|----------|----------|
| Extend backend responses with total/labels | Cleaner payload, but changes API scope | No |
| Reuse existing frontend hooks and fetch detail by `pedido_id` | Small extra request, no API churn | Yes |

**Rationale**: the user asked for a sync fix, not a backend redesign. Fetching order detail keeps the backend authoritative and also fixes refresh behavior on confirmation.

### Decision: Preserve already-correct timeline behavior

| Option | Tradeoff | Decision |
|--------|----------|----------|
| Rewrite `OrderTimeline` alongside other UI | More churn, higher regression risk | No |
| Leave timeline code intact and cover it with regression tests | Smaller diff, keeps verified behavior | Yes |

**Rationale**: verification showed `OrderTimeline` already contains `CANCELADO_ADMIN` and `CANCELADO_CLIENTE` labels plus cancel styling.

## Data Flow

```text
backend migration/FSM/catalog
        │
        ├── order/payment codes
        ▼
frontend shared types
        ├── CheckoutPage payment branching
        ├── OrderStatusBadge / OrderFilters / OrderDetailModal labels
        └── OrderConfirmationPage rendering

checkout success ──→ route state with pedido_id ──→ OrderConfirmationPage
                                                └── useOrderDetail(pedido_id) ──→ order.total
```

## File Changes

| File | Action | Description |
|------|--------|-------------|
| `frontend/src/features/orders/types/orders.types.ts` | Modify | Add cancel subtypes to `EstadoCodigo`; replace `MERCADOPAGO` with migrated payment codes. |
| `frontend/src/features/checkout/types/checkout.types.ts` | Modify | Add semantic UUID alias for `idempotency_key`. |
| `frontend/src/features/checkout/components/CheckoutPage.tsx` | Modify | Switch online-payment gating from legacy `MERCADOPAGO` to `TARJETA`. |
| `frontend/src/features/orders/components/OrderStatusBadge.tsx` | Modify | Map cancel subtypes to explicit destructive labels/variants. |
| `frontend/src/features/orders/components/OrderFilters.tsx` | Modify | Keep filter options aligned with expanded state union. |
| `frontend/src/features/orders/components/OrderDetailModal.tsx` | Modify | Add `TARJETA` label and keep cancel display aligned. |
| `frontend/src/features/orders/components/OrderConfirmationPage.tsx` | Modify | Render actual total from order detail instead of `$Pagado/$Pendiente`. |
| `frontend/src/features/checkout/components/__tests__/PaymentMethodSelector.test.tsx` | Modify | Update payment-code fixtures to `TARJETA`. |
| `frontend/src/features/orders/components/__tests__/OrderTimeline.test.tsx` | Modify | Lock in existing cancel-subtype behavior. |
| `frontend/src/features/orders/components/__tests__/OrderConfirmationPage.test.tsx` | Create | Verify confirmation total and fallback behavior. |

## Interfaces / Contracts

```ts
export type EstadoCodigo =
  | 'PENDIENTE'
  | 'CONFIRMADO'
  | 'EN_PREPARACION'
  | 'TERMINADO'
  | 'ENTREGADO'
  | 'CANCELADO'
  | 'CANCELADO_ADMIN'
  | 'CANCELADO_CLIENTE';

export type FormaPagoCodigo = 'EFECTIVO' | 'TARJETA';
export type UUIDString = string;
```

`CANCELADO` stays as a legacy terminal code because the backend FSM still recognizes it. `UUIDString` is semantic typing only; runtime validation still comes from backend Pydantic and `crypto.randomUUID()` generation.

## Testing Strategy

| Layer | What to Test | Approach |
|-------|-------------|----------|
| Unit | Badge/config rendering for cancel states | Vitest + RTL assertions on labels/classes |
| Integration | Checkout payment-code gating and confirmation totals | Component tests with mocked router/hooks |
| Regression | Timeline cancel-subtype display | Extend existing `OrderTimeline.test.tsx` |

## Migration / Rollout

No backend migration required. Roll out as a single frontend-only change after targeted vitest coverage passes.

## Open Questions

- [ ] `TRANSFERENCIA` remains outside this change; if checkout must support it end-to-end, that needs a separate proposal.
