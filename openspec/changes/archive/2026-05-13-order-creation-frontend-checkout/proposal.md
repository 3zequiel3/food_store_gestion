## Why

El cliente necesita una UI para confirmar su carrito validado, seleccionar dirección de entrega y forma de pago, ver un resumen con totales calculados (subtotal + envío), y crear un pedido contra `POST /api/v1/pedidos`. Tras la creación exitosa, el cliente debe recibir feedback visual claro (US-035, US-071). Este change cierra el flujo de checkout — el eslabón entre el carrito validado y la confirmación del pedido.

## What Changes

- **CheckoutPage**: Página completa en `/cliente/checkout` que orquesta la selección de dirección, forma de pago, resumen de items con snapshots de precio, cálculo de subtotal + envío, y notas opcionales. Reemplaza el `PlaceholderPage` actual.
- **Checkout flow**: Tras validación exitosa del carrito (change anterior `checkout-validation-frontend`), el usuario llega al checkout. Al confirmar, se envía `POST /api/v1/pedidos` con los datos del carrito, dirección seleccionada, forma de pago y notas.
- **Selección de dirección**: Componente para elegir dirección de entrega existente o "Retiro en local" (sin dirección, envío $0). Reutiliza `useAddresses()` del change `delivery-addresses-frontend`.
- **Selección de forma de pago**: Componente para elegir la forma de pago. El backend NO expone endpoint para listar formas de pago habilitadas → se agrega `GET /api/v1/formas-pago` (público, autenticado) que devuelve las formas habilitadas.
- **Resumen de pedido**: Tabla con items del carrito (nombre, cantidad, precio unitario, subtotal por línea), costo de envío, y total. Los precios ya están validados por `checkout-validation-frontend`.
- **Orden de creación**: `useCreateOrder` hook (TanStack Query mutation) que mapea el carrito → `CrearPedidoRequest` y envía al backend. Mapea `CartItem.personalizacion` (string en cart) → `personalizacion: number[]` (IDs de ingredientes excluidos) para el backend.
- **Post-creación**: Redirección a `OrderConfirmationPage` en `/cliente/pedidos/{id}/confirmacion` con número de pedido, resumen, estado PENDIENTE, y botones "Ir a pagar" y "Ver mis pedidos".
- **Limpieza de carrito**: Tras creación exitosa, `cartStore.clearCart()`.
- **Manejo de errores**: Mapeo de errores del backend (422 stock insuficiente, 422 forma de pago inválida, 404 dirección no encontrada, 401/403) a feedback visual tipo toast.

## Capabilities

### New Capabilities
- `order-creation-frontend`: UI de checkout completa — selección de dirección, forma de pago, resumen con totales, llamada a `POST /api/v1/pedidos`, y pantalla de confirmación post-creación (US-035, US-071)
- `payment-methods-backend`: Endpoint `GET /api/v1/formas-pago` que devuelve formas de pago habilitadas — gap detectado: el frontend necesita listar las opciones antes de crear el pedido

### Modified Capabilities
- `checkout-validation`: Se agrega requirement de navegación post-validación exitosa → `navigate('/cliente/checkout')` con datos del carrito como estado de location (necesario para el bridge entre validación y checkout)

## Impact

- **Frontend — nuevos archivos**:
  - `features/checkout/components/CheckoutPage.tsx` (página principal)
  - `features/checkout/components/AddressSelector.tsx` (selección de dirección)
  - `features/checkout/components/PaymentMethodSelector.tsx` (selección de forma de pago)
  - `features/checkout/components/OrderSummary.tsx` (resumen con totales)
  - `features/checkout/components/CheckoutForm.tsx` (formulario tanstack orquestador)
  - `features/checkout/hooks/useCreateOrder.ts` (mutation)
  - `features/checkout/hooks/usePaymentMethods.ts` (query)
  - `features/checkout/schemas/checkoutSchema.ts` (Zod validation)
  - `features/checkout/services/orders.service.ts` (API call)
  - `features/checkout/types/checkout.types.ts`
  - `features/orders/components/OrderConfirmationPage.tsx` (pantalla post-creación)
- **Frontend — rutas**: Reemplazar `PlaceholderPage` por `CheckoutPage` en `/cliente/checkout`, agregar `/cliente/pedidos/:id/confirmacion`
- **Backend — nuevo endpoint**: `GET /api/v1/formas-pago` en `features/catalog/router.py` con `FormaPagoRead` schema (solo formas con `habilitada=True`)
- **Dependencias**: `order-creation-backend` ✅, `checkout-validation-frontend` ✅, `delivery-addresses-frontend` ✅