## 1. Tipos y service admin

- [x] 1.1 Agregar `ProductoCreate`, `ProductoUpdate`, `StockUpdate` a `frontend/src/features/products/types/products.types.ts`
- [x] 1.2 Crear `frontend/src/features/products/services/admin-products.service.ts` con `createProduct`, `updateProduct`, `deleteProduct`, `toggleDisponibilidad`, `updateStock`

## 2. Hooks admin

- [x] 2.1 Crear `frontend/src/features/products/hooks/useCreateProduct.ts` — mutation POST `/productos/`
- [x] 2.2 Crear `frontend/src/features/products/hooks/useUpdateProduct.ts` — mutation PUT `/productos/{id}`
- [x] 2.3 Crear `frontend/src/features/products/hooks/useDeleteProduct.ts` — mutation DELETE `/productos/{id}`
- [x] 2.4 Crear `frontend/src/features/products/hooks/useToggleDisponibilidad.ts` — mutation PATCH `/productos/{id}/disponibilidad`

## 3. Componentes

- [x] 3.1 Crear `frontend/src/features/products/components/admin/ProductFormModal.tsx` — modal unificado create/edit con TanStack Form + Zod (campos: nombre, descripcion, precio, stock_cantidad, disponible, imagen_url)
- [x] 3.2 Crear `frontend/src/features/products/components/admin/ProductAdminRow.tsx` — fila de tabla con thumbnail, nombre, precio, stock, badge disponibilidad (clickeable para toggle), botones editar/eliminar
- [x] 3.3 Crear `frontend/src/features/products/components/admin/DeleteProductModal.tsx` — modal de confirmación de eliminación

## 4. Página y ruta

- [x] 4.1 Crear `frontend/src/pages/admin/AdminProductosPage.tsx` — tabla paginada, búsqueda por nombre (URL param), botón "Nuevo producto", integra ProductFormModal y DeleteProductModal
- [x] 4.2 Reemplazar `PlaceholderPage` de `/admin/productos` → `AdminProductosPage` en `AppRoute.tsx`
