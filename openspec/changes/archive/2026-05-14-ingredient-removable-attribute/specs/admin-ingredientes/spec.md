# Delta for admin-ingredientes

## MODIFIED Requirements

### Requirement: Admin ve el listado de ingredientes

El sistema SHALL mostrar una tabla paginada de ingredientes con badges de alérgeno y removible en `/admin/ingredientes`. (Previously: solo mostraba badge de alérgeno, no de removible)

#### Scenario: Listado carga con columna removible

- **WHEN** el admin navega a `/admin/ingredientes`
- **THEN** ve una tabla con nombre, badge "Alérgeno" y badge "Removible" donde corresponda

#### Scenario: Sin ingredientes

- **WHEN** no hay ingredientes
- **THEN** se muestra empty state con botón para crear el primero

### Requirement: Admin crea un ingrediente

El sistema SHALL permitir crear un ingrediente con nombre, flag `es_alergeno` y flag `es_removible`. (Previously: no incluía `es_removible`)

#### Scenario: Crear ingrediente con es_removible

- **WHEN** el admin completa nombre, marca es_removible y confirma
- **THEN** el ingrediente se crea con `es_removible: true` y aparece en la tabla con badge

#### Scenario: Crear ingrediente sin es_removible

- **WHEN** el admin completa nombre sin marcar es_removible
- **THEN** el ingrediente se crea con `es_removible: false`

#### Scenario: Nombre duplicado

- **WHEN** el admin intenta crear un ingrediente con nombre ya existente
- **THEN** el backend devuelve 409 y se muestra el error en el modal

### Requirement: Admin edita un ingrediente

El sistema SHALL permitir editar nombre, flag `es_alergeno` y flag `es_removible` de un ingrediente. (Previously: no incluía `es_removible`)

#### Scenario: Editar ingrediente con es_removible

- **WHEN** el admin hace click en editar
- **THEN** modal con datos precargados incluyendo checkbox de es_removible

#### Scenario: Toggle es_removible en edición

- **WHEN** el admin cambia es_removible de false a true y guarda
- **THEN** el ingrediente se actualiza y el badge se muestra en la tabla

### Requirement: Admin elimina un ingrediente

El sistema SHALL realizar soft-delete de un ingrediente.

#### Scenario: Eliminar ingrediente

- **WHEN** el admin confirma la eliminación
- **THEN** el ingrediente desaparece de la tabla (soft-delete)

### Requirement: IngredientAssignSelector es usable desde otros componentes

El sistema SHALL proveer `IngredientAssignSelector` que permite buscar ingredientes y agregarlos a una lista. El toggle `es_removible` se elimina del selector ya que ahora es atributo global del ingrediente. (Previously: incluía toggle `es_removible` por ítem)

#### Scenario: Buscar y agregar ingrediente

- **WHEN** el usuario escribe en el campo de búsqueda y selecciona un ingrediente
- **THEN** el ingrediente aparece en la lista de asignados (sin toggle es_removible)

#### Scenario: Badge de alérgeno

- **WHEN** un ingrediente en la lista tiene `es_alergeno: true`
- **THEN** se muestra un badge visual de alérgeno junto al nombre

#### Scenario: Badge de removible

- **WHEN** un ingrediente en la lista tiene `es_removible: true`
- **THEN** se muestra un badge visual de removible junto al nombre
