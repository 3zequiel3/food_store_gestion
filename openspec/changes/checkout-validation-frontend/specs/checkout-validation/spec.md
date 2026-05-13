## Purpose

Validación pre-checkout del carrito: verifica disponibilidad de stock y detecta cambios de precio consultando el backend antes de navegar al checkout. Implementa US-069 y US-070.

## ADDED Requirements

### Requirement: Botón "Ir al checkout" dispara validación
El sistema SHALL habilitar el botón "Ir al checkout" en `CartDrawer`. Al hacer click SHALL disparar `useValidateCart` que llama `GET /productos/{id}` en paralelo para todos los ítems del carrito. Mientras valida SHALL mostrar un spinner en el botón y deshabilitarlo. Si la validación pasa sin issues SHALL navegar a `/cliente/checkout` sin mostrar ningún modal.

#### Scenario: Carrito válido navega directo al checkout
- **WHEN** el usuario hace click en "Ir al checkout" y todos los productos tienen stock suficiente y precios sin cambios
- **THEN** el drawer se cierra y el usuario es redirigido a /cliente/checkout sin ningún modal

#### Scenario: Spinner durante la validación
- **WHEN** la validación está en curso
- **THEN** el botón "Ir al checkout" muestra spinner y está deshabilitado

### Requirement: Modal de stock insuficiente (bloqueante)
Si uno o más ítems del carrito tienen `disponible === false` o `stock_cantidad < cantidad_en_carrito`, el sistema SHALL mostrar `CartValidationModal` listando los productos afectados con el stock disponible actual. El modal SHALL tener solo el botón "Entendido" (sin opción de continuar) — el usuario debe ajustar el carrito antes de proceder. (US-069)

#### Scenario: Modal bloqueante con item sin stock
- **WHEN** un ítem del carrito tiene disponible=false en el backend
- **THEN** el modal muestra ese producto con el mensaje "Sin stock" y no ofrece opción de continuar

#### Scenario: Modal bloqueante con stock insuficiente
- **WHEN** el carrito tiene 5 unidades de un producto pero el backend reporta stock_cantidad=2
- **THEN** el modal muestra "Stock disponible: 2" para ese producto

#### Scenario: Stock issues bloquean aunque haya también cambios de precio
- **WHEN** hay ítems con stock insuficiente y otros con precio cambiado
- **THEN** el modal muestra solo los stock issues y el botón "Entendido" — no se ofrece continuar

### Requirement: Modal de cambio de precio (informativo)
Si no hay stock issues pero uno o más ítems tienen precio diferente al guardado en el carrito (`|precio_backend - precio_carrito| > 0.01`), el sistema SHALL mostrar `CartValidationModal` listando los productos con precio viejo y nuevo. El modal SHALL tener dos botones: "Actualizar precios y continuar" (actualiza precios en cartStore y navega a `/cliente/checkout`) y "Cancelar" (cierra modal sin cambios). (US-070)

#### Scenario: Modal informativo con precios actualizados
- **WHEN** un producto en el carrito cuesta $100 pero el backend devuelve $120
- **THEN** el modal muestra "Precio actualizado: $100 → $120" para ese producto

#### Scenario: Confirmar precios actualiza el cartStore y navega
- **WHEN** el usuario hace click en "Actualizar precios y continuar"
- **THEN** el cartStore actualiza el precio de cada ítem afectado y el usuario es redirigido a /cliente/checkout

#### Scenario: Cancelar cierra el modal sin cambios
- **WHEN** el usuario hace click en "Cancelar"
- **THEN** el modal se cierra, el carrito mantiene los precios originales y el usuario permanece en la página actual

### Requirement: acción updateItemPrice en cartStore
El sistema SHALL exponer `updateItemPrice(producto_id: number, precio: number)` en el cartStore. La acción SHALL actualizar el campo `precio` del ítem correspondiente sin tocar ningún otro campo. SHALL ser persistida en localStorage (misma partialize que el resto de items). (soporte para sincronización de precios post-validación)

#### Scenario: updateItemPrice actualiza solo el precio
- **WHEN** se llama updateItemPrice(42, 150)
- **THEN** el ítem con producto_id=42 tiene precio=150 y todos los demás campos permanecen iguales

#### Scenario: getTotalPrice refleja el precio actualizado
- **WHEN** se actualiza el precio de un ítem via updateItemPrice
- **THEN** getTotalPrice() retorna el total calculado con el precio nuevo
