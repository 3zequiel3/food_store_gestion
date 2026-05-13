## ADDED Requirements

### Requirement: Admin ve el listado de ingredientes
El sistema SHALL mostrar una tabla paginada de ingredientes con badge de alérgeno en `/admin/ingredientes`.

#### Scenario: Listado carga
- **WHEN** el admin navega a `/admin/ingredientes`
- **THEN** ve una tabla con nombre y badge "Alérgeno" donde corresponda

#### Scenario: Sin ingredientes
- **WHEN** no hay ingredientes
- **THEN** se muestra empty state con botón para crear el primero

### Requirement: Admin crea un ingrediente
El sistema SHALL permitir crear un ingrediente con nombre y flag `es_alergeno`.

#### Scenario: Crear ingrediente válido
- **WHEN** el admin completa nombre y opcionalmente marca es_alergeno y confirma
- **THEN** el ingrediente se crea y aparece en la tabla

#### Scenario: Nombre duplicado
- **WHEN** el admin intenta crear un ingrediente con nombre ya existente (incluso soft-deleted)
- **THEN** el backend devuelve 409 y se muestra el error en el modal

### Requirement: Admin edita un ingrediente
El sistema SHALL permitir editar nombre y flag `es_alergeno` de un ingrediente.

#### Scenario: Editar ingrediente
- **WHEN** el admin hace click en editar
- **THEN** modal con datos precargados y puede modificar nombre y/o es_alergeno

### Requirement: Admin elimina un ingrediente
El sistema SHALL realizar soft-delete de un ingrediente.

#### Scenario: Eliminar ingrediente
- **WHEN** el admin confirma la eliminación
- **THEN** el ingrediente desaparece de la tabla (soft-delete, sigue en pivots existentes)

### Requirement: IngredientAssignSelector es usable desde otros componentes
El sistema SHALL proveer `IngredientAssignSelector` que permite buscar ingredientes, agregarlos a una lista con toggle `es_removible` por ítem, y emitir la lista hacia el componente padre.

#### Scenario: Buscar y agregar ingrediente
- **WHEN** el usuario escribe en el campo de búsqueda y selecciona un ingrediente
- **THEN** el ingrediente aparece en la lista de asignados con toggle es_removible en false por defecto

#### Scenario: Toggle es_removible
- **WHEN** el usuario activa el toggle de un ingrediente en la lista
- **THEN** ese ingrediente queda marcado como removible por el cliente final

#### Scenario: Remover ingrediente de la lista
- **WHEN** el usuario hace click en × de un ingrediente asignado
- **THEN** el ingrediente desaparece de la lista de asignados

#### Scenario: Badge de alérgeno
- **WHEN** un ingrediente en la lista tiene `es_alergeno: true`
- **THEN** se muestra un badge visual de alérgeno junto al nombre
