## Context

El change #26 (checkout-flow-frontend) construyó el flujo de creación de pedido y dejó:
- `OrderConfirmationPage` con un botón "Ir a pagar" que navega a `/cliente/pedidos/:id/pago` — ruta inexistente.
- `toast` de sonner en `useCreateOrder` pero `<Toaster />` nunca montado en el árbol, por lo que los toasts no renderizan.
- `features/payments/` scaffoldeado con `.gitkeep`.

El backend ya expone `POST /api/v1/pagos` y `GET /api/v1/pagos/pedido/{pedido_id}`. El endpoint de creación devuelve `PagoRead` con `init_point` (URL de MercadoPago Checkout Pro). El backend maneja el IPN webhook de MP de forma asincrónica para actualizar el estado del pago.

## Goals / Non-Goals

**Goals:**
- Montar `<Toaster />` en `main.tsx` (fix bloqueante para toasts del #26).
- Wiring de las 3 rutas faltantes en `AppRoute.tsx`.
- `PaymentPage`: llama a `POST /api/v1/pagos`, obtiene `init_point`, redirige al checkout externo de MP.
- `PaymentResultPage`: lee `collection_status` de query params y muestra resultado al cliente.
- Feature folder `features/payments/` con tipos, service y hook.

**Non-Goals:**
- Procesar webhooks IPN (responsabilidad del backend).
- Polling del estado del pago desde el frontend (el backend los actualiza vía IPN).
- Reintentar pagos rechazados (fuera de alcance de este change).
- Mostrar el historial de pagos en detalle (cubierto por el modal de `OrderDetailPage`).

## Decisions

### D1 — Redirect via `window.location.href` (no popup, no `<a>`)

MP Checkout Pro espera una redirección de página completa al `init_point`. `window.open()` abre una pestaña nueva que muchos browsers bloquean por pop-up blocker (no es un click directo del usuario — se ejecuta dentro del `onSuccess` de la mutation). `<a href>` requeriría renderizar después de obtener la URL. La opción correcta es `window.location.href = init_point` dentro del `onSuccess` del hook, que es síncronamente posterior al click del usuario y no requiere re-render.

### D2 — `PaymentResultPage` lee solo query params, sin llamada a API

MP redirige a `/cliente/pago/resultado?collection_status=...&payment_id=...&merchant_order_id=...`. Para mostrar el resultado inmediato al cliente, alcanza con leer `collection_status` del query string. El estado autoritativo del pago lo actualiza el backend vía IPN de forma asincrónica — no tiene sentido hacer un `GET /pagos/pedido/:id` en este momento porque puede no estar actualizado aún. El cliente que quiera ver el estado real puede ir a "Mis pedidos".

### D3 — `PaymentPage` maneja idempotencia a nivel UX, no a nivel cliente

El backend ya tiene idempotency keys en `POST /pagos`. Si el usuario llega a `PaymentPage` y ya existe un pago pendiente para ese pedido, el backend devuelve el `init_point` existente. El frontend no necesita cachear nada — simplemente hace el POST y redirige. Para evitar doble-click: deshabilitar el botón mientras la mutation está en `isPending`.

### D4 — `<Toaster />` en `main.tsx` fuera del router

`<Toaster />` de sonner es un portal — debe estar en el árbol React pero fuera del scope del router para que persista en navegaciones. La ubicación correcta es dentro del `<QueryClientProvider>` pero fuera del `<App />` (donde está el router), o como hermano de `<App />`. Se elige como hermano directo de `<App />` para máxima visibilidad.

### D5 — Feature folder `features/payments/` con tipos, service y hook separados

Consistente con el patrón Feature-First del proyecto (ver #27-D9 del change anterior). Evitar poner lógica de pagos en el feature de checkout o de orders. El feature de payments es autónomo.

### D6 — `useInitPayment` como mutation hook, `usePaymentByOrder` como query hook

`useInitPayment`: wrappea `POST /pagos`, en `onSuccess` hace `window.location.href = data.init_point`. En `onError` muestra toast con descripción del error.

`usePaymentByOrder(pedidoId)`: wrappea `GET /pagos/pedido/:id`, `staleTime: 0` (el estado de pago puede cambiar rápido post-IPN). Útil para que `PaymentPage` verifique si ya hay un pago en curso antes de crear uno nuevo (mejora de UX futura — no bloqueante para este change).

## Risks / Trade-offs

- **[Riesgo] Usuario cierra MP sin completar el pago** → Vuelve desde MP a `/cliente/pago/resultado?collection_status=rejected` o navega directamente a la app. `PaymentResultPage` maneja `collection_status=null/undefined` con un estado neutro ("Resultado desconocido — chequeá tus pedidos").

- **[Riesgo] `init_point` puede ser `null` si el backend retorna `PagoRead` sin `init_point`** → `PaymentPage` debe manejar este caso: mostrar error toast y no redirigir. El tipo `PagoRead` tiene `init_point?: string`.

- **[Riesgo] IPN llega después de que el usuario ya vio el resultado** → El estado que muestra `PaymentResultPage` es solo visual/inmediato basado en query params. El estado real persiste en el backend. El cliente puede ver el estado actualizado en "Mis pedidos". Esta asincronía es inherente al modelo de MP Checkout Pro.

- **[Trade-off] No polling en `PaymentResultPage`** → Más simple, menos carga, pero el estado mostrado puede estar desactualizado si el IPN tarda. Aceptable porque el caso de uso principal es feedback inmediato post-pago; el estado final se ve en el historial de pedidos.
