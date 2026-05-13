## Context

`cartStore` ya tiene `updateQuantity(producto_id, cantidad)` que elimina el ítem si `cantidad <= 0`. `CartDrawer` muestra `cantidad × precio` pero sin controles. `ProductDetailPage` lista ingredientes con el campo `es_removible` disponible pero sin checkboxes. `CartItem.personalizacion` es un string libre — se genera juntando los nombres de los ingredientes desmarcados.

## Goals / Non-Goals

**Goals:**
- Botones +/− en cada fila del CartDrawer con eliminación automática en 0.
- Checkboxes de ingredientes removibles en ProductDetailPage que generan el string de personalización.
- Imagen del producto en el CartDrawer si está disponible.
- Coerción `Number(producto.precio)` en ProductDetailPage (fix consistency).

**Non-Goals:**
- Reescribir el store (ya es correcto).
- Cuantificar ingredientes (solo inclusión/exclusión binaria).
- Persistencia separada de personalizaciones (va dentro del `CartItem.personalizacion` como string).

## Decisions

### D1 — Personalización como string libre, no array
El store persiste `personalizacion` como `string?`. Construirlo como array y convertirlo en el momento del `addItem` mantiene el contrato del store sin cambios: `ingredientesExcluidos.map(i => 'sin ' + i.nombre).join(', ')`.

### D2 — Checkboxes inicializados como todos marcados
Al entrar al detalle todos los ingredientes removibles aparecen seleccionados (el cliente quiere el producto completo por defecto; desmarca lo que no quiere). Estado local: `Set<number>` de IDs excluidos, inicialmente vacío.

### D3 — +/− en CartDrawer con eliminación en 0
El botón "−" llama `updateQuantity(id, cantidad - 1)`. Si `cantidad === 1`, el click lo lleva a 0 y el store elimina el ítem automáticamente — no hace falta confirm adicional (ya existe el botón de papelera para eliminaciones explícitas).
