## Purpose

UI de checkout completa: selección de dirección y forma de pago, resumen con totales, creación del pedido contra `POST /api/v1/pedidos`, y pantalla de confirmación post-creación. Implementa US-035 y US-071.

## ADDED Requirements

### Requirement: Página de checkout con tres secciones

El sistema SHALL renderizar `CheckoutPage` en `/cliente/checkout` (reemplazando el `PlaceholderPage`) con tres secciones: `AddressSelector`, `PaymentMethodSelector` y `OrderSummary`. Cada sección maneja su propio estado local. La página SHALL mostrar un botón "Confirmar pedido" que arma el payload y envía `POST /api/v1/pedidos`. Mientras la mutation está pendiente, el botón SHALL mostrar un spinner y estar deshabilitado. (US-035)

#### Scenario: Checkout completo con dirección y pago
- **WHEN** un cliente autenticado con carrito validado navega a `/cliente/checkout`
- **THEN** ve tres secciones: dirección de entrega, forma de pago y resumen del pedido
- **AND** el botón "Confirmar pedido" está deshabilitado hasta seleccionar al menos una forma de pago

#### Scenario: Botón deshabilitado durante creación
- **WHEN** el cliente hace click en "Confirmar pedido" y la mutation está en curso
- **THEN** el botón muestra un spinner y está deshabilitado
- **AND** no se puede hacer click de nuevo hasta que termine

---

### Requirement: Selección de dirección con "Retiro en local"

El sistema SHALL mostrar un radio group con las direcciones del usuario (obtenidas via `useAddresses()`) y una opción "Retiro en local (sin envío)" como primera opción. Si el usuario selecciona retiro en local, `direccion_id` SHALL ser `null` y el costo de envío SHALL ser `$0`. Si selecciona una dirección, `direccion_id` SHALL ser el ID correspondiente y el costo de envío estimado SHALL ser `$50` (constante v1). Si el usuario no tiene direcciones, solo se muestra la opción de retiro en local. (US-035, RN-PE03)

#### Scenario: Selección de retiro en local
- **WHEN** el usuario selecciona "Retiro en local"
- **THEN** `direccion_id` es `null` en el payload y el resumen muestra "Envío: $0"

#### Scenario: Selección de dirección de entrega
- **WHEN** el usuario selecciona una dirección existente
- **THEN** `direccion_id` es el ID de esa dirección y el resumen muestra "Envío: $50"

#### Scenario: Sin direcciones guardadas
- **WHEN** el usuario no tiene direcciones (useAddresses devuelve [])
- **THEN** solo se muestra la opción "Retiro en local" y no se puede elegir entrega a domicilio

---

### Requirement: Selección de forma de pago

El sistema SHALL mostrar un radio group con las formas de pago habilitadas obtenidas via `GET /api/v1/formas-pago`. El usuario SHALL seleccionar exactamente una forma de pago antes de poder confirmar. El `forma_pago_codigo` seleccionado se incluye en el payload de creación del pedido. (US-035)

#### Scenario: Listar formas de pago disponibles
- **WHEN** la página de checkout se monta
- **THEN** se solicitan las formas de pago y se muestran como radio buttons con `descripcion` como label y `codigo` como valor

#### Scenario: Selección requerida
- **WHEN** el usuario no ha seleccionado una forma de pago
- **THEN** el botón "Confirmar pedido" está deshabilitado

---

### Requirement: Resumen del pedido con totales

El sistema SHALL mostrar `OrderSummary` con: tabla de items (nombre, cantidad, precio unitario, subtotal por línea), costo de envío, y total estimado. Los datos de los items vienen del `cartStore` (precios ya validados por `checkout-validation`). El subtotal se calcula como `sum(item.precio × item.cantidad)`. El total estimado es `subtotal + envío`. El campo de notas opcionales (`notas`, máximo 500 caracteres) se incluye como textarea. (US-035, US-037, US-038, RN-PE08)

#### Scenario: Resumen con dirección de entrega
- **WHEN** se selecciona una dirección
- **THEN** el resumen muestra los items, "Envío: $50", y el total = subtotal + 50

#### Scenario: Resumen con retiro en local
- **WHEN** se selecciona retiro en local
- **THEN** el resumen muestra los items, "Envío: $0", y el total = subtotal

#### Scenario: Notas opcionales
- **WHEN** el usuario escribe notas en el textarea (hasta 500 caracteres)
- **THEN** el campo `notas` se incluye en el payload; si está vacío, se envía como `null`

---

### Requirement: Creación del pedido (useCreateOrder)

