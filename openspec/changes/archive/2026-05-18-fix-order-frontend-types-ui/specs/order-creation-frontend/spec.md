# Delta for order-creation-frontend

## ADDED Requirements

### Requirement: Checkout idempotency key is explicitly typed as UUID

The frontend checkout contract SHALL model `idempotency_key` as a semantic UUID string type while remaining wire-compatible with the backend `UUID` field.

#### Scenario: Online checkout payload preserves UUID semantics

- GIVEN `CheckoutPage` generates an idempotency key with `crypto.randomUUID()`
- WHEN the payload is typed in TypeScript
- THEN `idempotency_key` is represented as an explicit UUID string alias

## MODIFIED Requirements

### Requirement: Página de checkout con cuatro secciones

El sistema SHALL renderizar `CheckoutPage` en `/cliente/checkout` con cuatro secciones: `AddressSelector`, `PaymentMethodSelector`, `PaymentForm` (cuando aplica) y `OrderSummary`. La página SHALL mostrar un botón "Confirmar y pagar" (online) o "Confirmar pedido" (pickup+efectivo) que invoca el hook de checkout correspondiente (`useCheckoutOnline` o `useCheckoutPickupEfectivo`). Mientras la mutation está pendiente, el botón SHALL mostrar un spinner y estar deshabilitado. El branch de pago online SHALL activarse con el código backend `TARJETA`; el frontend SHALL NOT depender del valor legado `MERCADOPAGO`. (Previously: el branch online estaba atado a `MERCADOPAGO`.)

#### Scenario: Checkout online con TARJETA requiere PaymentForm visible
- WHEN un cliente selecciona forma de pago `TARJETA`
- THEN la sección `PaymentForm` se renderiza inline dentro de `CheckoutPage`
- AND el botón "Confirmar y pagar" está deshabilitado hasta que exista un `card_token` válido

#### Scenario: Checkout pickup+efectivo no muestra PaymentForm
- WHEN el cliente selecciona forma de pago `EFECTIVO` y elige "Retiro en local"
- THEN la sección `PaymentForm` NO se renderiza
- AND el botón muestra texto "Confirmar pedido"

#### Scenario: Botón deshabilitado durante el checkout
- WHEN el cliente hace click en el botón de confirmar y la mutation está en curso
- THEN el botón muestra un spinner y está deshabilitado
- AND no se puede hacer click de nuevo

### Requirement: Pantalla de confirmación post-creación (OrderConfirmationPage)

Tras `200 OK` de cualquiera de los dos endpoints de checkout, el sistema SHALL redirigir a `/cliente/pedidos/:id/confirmacion` con el response como location state. La página SHALL mostrar: número de pedido (`pedido_id`), estado `"PENDIENTE — Esperando que el local acepte tu pedido"`, resumen de items (si hay snapshot en state), total real del pedido y dirección si aplica. Cuando `pedido_id` esté disponible, la página SHOULD recuperar el detalle del pedido para renderizar el total autoritativo del backend y soportar refresh. Tras la redirección exitosa, el carrito SHALL ser limpiado vía `cartStore.clearCart()`. Ya NO se incluye el botón "Ir a pagar". (Previously: la página mostraba placeholders `$Pagado`/`$Pendiente` en vez del monto.)

#### Scenario: Confirmación post-checkout online aprobado muestra total real
- WHEN `POST /checkout/online` devuelve `200` con `pedido_id`
- THEN la confirmación muestra ID, estado y el monto real del pedido
- AND NO se muestra ningún placeholder textual en el campo total
- AND el carrito queda vacío
- AND NO se muestra ningún botón "Ir a pagar"

#### Scenario: Confirmación post-checkout pickup+efectivo
- WHEN `POST /checkout/pickup-efectivo` devuelve `200`
- THEN se navega a la confirmación mostrando "Retiro en local — Pagás al retirar"
- AND la página muestra el monto real del pedido
- AND el carrito queda vacío

#### Scenario: Fallback sin location state
- WHEN el usuario llega a la confirmación sin location state pero con `pedido_id` en la URL
- THEN la página intenta cargar el detalle del pedido
- AND si la carga resulta exitosa, renderiza el total real en lugar del fallback genérico
- AND si la carga falla, mantiene el fallback "Pedido creado" con botón "Ver mis pedidos"
