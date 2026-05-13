## Why

El carrito funciona pero el botón "Ir al checkout" está deshabilitado. Antes de crear un pedido, el sistema debe validar que el stock sigue disponible y que los precios no cambiaron desde que el cliente agregó los productos. Sin esta validación, el backend puede rechazar el pedido con errores difíciles de interpretar.

## What Changes

- Habilitar el botón "Ir al checkout" en `CartDrawer` — actualmente hardcodeado como disabled.
- Al hacer click, disparar validación: llama `GET /productos/{id}` en paralelo para cada ítem del carrito.
- Si hay **problemas de stock** (disponible=false o stock < cantidad pedida): modal con listado de ítems afectados, botón "Entendido" para volver al carrito y ajustar.
- Si hay **cambios de precio** (sin problemas de stock): modal informativo con precios viejos vs nuevos, botones "Actualizar precios y continuar" (sincroniza el carrito y navega a `/cliente/checkout`) y "Cancelar".
- Si todo está OK: navega directo a `/cliente/checkout` sin modal.
- Agregar acción `updateItemPrice(producto_id, precio)` al `cartStore` para sincronizar precios actualizados.

## Capabilities

### New Capabilities
- `checkout-validation`: lógica de validación pre-checkout con detección de stock y cambios de precio.

### Modified Capabilities
- `zustand-stores`: agregar `updateItemPrice` al cartStore.

## Impact

- **Archivos nuevos**: `features/checkout/` (types, hook, modal).
- **Archivos modificados**: `features/cart/stores/cartStore.ts` (nueva acción), `components/layout/CartDrawer.tsx` (habilitar botón).
- **Sin cambios de backend**: reutiliza `GET /productos/{id}` existente.
