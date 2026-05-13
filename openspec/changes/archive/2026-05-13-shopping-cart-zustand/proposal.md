## Why

El carrito tiene el store completo y el drawer base, pero dos funcionalidades clave del Sprint 9 no están conectadas a ninguna UI: los botones +/− de cantidad dentro del drawer (el store tiene `updateQuantity` pero nadie lo llama) y la personalización de ingredientes removibles en el detalle del producto (el tipo `CartItem` tiene `personalizacion` pero nunca se popula). Sin esto el checkout no puede reflejar pedidos personalizados.

## What Changes

- **CartDrawer**: agregar controles +/− de cantidad por ítem (llaman a `updateQuantity`). Eliminar automáticamente si cantidad llega a 0.
- **ProductDetailPage**: agregar checkboxes para ingredientes removibles. Los desmarcados se convierten en el string `personalizacion` (ej: "sin cebolla, sin ajo") que se pasa a `addItem`. También corregir que `precio` se pase como `Number(producto.precio)` (mismo fix que se hizo en ProductCard).
- **CartDrawer imagen**: mostrar la imagen del producto si `imagen_url` está disponible (actualmente hay un div vacío gris de placeholder).

## Capabilities

### New Capabilities

### Modified Capabilities
- `zustand-stores`: la UI del cart drawer ahora consume `updateQuantity` — no cambia el contrato del store, solo se expone en la vista.

## Impact

- **Archivos modificados**: `components/layout/CartDrawer.tsx`, `pages/client/ProductDetailPage.tsx`.
- **Sin nuevos archivos**: toda la infraestructura ya existe.
- **Sin cambios de backend**: 100% client-side.
