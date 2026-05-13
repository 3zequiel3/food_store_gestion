## 1. cartStore — updateItemPrice action

- [x] 1.1 Add `updateItemPrice(producto_id: number, precio: number): void` to `CartActions` interface in `cartStore.ts`
- [x] 1.2 Implement `updateItemPrice` in the store: map items, update `precio` on matching `producto_id`, leave all other fields unchanged

## 2. Checkout types

- [x] 2.1 Create `features/checkout/types/validation.types.ts` with `StockIssue`, `PriceChange`, and `ValidationResult` interfaces

## 3. useValidateCart hook

- [x] 3.1 Create `features/checkout/hooks/useValidateCart.ts` with `validateCartItems` mutationFn that calls `getProduct(id)` in parallel via `Promise.all` for all cart items
- [x] 3.2 Classify results: stock issues (`!disponible || stock_cantidad < cantidad`) and price changes (`|precio_backend - precio_carrito| > 0.01`)
- [x] 3.3 Return `ValidationResult` from the mutation

## 4. CartValidationModal component

- [x] 4.1 Create `features/checkout/components/CartValidationModal.tsx` as a native `<dialog>` element
- [x] 4.2 Stock issues mode: list affected products with available stock (or "Sin stock"), single "Entendido" button, no continue option
- [x] 4.3 Price changes mode: list products with old → new price, "Actualizar precios y continuar" + "Cancelar" buttons
- [x] 4.4 "Actualizar precios y continuar" calls `updateItemPrice` for each affected item then navigates to `/cliente/checkout`

## 5. CartDrawer — wire validation

- [x] 5.1 Import and call `useValidateCart` in `CartDrawer.tsx`
- [x] 5.2 Replace the disabled checkout button with an enabled button that calls `mutate()` on click
- [x] 5.3 Show spinner and disable button while `isPending === true`
- [x] 5.4 On mutation success: if no issues → close drawer and navigate to `/cliente/checkout`; else → open `CartValidationModal` with the result
- [x] 5.5 Integrate `CartValidationModal` into `CartDrawer` JSX with open state management

## 6. AppRoute — checkout placeholder

- [x] 6.1 Add `<Route path="checkout" element={<PlaceholderPage title="Checkout" description="Finalización del pedido — llega en #26." />} />` inside the `/cliente` layout in `AppRoute.tsx`
