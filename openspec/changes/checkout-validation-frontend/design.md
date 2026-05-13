## Context

`getProduct(id)` ya existe en `features/products/services/products.service.ts` y devuelve `ProductoDetail` con `disponible`, `stock_cantidad` y `precio`. El `cartStore` tiene `items: CartItem[]` con `precio` y `cantidad`. La validación es 100% client-side — compara los datos del carrito contra el backend en el momento del click.

## Goals / Non-Goals

**Goals:**
- Validación paralela de todos los ítems en un solo batch de requests.
- Dos tipos de resultado: stock issues (bloqueantes) y price changes (informativas).
- Sincronización de precios en cartStore antes de navegar al checkout.
- Navegación a `/cliente/checkout` (la ruta y página se crean en #26).

**Non-Goals:**
- Validación en tiempo real mientras el usuario navega (polling).
- Reserva de stock (pertenece al backend al crear el pedido).
- Descuentos o cupones.

## Decisions

### D1 — Promise.all para validación paralela
Todos los `getProduct(id)` se lanzan en paralelo con `Promise.all`. Con carritos típicos de 3-8 ítems el overhead es mínimo y la UX es inmediata.

### D2 — Dos niveles de severidad
- **Stock issues** (bloqueantes): `!disponible || stock_cantidad < cantidad`. El usuario DEBE ajustar el carrito — el modal no tiene opción de continuar.
- **Price changes** (informativas): `|precio_backend - precio_carrito| > 0.01`. El usuario PUEDE continuar actualizando precios o cancelar.
- Si hay ambos tipos: se muestran los stock issues primero y no se ofrece continuar hasta resolverlos.

### D3 — `updateItemPrice` en cartStore
Acción mínima: `updateItemPrice(producto_id, precio)` — hace `set` mapeando el ítem correspondiente. Se usa solo desde `CartValidationModal` cuando el usuario acepta los nuevos precios antes de navegar.

### D4 — `useValidateCart` como useMutation
La validación es una operación disparada por evento (click), no un query continuo. `useMutation` con `mutationFn: validateCartItems` devuelve el resultado tipado. `isPending` muestra spinner en el botón del drawer mientras se validan los requests.

### D5 — Ruta `/cliente/checkout` pendiente
El botón navega a `/cliente/checkout` que en este sprint es una ruta que aún no existe (se crea en #26). Para evitar 404, se agrega un `PlaceholderPage` temporal en `AppRoute.tsx` que #26 reemplazará.
