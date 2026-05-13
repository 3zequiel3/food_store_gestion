## Context

El backend expone endpoints completos para categorías (`GET/POST/PUT/DELETE /categorias/`) e ingredientes (`GET/POST/PUT/DELETE /ingredientes/`). Las categorías son reflexivas: `padre_id: int | None` define el árbol. Solo las hojas (sin hijos activos) pueden asignarse a productos. Los ingredientes tienen `es_alergeno: bool` global y `es_removible: bool` que vive en el pivot `product_ingredients` (por-producto).

## Goals / Non-Goals

**Goals:**
- AdminCategoriasPage: árbol visual colapsable, crear categoría raíz o hija, editar nombre, soft-delete con feedback de error si tiene hijas/productos activos
- AdminIngredientesPage: tabla paginada, badge `es_alergeno`, crear, editar, soft-delete
- `CategoryLeafSelector`: combobox con árbol, solo hojas seleccionables, multi-select, chips de seleccionados — para reusar en ProductFormModal
- `IngredientAssignSelector`: search + select + lista con toggle `es_removible` por ítem — para reusar en ProductFormModal

**Non-Goals:**
- Reparenting de categorías (mover una categoría de padre) — no entra en scope
- Gestión de stock de ingredientes
- Drag&drop en el árbol

## Decisions

**D1 — Árbol de categorías con indentación, no drag&drop**
El árbol se renderiza con indentación visual (padding-left por nivel). Los nodos padre tienen un toggle de colapso. Las operaciones son botones inline por nodo: "+ hijo", "✏", "🗑".

**D2 — GET /categorias sin `solo_hojas` devuelve el árbol anidado**
El backend devuelve `list[CategoriaTreeNode]` con campo `subcategorias: list[...]` recursivo cuando `solo_hojas=false` (default). Usamos esto para renderizar el árbol. Para el `CategoryLeafSelector` pedimos `?solo_hojas=true` que devuelve lista plana de hojas.

**D3 — CategoryLeafSelector como combobox con búsqueda**
Input de búsqueda filtra las hojas por nombre (client-side, la lista de hojas es pequeña). Hojas seleccionadas se muestran como chips con `×`. Los padres se muestran como separadores visuales en el dropdown pero no son seleccionables.

**D4 — IngredientAssignSelector como lista incremental**
Campo de búsqueda + dropdown de ingredientes disponibles. Al seleccionar uno, se agrega a la lista de "asignados" con un toggle `es_removible`. El usuario puede remover ítems de la lista antes de guardar.

**D5 — Endpoints existentes, no crear nuevos**
Todas las mutaciones usan los endpoints ya documentados. El CRUD de categorías e ingredientes es standard. El `CategoryLeafSelector` e `IngredientAssignSelector` son componentes puros de selección que emiten el valor seleccionado hacia arriba — no hacen mutaciones.

**D6 — Manejo de errores de delete con toast descriptivo**
El backend retorna 409 con `detail` cuando no se puede borrar (hijas activas, productos activos). El hook `useDeleteCategoria` interpreta el 409 y muestra el mensaje del backend en el toast de error.

## Risks / Trade-offs

- [El árbol puede ser grande en proyectos reales] → Mitigation: colapso por defecto de sub-árboles con más de 3 hijos
- [IngredientAssignSelector necesita todos los ingredientes para el search] → Mitigation: `useIngredientes` con `limit=100` — suficiente para el scope del proyecto académico
