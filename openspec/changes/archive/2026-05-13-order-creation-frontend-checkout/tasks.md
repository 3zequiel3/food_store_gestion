## 1. Backend — GET /api/v1/formas-pago

- [x] 1.1 Create `FormaPagoRead` schema in `backend/features/catalog/schemas.py` with fields `codigo: str`, `descripcion: str`, `habilitada: bool` (model_config `from_attributes=True`)
- [x] 1.2 Create `listar_formas_pago()` service function in `backend/features/catalog/service.py` — query `FormaPago` where `habilitada=True`, order by `id`
- [x] 1.3 Add `GET /formas-pago` endpoint in `backend/features/catalog/router.py` — `Depends(get_current_user)`, returns `list[FormaPagoRead]`
- [x] 1.4 Add integration test: authenticated user gets enabled payment methods; disabled ones excluded; unauthenticated gets 401
- [x] 1.5 Add `paymentMethods.list` endpoint constant in `frontend/src/lib/constants/endpoints.ts`

## 2. Frontend — CartItem type update

- [x] 2.1 Add `personalizacionIds?: number[]` to `CartItem` type in `cartStore.ts`
- [x] 2.2 Ensure `addItem()` in cartStore accepts and stores `personalizacionIds` (default `undefined`)
- [x] 2.3 Ensure `clearCart()` removes all items including `personalizacionIds`

## 3. Frontend — Checkout types and schemas

- [x] 3.1 Create `frontend/src/features/checkout/types/checkout.types.ts` with `CrearPedidoRequest`, `ItemPedidoPayload`, `CheckoutState`, `PaymentMethodRead` types
- [x] 3.2 Create `frontend/src/features/checkout/schemas/checkoutSchema.ts` with Zod schemas mirroring backend validation (min 1 item, max 50, cantidad ≥ 1, forma_pago_codigo required, direccion_id optional, notas max 500, extra forbid)

## 4. Frontend — Services and hooks

- [x] 4.1 Create `frontend/src/features/checkout/services/orders.service.ts` with `createOrder(payload: CrearPedidoRequest)` function calling `POST /pedidos/`
- [x] 4.2 Create `frontend/src/features/checkout/services/paymentMethods.service.ts` with `getPaymentMethods()` function calling `GET /formas-pago`
- [x] 4.3 Create `frontend/src/features/checkout/hooks/useCreateOrder.ts` as `useMutation` wrapping `createOrder`, with `onSuccess` that calls `cartStore.clearCart()` and navigates to `/cliente/pedidos/:id/confirmacion` with location state
- [x] 4.4 Create `frontend/src/features/checkout/hooks/usePaymentMethods.ts` as `useQuery` wrapping `getPaymentMethods` with `staleTime: 5 * 60_000`

## 5. Frontend — Checkout components

- [x] 5.1 Create `frontend/src/features/checkout/components/AddressSelector.tsx` — radio group showing user addresses from `useAddresses()` + "Retiro en local" option. Returns `selectedAddressId: number | null`. Handles empty addresses (only "Retiro en local")
- [x] 5.2 Create `frontend/src/features/checkout/components/PaymentMethodSelector.tsx` — radio group showing payment methods from `usePaymentMethods()`. Returns `selectedPaymentMethod: string | null`. Shows skeleton while loading
- [x] 5.3 Create `frontend/src/features/checkout/components/OrderSummary.tsx` — table of cart items (nombre, cantidad, precio unit, subtotal), shipping cost ($50 or $0), estimated total, optional `notas` textarea (max 500 chars). Reads from `useCartStore`
- [x] 5.4 Create `frontend/src/features/checkout/components/CheckoutPage.tsx` — orchestrates AddressSelector, PaymentMethodSelector, OrderSummary. Disables "Confirmar pedido" until payment method selected. On submit: validates with `checkoutSchema`, builds payload with `buildOrderPayload()`, calls `useCreateOrder.mutate()`. Shows spinner on button while pending. Error handling: toasts per design D7

## 6. Frontend — OrderConfirmationPage and routing

- [x] 6.1 Create `frontend/src/features/orders/components/OrderConfirmationPage.tsx` — reads `PedidoRead` from location state. Shows: order number, status "PENDIENTE — Esperando pago", items summary from cart, total from response, address or "Retiro en local", buttons "Ir a pagar" (#27) and "Ver mis pedidos" (#28). Fallback: if no location state, shows generic "Pedido creado" with "Ver mis pedidos" link
- [x] 6.2 Update `frontend/src/router/AppRoute.tsx` — replace `PlaceholderPage` for `/cliente/checkout` with `CheckoutPage`, add `/cliente/pedidos/:id/confirmacion` with `OrderConfirmationPage`, both inside `RoleGuard(['CLIENT'])

## 7. Frontend — update CartDrawer navigation (checkout-validation bridge)

- [x] 7.1 Update `CartDrawer.tsx` navigation after successful validation: ensure `navigate('/cliente/checkout')` includes location state `{ validated: true }`
- [x] 7.2 Update `CheckoutPage.tsx` to handle empty cart: if `cartStore.items.length === 0`, show "Tu carrito está vacío" with link to `/cliente/catalogo`

## 8. Tests

- [x] 8.1 Integration test: `GET /api/v1/formas-pago` returns enabled methods, excludes disabled
- [x] 8.2 Integration test: `GET /api/v1/formas-pago` returns 401 for unauthenticated request