## Context

El feature de productos ya existe en `features/products/` para el flujo cliente (listado público, detalle). Los tipos `ProductoRead` y `ProductoDetail` están definidos. Los endpoints admin (`POST /`, `PUT /{id}`, `DELETE /{id}`, `PATCH /{id}/disponibilidad`, `PATCH /{id}/stock`) ya existen en el backend con roles ADMIN/STOCK.

## Goals / Non-Goals

**Goals:**
- Tabla admin con todos los productos (activos e inactivos), paginada, con filtro por nombre
- Modal de creación con campos básicos (nombre, precio, stock, descripcion, imagen_url, disponible)
- Modal de edición con los mismos campos
- Toggle rápido de disponibilidad desde la fila
- Soft-delete con confirmación
- Reusar hooks, tipos y componentes del feature existente donde sea posible

**Non-Goals:**
- Gestión de ingredientes por producto (se puede hacer en `/admin/ingredientes` cuando exista)
- Gestión de categorías por producto en este change (se puede agregar después)
- Upload de imágenes (solo URL manual)
- Importación masiva

## Decisions

**D1 — Tabla en lugar de grilla de cards**
El admin necesita densidad de información: precio, stock, estado, acciones. Una tabla permite esto. El `CatalogPage` usa cards porque es UX de compra.

**D2 — Modal de create/edit unificado (`ProductFormModal`)**
Un solo componente con prop `producto?: ProductoRead` — si viene `undefined` es alta, si viene con datos es edición. Evita duplicar el formulario.

**D3 — TanStack Form + Zod para el formulario**
Consistente con el resto del proyecto (checkout, admin-users). Schema Zod para validación: nombre (min 2), precio (positivo), stock (entero ≥ 0), imagen_url (url opcional o vacío).

**D4 — Mutations pessimistas con invalidateQueries**
Igual que el patrón ya establecido en admin-users y checkout. En `onSuccess` de cada mutation → `queryClient.invalidateQueries(['products'])`.

**D5 — Reusar `useProducts` existente**
El hook ya acepta `{ page, limit, search }`. Para el admin agregamos `disponible: undefined` (sin filtrar por disponibilidad — ver todos).

**D6 — Nuevos tipos en el feature existente**
`ProductoCreate` y `ProductoUpdate` se agregan a `features/products/types/products.types.ts`. El service admin va a `features/products/services/admin-products.service.ts` separado del service público.

## Risks / Trade-offs

- [El toggle de disponibilidad hace un PATCH optimista visual → si falla, la UI revierte] → Mitigation: usar onError para invalidar el query y revertir el estado
- [Formulario sin upload de imagen puede frustrar en demo] → Mitigación: aclarar que imagen_url es una URL de Cloudinary/externo
