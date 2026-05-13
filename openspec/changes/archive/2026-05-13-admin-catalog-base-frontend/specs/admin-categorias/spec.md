## ADDED Requirements

### Requirement: Admin ve el árbol de categorías
El sistema SHALL mostrar todas las categorías en estructura de árbol jerárquico con indentación por nivel en `/admin/categorias`.

#### Scenario: Árbol carga
- **WHEN** el admin navega a `/admin/categorias`
- **THEN** ve las categorías raíz con sus sub-categorías indentadas y colapsables

#### Scenario: Sin categorías
- **WHEN** no hay categorías creadas
- **THEN** se muestra empty state con botón para crear la primera

### Requirement: Admin crea una categoría
El sistema SHALL permitir crear categorías raíz (sin padre) o categorías hijo (con padre elegido).

#### Scenario: Crear categoría raíz
- **WHEN** el admin hace click en "Nueva categoría" y no selecciona padre
- **THEN** se crea con `padre_id: null` y aparece como nodo raíz en el árbol

#### Scenario: Crear categoría hija
- **WHEN** el admin hace click en "+ hijo" en un nodo del árbol
- **THEN** se abre modal con el padre pre-seleccionado

#### Scenario: Nombre duplicado en el mismo nivel
- **WHEN** el admin intenta crear una categoría con nombre que ya existe bajo el mismo padre
- **THEN** el backend devuelve 409 y se muestra el error en el modal

### Requirement: Admin edita una categoría
El sistema SHALL permitir editar el nombre de una categoría existente.

#### Scenario: Editar nombre
- **WHEN** el admin hace click en el ícono de editar de un nodo
- **THEN** se abre modal con el nombre pre-cargado y puede modificarlo

### Requirement: Admin elimina una categoría
El sistema SHALL realizar soft-delete de una categoría, con error descriptivo si tiene restricciones.

#### Scenario: Eliminar categoría hoja sin productos
- **WHEN** el admin elimina una categoría hoja sin productos activos
- **THEN** la categoría desaparece del árbol

#### Scenario: Eliminar categoría con hijas activas
- **WHEN** el admin intenta eliminar una categoría que tiene hijas activas
- **THEN** se muestra toast de error con el mensaje del backend (409)

### Requirement: CategoryLeafSelector es usable desde otros componentes
El sistema SHALL proveer un componente `CategoryLeafSelector` que muestre las hojas seleccionables y emita la lista de IDs seleccionados.

#### Scenario: Solo hojas son seleccionables
- **WHEN** el componente muestra el dropdown
- **THEN** los nodos padre aparecen como separadores no-clickeables y solo las hojas tienen acción de selección

#### Scenario: Chips de selección
- **WHEN** el usuario selecciona una hoja
- **THEN** aparece un chip con el nombre de la categoría y botón para removerla
