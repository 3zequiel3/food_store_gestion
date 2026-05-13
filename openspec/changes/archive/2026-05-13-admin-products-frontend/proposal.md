## Why

El área admin muestra un PlaceholderPage en `/admin/productos`. El personal administrativo no puede gestionar el catálogo desde la UI — tiene que hacerlo directamente por API o BD. Para poder hacer un demo E2E funcional (y para uso real), necesitamos la pantalla de listado y alta de productos.

## What Changes

- Reemplazar `PlaceholderPage` en `/admin/productos` por `AdminProductosPage` con tabla de productos
- Reemplazar `PlaceholderPage` en `/admin/productos/nuevo` con navegación al modal de creación (la ruta queda pero el flujo usa modal)
- Agregar mutations: `useCreateProduct`, `useUpdateProduct`, `useDeleteProduct`, `useToggleDisponibilidad`, `useUpdateStock`
- Agregar service methods para las operaciones admin (`createProduct`, `updateProduct`, `deleteProduct`, `toggleDisponibilidad`, `updateStock`)
- Agregar tipos admin: `ProductoCreate`, `ProductoUpdate`, `StockUpdate`
- `AdminProductosPage`: tabla con imagen, nombre, precio, stock, estado, acciones
- Modal de creación/edición con TanStack Form + Zod
- Acciones rápidas por fila: toggle disponible, editar, eliminar

## Capabilities

### New Capabilities

- `admin-products`: Gestión admin de productos — listado tabular, creación, edición, toggle de disponibilidad, eliminación (soft-delete)

### Modified Capabilities

- `products`: Se agregan los tipos `ProductoCreate` y `ProductoUpdate` al feature de productos existente

## Impact

- `frontend/src/features/products/` — nuevos types, services, hooks
- `frontend/src/pages/admin/AdminProductosPage.tsx` — nueva página
- `frontend/src/router/AppRoute.tsx` — reemplazar PlaceholderPage en `/admin/productos`
- No hay cambios en el backend — todos los endpoints ya existen
