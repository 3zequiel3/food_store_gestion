## ADDED Requirements

### Requirement: Controles de cantidad en CartDrawer
El sistema SHALL mostrar botones "−" y "+" junto a cada ítem en el CartDrawer. El botón "−" SHALL llamar `updateQuantity(producto_id, cantidad - 1)`. Si `cantidad === 1` y se presiona "−", el ítem SHALL ser eliminado automáticamente (el store ya aplica esto). El botón "+" SHALL llamar `updateQuantity(producto_id, cantidad + 1)`. La cantidad SHALL mostrarse entre los dos botones. El botón de papelera existente SHALL mantenerse para eliminación explícita.

#### Scenario: Incrementar cantidad
- **WHEN** el usuario presiona "+" en un ítem con cantidad 2
- **THEN** el ítem muestra cantidad 3 y el total del carrito se actualiza

#### Scenario: Decrementar a 0 elimina el ítem
- **WHEN** el usuario presiona "−" en un ítem con cantidad 1
- **THEN** el ítem desaparece del drawer y el contador del navbar se decrementa

#### Scenario: Decrementar sin llegar a 0
- **WHEN** el usuario presiona "−" en un ítem con cantidad 3
- **THEN** el ítem muestra cantidad 2 sin eliminarse

### Requirement: Imagen del producto en CartDrawer
El sistema SHALL mostrar la imagen del producto en el ítem del CartDrawer si `imagen_url` está disponible. Si no hay imagen, SHALL mantener el placeholder gris actual.

#### Scenario: Item con imagen muestra la foto
- **WHEN** un ítem en el carrito tiene imagen_url
- **THEN** la imagen se muestra en el espacio del placeholder (12×12 redondeado)

#### Scenario: Item sin imagen mantiene placeholder
- **WHEN** un ítem en el carrito no tiene imagen_url
- **THEN** se muestra el div gris de placeholder sin error

### Requirement: Personalización de ingredientes removibles en ProductDetailPage
El sistema SHALL mostrar checkboxes para los ingredientes marcados como `es_removible === true` en la página de detalle del producto. Todos los checkboxes SHALL iniciar marcados (el cliente tiene el producto completo por defecto). Al desmarcar un ingrediente, éste se agrega a la lista de excluidos. Al presionar "Agregar al carrito", el campo `personalizacion` de `CartItem` SHALL ser el string resultante de unir los excluidos con el prefijo "sin": `"sin cebolla, sin ajo"`. Si no hay exclusiones, `personalizacion` SHALL ser `undefined`.

#### Scenario: Sin exclusiones, personalizacion es undefined
- **WHEN** el usuario agrega un producto sin desmarcar ningún ingrediente
- **THEN** el CartItem.personalizacion es undefined y el drawer no muestra nota de personalización

#### Scenario: Con exclusiones, personalizacion es string
- **WHEN** el usuario desmarca "cebolla" y "ajo" antes de agregar
- **THEN** el CartItem.personalizacion es "sin cebolla, sin ajo"

#### Scenario: Solo ingredientes removibles tienen checkbox
- **WHEN** un producto tiene ingredientes con es_removible=false (alérgenos fijos)
- **THEN** esos ingredientes se muestran en la lista pero sin checkbox (solo lectura)
