## Requirements

### Requirement: Admin puede ver el listado de productos
El sistema SHALL mostrar una tabla paginada con todos los productos (activos e inactivos) en `/admin/productos`. Cada fila debe mostrar: imagen thumbnail, nombre, precio, stock, estado de disponibilidad y acciones.

#### Scenario: Listado carga con productos
- **WHEN** el admin navega a `/admin/productos`
- **THEN** ve una tabla con filas de productos, con imagen, nombre, precio, stock y badge de disponibilidad

#### Scenario: Listado vacío
- **WHEN** no hay productos en el sistema
- **THEN** se muestra un empty state con mensaje y botón para crear el primer producto

#### Scenario: Filtro por nombre
- **WHEN** el admin escribe en el campo de búsqueda
- **THEN** la tabla se filtra por nombre de producto

### Requirement: Admin puede crear un producto (MODIFIED)
The product creation modal now includes category selection, ingredient assignment, and image management in a 2-column layout: left column for data fields + selectors, right column for image management. `categoria_ids` is REQUIRED — the form SHALL NOT allow submission without at least one leaf category selected. The same modal is used for both create and edit operations (unified form).

> **CHANGE (product-creation-complete)**: Modal expanded from basic fields (nombre, precio, stock) to full 2-column layout with CategoryLeafSelector, IngredientAssignSelector, and image management section. Form unified for create+edit.

#### Scenario: Crear producto válido con categorías
- **WHEN** el admin completa nombre, precio, stock, selecciona al menos una categoría y envía el formulario
- **THEN** el producto se crea con las categorías asignadas, el modal se cierra y la tabla se actualiza

#### Scenario: Validación de categorías requeridas
- **WHEN** el admin intenta crear sin seleccionar ninguna categoría
- **THEN** el formulario muestra un error "El producto debe tener al menos una categoría" y no envía la request

#### Scenario: Crear producto con ingredientes
- **WHEN** el admin asigna ingredientes al producto en el formulario y envía
- **THEN** el producto se crea con los ingredientes asociados

#### Scenario: Crear producto con imagen
- **WHEN** el admin sube una imagen (por archivo o URL) y envía el formulario
- **THEN** el producto se crea con la imagen asociada

### Requirement: Admin puede editar un producto (MODIFIED)
The edit modal now preloads categories, ingredients, and images. The admin can modify all aspects of the product in the same unified form. On save, the system SHALL sync ingredient assignments (including `es_removible`) to the backend via individual API calls: `PUT /api/v1/productos/{id}/ingredientes/{ingId}` for updated associations, `POST` for new ones, `DELETE` for removed ones. Basic fields (nombre, precio, stock, disponible) are updated first, then ingredient sync runs sequentially.

> **CHANGE (ui-sidebar-user-and-ingredient-fix)**: Ingredient sync implemented — `es_removible` toggles, add/remove ingredients now persist via individual PUT/POST/DELETE API calls instead of a TODO comment. Backend 409 ConflictError avoided by DELETE→POST sequence.

#### Scenario: Editar producto carga datos completos
- **WHEN** el admin hace click en "Editar" en una fila
- **THEN** se abre el modal con nombre, precio, stock, categorías seleccionadas, ingredientes asignados e imágenes precargados

#### Scenario: Editar categorías del producto
- **WHEN** el admin modifica las categorías en el modal de edición y guarda
- **THEN** las categorías del producto se actualizan (PUT /{id}/categorias)

#### Scenario: Editar ingredientes del producto (es_removible persists)
- **WHEN** el admin modifica ingredientes (agrega, quita, o toggles `es_removible`) en el modal de edición y guarda
- **THEN** los cambios de ingredientes se sincronizan al backend y, al recargar, los ingredientes y sus flags `es_removible` reflejan los valores guardados

#### Scenario: es_removible toggle persists after reload
- **GIVEN** a product with ingredient "Tomate" where `es_removible = false`
- **WHEN** the admin toggles `es_removible` to `true` and saves
- **THEN** after page reload, "Tomate" shows `es_removible = true`

#### Scenario: Removed ingredient is dissociated
- **WHEN** the admin removes an ingredient from the product in edit mode and saves
- **THEN** the ingredient association is deleted via `DELETE /api/v1/productos/{id}/ingredientes/{ingId}` and is absent after reload

#### Scenario: Editar imágenes del producto
- **WHEN** el admin agrega, reordena o elimina imágenes en el modal de edición y guarda
- **THEN** las imágenes del producto se actualizan

### Requirement: Admin puede togglear disponibilidad
El sistema SHALL permitir activar/desactivar la disponibilidad de un producto con un solo click desde la tabla.

#### Scenario: Toggle disponibilidad
- **WHEN** el admin hace click en el badge de disponibilidad de una fila
- **THEN** el estado del producto cambia (PATCH /{id}/disponibilidad) y el badge se actualiza

### Requirement: Admin puede eliminar un producto
El sistema SHALL permitir eliminar (soft-delete) un producto con confirmación.

#### Scenario: Eliminar con confirmación
- **WHEN** el admin hace click en "Eliminar" y confirma en el diálogo
- **THEN** el producto se elimina del sistema y desaparece de la tabla

---

> **ADDED in product-creation-complete** — The following requirements were added to support image management and complete product form.