El sistema SHALL exponer `useCreateOrder` como `useMutation` que envía `POST /api/v1/pedidos` con el payload armado por `buildOrderPayload()`. El mapeo de `CartItem[]` a `CrearPedidoRequest` SHALL:
- `items`: mapear cada `CartItem` a `{ producto_id, cantidad, personalizacion: item.personalizacionIds ?? null }`
- `forma_pago_codigo`: el código seleccionado
- `direccion_id`: el ID seleccionado o `null` para retiro en local
- `notas`: el valor del textarea o `null`

El Zod schema `checkoutSchema` SHALL validar el payload ANTES de enviar. (US-035, US-036, RN-PE01, RN-PE02, RN-PE07)

#### Scenario: Mapeo correcto de personalizacionIds
- **WHEN** un CartItem tiene `personalizacionIds: [3, 7]`
- **THEN** el item en el payload tiene `personalizacion: [3, 7]`

#### Scenario: personalizacionIds ausente se mapea a null
- **WHEN** un CartItem no tiene `personalizacionIds`
- **THEN** el item en el payload tiene `personalizacion: null`

#### Scenario: Validación Zod antes del envío
- **WHEN** el usuario confirma el pedido
- **THEN** el payload se valida contra `checkoutSchema` antes de llamar a la API
- **AND** si la validación falla, se muestran errores inline sin hacer la llamada

---

### Requirement: Pantalla de confirmación post-creación (OrderConfirmationPage)

Tras `201 Created`, el sistema SHALL redirigir a `/cliente/pedidos/:id/confirmacion` con `PedidoRead` como location state. La página SHALL mostrar: número de pedido (id), estado "PENDIENTE — Esperando pago", resumen de items (desde cartStore antes de clearCart), total (desde `PedidoRead.total`), dirección (si aplica), y botones "Ir a pagar" (#27) y "Ver mis pedidos" (#28). Tras la redirección exitosa, el carrito SHALL ser limpiado via `cartStore.clearCart()`. (US-071)

#### Scenario: Confirmación con items y dirección
- **WHEN** el pedido se crea exitosamente con dirección
- **THEN** se navega a `/cliente/pedidos/:id/confirmacion` mostrando el ID, items, total, dirección y estado PENDIENTE
- **AND** el carrito queda vacío

#### Scenario: Confirmación con retiro en local
- **WHEN** el pedido se crea exitosamente sin dirección
- **THEN** la confirmación muestra "Retiro en local" en lugar de la dirección

#### Scenario: Fallback sin location state (refresh)
- **WHEN** el usuario llega a `/cliente/pedidos/:id/confirmacion` sin location state (ej. refresh)
- **THEN** se muestra un fallback genérico "Pedido creado" con botón "Ver mis pedidos"

#### Scenario: Botón "Ir a pagar"
- **WHEN** el usuario hace click en "Ir a pagar"
- **THEN** navega a la pantalla de pago (#27, placeholder por ahora)

---

### Requirement: Manejo de errores del backend

El sistema SHALL mapear errores del backend a toasts informativos:
- `422` con stock insuficiente → toast "Producto sin stock suficiente. Volvé al carrito para ajustar." + botón para volver al catálogo.
- `422` con forma de pago inválida → toast "Forma de pago no disponible. Seleccioná otra." + re-selección automática.
- `404` dirección no encontrada → toast "Dirección no encontrada. Seleccioná otra." + limpiar selección de dirección.
- `401`/`403` → manejo por interceptor existente (refresh o redirect).
- Error genérico → toast "Error al crear el pedido. Intentá de nuevo."

#### Scenario: Stock insuficiente detectado por backend
- **WHEN** el backend responde 422 con detalle de stock insuficiente
- **THEN** se muestra toast con el mensaje y se habilita un botón para volver al carrito

#### Scenario: Dirección eliminada mientras se checkout
- **WHEN** el backend responde 404 para direccion_id
- **THEN** se muestra toast "Dirección no encontrada" y se deselecciona la dirección

---

### Requirement: Agregar `personalizacionIds` a CartItem en cartStore

El sistema SHALL agregar el campo opcional `personalizacionIds?: number[]` al tipo `CartItem` del cartStore. Este campo almacena los IDs de ingredientes excluidos (mapeo directo al backend `personalizacion: list[int]`). Si `personalizacionIds` es `undefined`, se mapea a `null` en el payload. El campo `personalizacion` (string) se mantiene para display. (D3)

#### Scenario: Item con personalizacionIds en el carrito
- **WHEN** se agrega un producto al carrito con `personalizacionIds: [3, 7]`
- **THEN** el item tiene `personalizacion: "Sin cebolla"` y `personalizacionIds: [3, 7]`
- **AND** al crear el pedido, el payload tiene `personalizacion: [3, 7]`

#### Scenario: Item sin personalizacionIds
- **WHEN** se agrega un producto sin exclusión de ingredientes
- **THEN** el item tiene `personalizacionIds: undefined`
- **AND** al crear el pedido, el payload tiene `personalizacion: null`