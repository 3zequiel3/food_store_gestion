## 1. Fix bloqueante — Toaster y ruta de confirmación

- [x] 1.1 Agregar `<Toaster />` de sonner en `frontend/src/main.tsx` como hermano de `<App />`
- [x] 1.2 Registrar ruta `/cliente/pedidos/:id/confirmacion` → `OrderConfirmationPage` en `AppRoute.tsx`

## 2. Feature folder payments — tipos, service y hooks

- [x] 2.1 Crear `frontend/src/features/payments/types/payments.types.ts` con tipo `PagoCreate` y `PagoRead` (mirrors backend schema)
- [x] 2.2 Crear `frontend/src/features/payments/services/payments.service.ts` con `initiatePayment(pedidoId)` y `getPaymentByOrder(pedidoId)`
- [x] 2.3 Crear `frontend/src/features/payments/hooks/useInitPayment.ts` — mutation que llama a `initiatePayment`, en `onSuccess` hace `window.location.href = data.init_point`, en `onError` muestra toast
- [x] 2.4 Crear `frontend/src/features/payments/hooks/usePaymentByOrder.ts` — query con `staleTime: 0`, habilitada solo cuando `pedidoId` es no-nulo

## 3. PaymentPage

- [x] 3.1 Crear `frontend/src/pages/client/PaymentPage.tsx`: llama a `useInitPayment` con `pedidoId` del param de ruta, muestra spinner mientras `isPending`, muestra error con botón "Volver" si falla o si `init_point` es nulo
- [x] 3.2 Registrar ruta `/cliente/pedidos/:id/pago` → `PaymentPage` en `AppRoute.tsx`

## 4. PaymentResultPage

- [x] 4.1 Crear `frontend/src/pages/client/PaymentResultPage.tsx`: lee `collection_status` de `useSearchParams`, muestra resultado (aprobado / pendiente / rechazado / fallback neutro) con botones de navegación
- [x] 4.2 Registrar ruta `/cliente/pago/resultado` → `PaymentResultPage` en `AppRoute.tsx`
