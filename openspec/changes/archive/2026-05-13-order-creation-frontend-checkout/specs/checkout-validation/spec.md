## Purpose

Actualización del requirement de navegación post-validación: el `useValidateCart` ahora debe pasar datos del carrito al checkout via location state para que la página de checkout pueda armar el payload sin re-fetch.

## CHANGED Requirements

### Requirement: Navegación post-validación con location state

(Reemplaza el requirement original "Botón 'Ir al checkout' dispara validación" en la sección de navegación.)

Tras validación exitosa del carrito (sin stock issues ni price changes), el sistema SHALL navegar a `/cliente/checkout` pasando `cartItems` como location state. La `CheckoutPage` SHALL leer los items del `cartStore` directamente (no del location state) pero la navegación con state asegura que la página solo es accesible después de validación. Si un usuario navega directamente a `/cliente/checkout` sin items en el carrito, SHALL mostrar un mensaje "Tu carrito está vacío" con link al catálogo.

#### Scenario: Navegación directa al checkout sin items
- **WHEN** el usuario navega a `/cliente/checkout` con el carrito vacío
- **THEN** se muestra "Tu carrito está vacío" con un link a `/cliente/catalogo`

#### Scenario: Navegación post-validación exitosa
- **WHEN** la validación del carrito pasa sin issues
- **THEN** se navega a `/cliente/checkout` y la página muestra los items del carrito