### Requirement: CategoryLeafSelector integrado en ProductFormModal
El sistema SHALL integrar el componente `CategoryLeafSelector` existente en el formulario de producto. El selector SHALL: mostrar el árbol de categorías jerárquico con búsqueda, permitir seleccionar solo categorías hoja (no padres), mostrar las categorías seleccionadas como chips removibles, y validar que al menos una categoría esté seleccionada antes de permitir el envío.

#### Scenario: Selector muestra categorías hoja
- **WHEN** el admin abre el selector de categorías
- **THEN** ve el árbol jerárquico y solo puede seleccionar categorías sin hijas

#### Scenario: Categoría padre no seleccionable
- **WHEN** el admin intenta seleccionar una categoría que tiene hijas activas
- **THEN** la categoría no aparece como seleccionable (solo las hojas son clickeables)

### Requirement: IngredientAssignSelector integrado en ProductFormModal
El sistema SHALL integrar el componente `IngredientAssignSelector` existente en el formulario de producto. El selector SHALL: permitir buscar y agregar ingredientes por nombre, mostrar badge de alérgeno para ingredientes con `es_alergeno = true`, permitir togglear `es_removible` para cada ingrediente asignado, y mostrar ingredientes asignados en lista con opción de eliminar.

#### Scenario: Agregar ingrediente con badge de alérgeno
- **WHEN** el admin busca y agrega un ingrediente con `es_alergeno = true`
- **THEN** el ingrediente aparece en la lista con badge "Alérgeno"

#### Scenario: Toggle removible
- **WHEN** el admin hace click en "Removible" / "Fijo" para un ingrediente
- **THEN** el estado de `es_removible` se alterna visualmente

### Requirement: Image section en ProductFormModal
El sistema SHALL incluir una sección de gestión de imágenes en el formulario de producto con: toggle entre modo "subir archivo" (drag & drop) y modo "ingresar URL", lista de thumbnails con indicador de imagen primaria (★), capacidad de reordenar imágenes (drag), capacidad de eliminar imágenes (×), y capacidad de establecer imagen primaria (click en ★).

#### Scenario: Subir imagen por archivo
- **WHEN** el admin arrastra un archivo de imagen al área de upload
- **THEN** la imagen se sube y aparece como thumbnail

#### Scenario: Agregar imagen por URL
- **WHEN** el admin cambia a modo URL, ingresa una URL válida y confirma
- **THEN** la imagen se agrega y aparece como thumbnail

#### Scenario: Establecer imagen primaria
- **WHEN** el admin hace click en el ícono ★ de un thumbnail no-primario
- **THEN** esa imagen se marca como primaria y la anterior deja de serlo

#### Scenario: Eliminar imagen
- **WHEN** el admin hace click en × de un thumbnail
- **THEN** la imagen se elimina de la lista

### Requirement: ProductDetailPage con carousel de imágenes
El sistema SHALL mostrar un carousel de imágenes en la página de detalle de producto: imagen principal muestra la imagen primaria (o la primera si no hay primaria), strip de thumbnails debajo de la imagen principal, click en thumbnail cambia la imagen principal. Si hay una sola imagen, no se muestra carousel (comportamiento actual).

#### Scenario: Carousel con múltiples imágenes
- **WHEN** el producto tiene 3 imágenes
- **THEN** se muestra la imagen principal con strip de 3 thumbnails debajo

#### Scenario: Click en thumbnail cambia imagen principal
- **WHEN** el admin hace click en el segundo thumbnail
- **THEN** la imagen principal muestra la segunda imagen

#### Scenario: Producto con una sola imagen
- **WHEN** el producto tiene solo 1 imagen
- **THEN** se muestra la imagen sin carousel ni thumbnails (comportamiento actual preservado)

### Requirement: Tipo CategoriaRead corregido
El tipo `CategoriaRead` en `products.types.ts` SHALL usar `padre_id` (no `parent_id`) y NO SHALL incluir `slug`. Esto alinea el tipo frontend con el schema backend `CategoriaRead` que envía `padre_id: int | null` sin `slug`.

#### Scenario: Tipo coincide con backend
- **WHEN** el frontend recibe una categoría del backend
- **THEN** el tipo `CategoriaRead` tiene `padre_id` y no tiene `slug`

### Requirement: ImagenRead y ProductoRead types en frontend
El frontend SHALL definir `ImagenRead { id: number; url: string; orden: number; es_primaria: boolean }` y `ProductoRead` SHALL incluir `imagenes: ImagenRead[]`. El campo `imagen_url` se mantiene como opcional para backward compat.

#### Scenario: ProductoRead tiene imagenes
- **WHEN** el frontend recibe un producto del backend
- **THEN** el objeto tiene `imagenes: ImagenRead[]`

### Requirement: Admin image service functions
El frontend SHALL proveer funciones de servicio para: `uploadProductImage(id, file)`, `addProductImageUrl(id, url)`, `deleteProductImage(id, imagenId)`, `setProductImagePrimary(id, imagenId)`, `setProductImageOrder(id, imagenId, orden)`.

#### Scenario: Upload image calls correct endpoint
- **WHEN** `uploadProductImage(5, file)` is called
- **THEN** it POSTs to `/api/v1/productos/5/imagenes` with multipart form data
