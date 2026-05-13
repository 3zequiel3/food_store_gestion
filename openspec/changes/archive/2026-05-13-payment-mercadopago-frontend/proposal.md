## Why

El change #26 construyó el checkout que crea el pedido y tiene una página de confirmación con un botón "Ir a pagar" que navega a `/cliente/pedidos/:id/pago`. Esa ruta no existe todavía. Además el `<Toaster />` de sonner nunca se montó en el árbol de la app, por lo que los toasts del checkout tampoco funcionan. Este change cierra el ciclo: el cliente crea el pedido → inicia el pago con MercadoPago → vuelve a la app con el resultado.

## What Changes

- `<Toaster />` de sonner agregado en `main.tsx` (fix bloqueante para toasts del #26).
- Nueva página `PaymentPage` en `/cliente/pedidos/:id/pago`: llama a `POST /api/v1/pagos` con el `pedido_id`, obtiene el `init_point` y redirige al checkout externo de MercadoPago.
- Nueva página `PaymentResultPage` en `/cliente/pago/resultado`: página de retorno que MercadoPago redirige al cliente después del pago. Lee `collection_status` de los query params y muestra el resultado (aprobado / pendiente / rechazado).
- `OrderConfirmationPage` ya montada en su ruta (`/cliente/pedidos/:id/confirmacion`), hoy sin ruta en el router.
- Feature folder `features/payments/` con tipos, service y hooks para las llamadas a `/api/v1/pagos`.

## Capabilities

### New Capabilities
- `payment-mercadopago-frontend`: UI para iniciar pago con MercadoPago y manejar el retorno post-pago.

### Modified Capabilities
- (ninguna — los requisitos del backend no cambian)

## Impact

- **Nuevos archivos**: `features/payments/types/`, `features/payments/services/`, `features/payments/hooks/`, `pages/client/PaymentPage.tsx`, `pages/client/PaymentResultPage.tsx`
- **Modificados**: `main.tsx` (Toaster), `router/AppRoute.tsx` (3 rutas nuevas: confirmación, pago, resultado)
- **APIs consumidas**: `POST /api/v1/pagos`, `GET /api/v1/pagos/pedido/{pedido_id}`
- **Flujo externo**: redirección a `init_point` (URL de MercadoPago Checkout Pro)
