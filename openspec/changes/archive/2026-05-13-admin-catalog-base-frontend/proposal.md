## Why

El admin no puede gestionar categorías ni ingredientes desde la UI — ambas pantallas son PlaceholderPage. Sin categorías hoja creadas, los productos no pueden activarse (el backend auto-deshabilita productos sin categoría hoja). Sin ingredientes, no se puede armar el catálogo completo. Este change es el paso previo obligatorio al rediseño del formulario de productos (Change 2).

## What Changes

- Reemplazar PlaceholderPage en `/admin/categorias` por `AdminCategoriasPage` con árbol jerárquico, CRUD
- Reemplazar PlaceholderPage en `/admin/ingredientes` por `AdminIngredientesPage` con tabla, CRUD
- Crear `CategoryLeafSelector` — componente de selección múltiple que muestra el árbol pero solo permite seleccionar hojas (reutilizable en el formulario de productos)
- Crear `IngredientAssignSelector` — componente para asociar ingredientes a un producto con flag `es_removible` por ítem (reutilizable en el formulario de productos)

## Capabilities

### New Capabilities

- `admin-categorias`: CRUD de categorías con árbol reflexivo — crear raíz e hijos, editar nombre/padre, soft-delete con guards, `CategoryLeafSelector` compartido
- `admin-ingredientes`: CRUD de ingredientes con flags `es_alergeno`/`es_removible` — crear, editar, soft-delete, `IngredientAssignSelector` compartido

### Modified Capabilities

## Impact

- `frontend/src/features/categorias/` — nueva feature folder completa
- `frontend/src/features/ingredientes/` — nueva feature folder completa
- `frontend/src/pages/admin/AdminCategoriasPage.tsx` — nueva página
- `frontend/src/pages/admin/AdminIngredientesPage.tsx` — nueva página
- `frontend/src/router/AppRoute.tsx` — reemplazar PlaceholderPages
- No hay cambios en el backend — todos los endpoints ya existen
