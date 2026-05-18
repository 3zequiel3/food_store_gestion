## Purpose

Actualización del requirement de navegación post-validación: el `useValidateCart` ahora debe pasar datos del carrito al checkout via location state para que la página de checkout pueda armar el payload sin re-fetch.

## CHANGED Requirements

### Requirement: Navegación post-validación con location state

Tras validación exitosa del carrito (sin stock issues ni price changes), el sistema SHALL navegar a `/cliente/checkout` pasando `cartItems` como location state. La `CheckoutPage` SHALL leer los items del `cartStore` directamente (no del location state) — la navegación con state existe como guard semántico para asegurar que la página solo es accesible después de validación. Si un usuario navega directamente a `/cliente/checkout` sin items en el carrito, el sistema SHALL mostrar un mensaje "Tu carrito está vacío" con link al catálogo.

**Cambio en `checkout-pay-first-flow`**: la `CheckoutPage` deja de armar un payload para `POST /api/v1/pedidos/` y pasa a armar payload para `POST /api/v1/checkout/online` o `POST /api/v1/checkout/pickup-efectivo`, según la combinación de "forma de pago" y "tipo de entrega" elegida por el usuario. La validación pre-checkout (`useValidateCart`) no cambia — sigue validando stock y precios contra el catálogo antes de avanzar al checkout.

#### Scenario: Navegación directa al checkout sin items
- **WHEN** el usuario navega a `/cliente/checkout` con el carrito vacío
- **THEN** se muestra "Tu carrito está vacío" con un link a `/cliente/catalogo`

#### Scenario: Navegación post-validación exitosa
- **WHEN** la validación del carrito pasa sin issues
- **THEN** se navega a `/cliente/checkout` y la página muestra los items del carrito
- **AND** el `idempotency_key` se genera al montar el componente

#### Scenario: idempotency_key fresco al entrar al checkout
- **WHEN** el usuario llega a `/cliente/checkout` por primera vez (o vuelve después de salir)
- **THEN** se genera un nuevo `idempotency_key` (UUID4) que será usado por el `useCheckoutOnline` durante esa sesión de checkout
