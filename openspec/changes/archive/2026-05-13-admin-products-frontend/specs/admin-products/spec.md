## ADDED Requirements

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
- **THEN** la tabla se filtra en tiempo real (debounced) por nombre de producto

### Requirement: Admin puede crear un producto
El sistema SHALL permitir crear un producto nuevo vía modal con formulario validado.

#### Scenario: Crear producto válido
- **WHEN** el admin completa nombre, precio y stock mínimo y envía el formulario
- **THEN** el producto se crea, el modal se cierra y la tabla se actualiza con el nuevo producto

#### Scenario: Validación de campos requeridos
- **WHEN** el admin intenta crear sin nombre o con precio inválido
- **THEN** el formulario muestra errores de validación inline sin enviar la request

### Requirement: Admin puede editar un producto
El sistema SHALL permitir editar los campos de un producto existente.

#### Scenario: Editar producto
- **WHEN** el admin hace click en "Editar" en una fila
- **THEN** se abre el modal de formulario con los datos actuales del producto precargados

#### Scenario: Guardar cambios
- **WHEN** el admin modifica campos y confirma
- **THEN** el producto se actualiza y la tabla refleja los cambios

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
