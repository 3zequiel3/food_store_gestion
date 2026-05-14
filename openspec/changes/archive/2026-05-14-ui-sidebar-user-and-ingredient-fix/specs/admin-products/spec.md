# Delta Spec: admin-products (MODIFIED Requirements)

### Requirement: Admin puede editar un producto (MODIFIED)
The edit modal now preloads categories, ingredients, and images. The admin can modify all aspects of the product in the same unified form. On save, the system SHALL sync ingredient assignments (including `es_removible`) to the backend via individual API calls: `PUT /api/v1/productos/{id}/ingredientes/{ingId}` for updated associations, `POST` for new ones, `DELETE` for removed ones. Basic fields (nombre, precio, stock, disponible) are updated first, then ingredient sync runs sequentially.

(Previously: Ingredient sync was deferred with a TODO comment; only basic fields were sent on edit.)

##### Scenario: Editar producto carga datos completos
- **WHEN** el admin hace click en "Editar" en una fila
- **THEN** se abre el modal con nombre, precio, stock, categorías seleccionadas, ingredientes asignados e imágenes precargados

##### Scenario: Editar categorías del producto
- **WHEN** el admin modifica las categorías en el modal de edición y guarda
- **THEN** las categorías del producto se actualizan (PUT /{id}/categorias)

##### Scenario: Editar ingredientes del producto (es_removible persists)
- **WHEN** el admin modifica ingredientes (agrega, quita, o toggles `es_removible`) en el modal de edición y guarda
- **THEN** los cambios de ingredientes se sincronizan al backend y, al recargar, los ingredientes y sus flags `es_removible` reflejan los valores guardados

##### Scenario: es_removible toggle persists after reload
- **GIVEN** a product with ingredient "Tomate" where `es_removible = false`
- **WHEN** the admin toggles `es_removible` to `true` and saves
- **THEN** after page reload, "Tomate" shows `es_removible = true`

##### Scenario: Removed ingredient is dissociated
- **WHEN** the admin removes an ingredient from the product in edit mode and saves
- **THEN** the ingredient association is deleted via `DELETE /api/v1/productos/{id}/ingredientes/{ingId}` and is absent after reload

##### Scenario: Editar imágenes del producto
- **WHEN** el admin agrega, reordena o elimina imágenes en el modal de edición y guarda
- **THEN** las imágenes del producto se actualizan
