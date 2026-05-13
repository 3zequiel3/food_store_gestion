## 1. Feature folder — categorías (tipos, service, hooks)

- [x] 1.1 Crear `frontend/src/features/categorias/types/categorias.types.ts` con `CategoriaRead`, `CategoriaTreeNode`, `CategoriaCreate`, `CategoriaUpdate`
- [x] 1.2 Crear `frontend/src/features/categorias/services/categorias.service.ts` con `getCategorias` (árbol), `getCategoriasHojas` (flat `?solo_hojas=true`), `createCategoria`, `updateCategoria`, `deleteCategoria`
- [x] 1.3 Crear `frontend/src/features/categorias/hooks/useCategorias.ts` — query árbol completo
- [x] 1.4 Crear `frontend/src/features/categorias/hooks/useCategoriasHojas.ts` — query lista plana de hojas
- [x] 1.5 Crear `frontend/src/features/categorias/hooks/useCreateCategoria.ts` — mutation POST, invalida `['categorias']`
- [x] 1.6 Crear `frontend/src/features/categorias/hooks/useUpdateCategoria.ts` — mutation PUT, invalida `['categorias']`
- [x] 1.7 Crear `frontend/src/features/categorias/hooks/useDeleteCategoria.ts` — mutation DELETE, interpreta 409 con toast descriptivo

## 2. Feature folder — ingredientes (tipos, service, hooks)

- [x] 2.1 Crear `frontend/src/features/ingredientes/types/ingredientes.types.ts` con `IngredienteRead`, `IngredienteCreate`, `IngredienteUpdate`, `IngredienteAsignado` (id, nombre, es_alergeno, es_removible)
- [x] 2.2 Crear `frontend/src/features/ingredientes/services/ingredientes.service.ts` con `getIngredientes`, `createIngrediente`, `updateIngrediente`, `deleteIngrediente`
- [x] 2.3 Crear `frontend/src/features/ingredientes/hooks/useIngredientes.ts` — query paginada
- [x] 2.4 Crear `frontend/src/features/ingredientes/hooks/useTodosIngredientes.ts` — query con `limit=200` sin paginación para uso en selectores
- [x] 2.5 Crear `frontend/src/features/ingredientes/hooks/useCreateIngrediente.ts` — mutation POST, invalida `['ingredientes']`
- [x] 2.6 Crear `frontend/src/features/ingredientes/hooks/useUpdateIngrediente.ts` — mutation PUT, invalida `['ingredientes']`
- [x] 2.7 Crear `frontend/src/features/ingredientes/hooks/useDeleteIngrediente.ts` — mutation DELETE, invalida `['ingredientes']`

## 3. Componentes compartidos (reutilizables en ProductFormModal)

- [x] 3.1 Crear `frontend/src/features/categorias/components/CategoryLeafSelector.tsx` — combobox con árbol visual, solo hojas seleccionables, multi-select, chips, búsqueda client-side; props: `value: number[]`, `onChange: (ids: number[]) => void`
- [x] 3.2 Crear `frontend/src/features/ingredientes/components/IngredientAssignSelector.tsx` — search + dropdown + lista de asignados con toggle `es_removible` y badge alérgeno; props: `value: IngredienteAsignado[]`, `onChange: (items: IngredienteAsignado[]) => void`

## 4. Componentes admin — categorías

- [x] 4.1 Crear `frontend/src/features/categorias/components/CategoriaTreeNode.tsx` — nodo del árbol con indentación por nivel, botones "+ hijo", "✏", "🗑", toggle colapso
- [x] 4.2 Crear `frontend/src/features/categorias/components/CategoriaFormModal.tsx` — modal create/edit con campo nombre y selector de padre (opcional); maneja 409 en submit
- [x] 4.3 Crear `frontend/src/features/categorias/components/DeleteCategoriaModal.tsx` — confirmación de eliminación

## 5. Componentes admin — ingredientes

- [x] 5.1 Crear `frontend/src/features/ingredientes/components/IngredienteRow.tsx` — fila de tabla con nombre, badge alérgeno, botones editar/eliminar
- [x] 5.2 Crear `frontend/src/features/ingredientes/components/IngredienteFormModal.tsx` — modal create/edit con nombre y checkbox `es_alergeno`; maneja 409 en submit
- [x] 5.3 Crear `frontend/src/features/ingredientes/components/DeleteIngredienteModal.tsx` — confirmación de eliminación

## 6. Páginas y rutas

- [x] 6.1 Crear `frontend/src/pages/admin/AdminCategoriasPage.tsx` — árbol completo con árbol de nodos, botón "Nueva categoría raíz", integra modales
- [x] 6.2 Crear `frontend/src/pages/admin/AdminIngredientesPage.tsx` — tabla paginada con búsqueda, botón "Nuevo ingrediente", integra modales
- [x] 6.3 Reemplazar PlaceholderPages de `/admin/categorias` y `/admin/ingredientes` en `AppRoute.tsx`
