## ADDED Requirements

### Requirement: Crear pedido desde el carrito (atomicidad)

El sistema SHALL exponer `POST /api/v1/pedidos` que crea un pedido a partir del carrito del cliente. La operación SHALL ser atómica: la inserción del `Pedido`, todos sus `DetallePedido` y el `HistorialEstadoPedido` inicial ocurren dentro de una única transacción (Unit of Work). Si cualquier paso falla, ningún registro persiste.

#### Scenario: Cliente autenticado crea pedido válido con dirección y items
- **WHEN** un cliente autenticado (rol CLIENT) envía `POST /api/v1/pedidos` con un body válido (`items` con ≥1 elemento, `forma_pago_codigo` existente y habilitada, `direccion_id` propia, productos disponibles con stock suficiente)
- **THEN** el sistema responde `201 Created` con `PedidoRead` (`id`, `estado_codigo="PENDIENTE"`, `total`, `created_at`)
- **AND** en BD existe exactamente 1 fila en `orders`, N filas en `order_items` (una por cada item del request) y 1 fila en `order_state_history` con `estado_anterior_codigo=NULL` y `estado_nuevo_codigo="PENDIENTE"`
- **AND** el `total` del pedido = `sum(cantidad × precio_snapshot) + costo_envio`

#### Scenario: Rollback atómico ante fallo en mitad de la operación
- **WHEN** durante la creación de un pedido falla la inserción del `HistorialEstadoPedido` (por ejemplo, error de integridad referencial simulado)
- **THEN** el sistema responde `500 Internal Server Error` (o el error mapeado correspondiente)
- **AND** en BD no existe ninguna fila en `orders`, `order_items` ni `order_state_history` asociada al request fallido

#### Scenario: Pedido nace en estado PENDIENTE con historial inicial
- **WHEN** un cliente crea un pedido exitosamente
- **THEN** la columna `orders.estado_codigo` vale exactamente `"PENDIENTE"`
- **AND** existe exactamente una fila en `order_state_history` con `pedido_id` del nuevo pedido, `estado_anterior_codigo=NULL`, `estado_nuevo_codigo="PENDIENTE"` y `cambiado_por_id` igual al `user_id` del cliente autenticado

#### Scenario: Items con mismo producto_id pero distinta personalización se aceptan como filas separadas (D13)
- **WHEN** un cliente envía 2 items con el mismo `producto_id=1`: uno con `personalizacion=[3]` (sin cebolla) y otro con `personalizacion=[]` o `null` (con cebolla)
- **THEN** el sistema responde `201 Created`
- **AND** en BD existen **2 filas independientes** en `order_items` con el mismo `producto_id` y `pedido_id` pero distinta `personalizacion`
- **AND** el `total` suma correctamente ambos subtotales (no se deduplica ni agrega cantidades)

---

### Requirement: Snapshots inmutables de precio y dirección

El sistema SHALL capturar y persistir snapshots inmutables al crear un pedido: `precio_snapshot` y `nombre_snapshot` en cada `DetallePedido`, y `direccion_snapshot` en `Pedido` (cuando aplica). Cambios futuros en el catálogo de productos o en las direcciones del cliente SHALL NOT alterar los snapshots de pedidos ya creados.

#### Scenario: Cambio posterior de precio no altera snapshot del pedido
- **WHEN** un cliente crea un pedido con un producto cuyo `precio` actual es `100.00`
- **AND** posteriormente un administrador actualiza el precio del mismo producto a `150.00`
- **THEN** el `precio_snapshot` en el `DetallePedido` original sigue siendo `100.00`
- **AND** el `total` del pedido original se mantiene calculado con `100.00 × cantidad`

#### Scenario: Cambio posterior de nombre de producto no altera snapshot
- **WHEN** un cliente crea un pedido con un producto cuyo `nombre` actual es `"Milanesa Napolitana"`
- **AND** posteriormente se renombra el producto a `"Milanesa Napolitana XL"`
- **THEN** `DetallePedido.nombre_snapshot` del pedido original sigue siendo `"Milanesa Napolitana"`

#### Scenario: Snapshot de dirección preserva datos al momento del pedido
- **WHEN** un cliente crea un pedido con `direccion_id=42` que representa `"Av Siempre Viva 742, Springfield 1000"`
- **AND** posteriormente el cliente edita esa dirección a `"Av Corrientes 1234"`
- **THEN** `orders.direccion_snapshot` del pedido original conserva el texto original `"Av Siempre Viva 742, Springfield 1000"` (o el formato establecido en la implementación)

#### Scenario: Borrado de dirección preserva snapshot histórico
- **WHEN** un cliente crea un pedido con `direccion_id=42`
- **AND** posteriormente el cliente borra (soft-delete) la dirección 42
- **THEN** el pedido original conserva `direccion_snapshot` con el texto histórico
- **AND** `orders.direccion_entrega_id` queda en `NULL` (por `ON DELETE SET NULL`) **O** sigue apuntando a la dirección soft-deleted (según implementación de soft-delete vs. hard-delete en `delivery_addresses`)

---

### Requirement: Validación de stock con lock pesimista dentro de la transacción

El sistema SHALL validar la disponibilidad y el stock de cada producto del pedido DENTRO de la transacción y CON `SELECT FOR UPDATE`. Si algún producto no tiene stock suficiente o no está disponible, el sistema SHALL rechazar el pedido completo y no crear ningún `Pedido` ni `DetallePedido` (todo o nada).

#### Scenario: Stock insuficiente en un item rechaza el pedido completo
- **WHEN** un cliente envía un pedido con 2 items: producto A con stock 10 (pide 5, OK) y producto B con stock 1 (pide 3, insuficiente)
- **THEN** el sistema responde `422 Unprocessable Entity` con un mensaje que identifica el producto B
- **AND** en BD no existe ninguna fila nueva en `orders`, `order_items` ni `order_state_history`
- **AND** el `stock_cantidad` del producto A se mantiene en 10

#### Scenario: Producto marcado como no disponible rechaza el pedido
- **WHEN** un cliente intenta crear un pedido con un producto cuya columna `disponible` es `false`
- **THEN** el sistema responde `422 Unprocessable Entity` con un mensaje que indica que el producto no está disponible
- **AND** no se crea ningún registro

#### Scenario: Producto inexistente o soft-deleted rechaza el pedido
- **WHEN** un cliente envía un `producto_id` que no existe o está soft-deleted (`eliminado_en IS NOT NULL`)
- **THEN** el sistema responde `404 Not Found` con un mensaje que indica que el producto no fue encontrado
- **AND** no se crea ningún registro

#### Scenario: Stock no se decrementa durante la creación del pedido
- **WHEN** un cliente crea un pedido exitoso con un item de producto X (stock 10, pide 3)
- **THEN** después del `201 Created`, `products.stock_cantidad` del producto X sigue siendo `10`
- **AND** el decremento real ocurrirá cuando el pedido transicione a estado `CONFIRMADO` (out-of-scope de este change, lo implementa `order-state-machine-fsm`)

---

### Requirement: Validación de forma de pago contra el catálogo

El sistema SHALL validar que `forma_pago_codigo` exista en el catálogo `payment_methods` y tenga `habilitada=true`. Si el código no existe o está deshabilitado, el sistema SHALL rechazar el pedido.

#### Scenario: forma_pago_codigo inexistente rechaza el pedido
- **WHEN** un cliente envía `forma_pago_codigo="BITCOIN"` (no existe en catálogo)
- **THEN** el sistema responde `422 Unprocessable Entity` con un mensaje que indica que la forma de pago no es válida
- **AND** no se crea ningún registro

#### Scenario: forma_pago_codigo deshabilitada rechaza el pedido
- **WHEN** un administrador deshabilita la forma de pago `EFECTIVO` (`habilitada=false`)
- **AND** un cliente envía `forma_pago_codigo="EFECTIVO"`
- **THEN** el sistema responde `422 Unprocessable Entity`
- **AND** no se crea ningún registro

#### Scenario: forma_pago_codigo válida y habilitada permite el pedido
- **WHEN** un cliente envía `forma_pago_codigo="MERCADOPAGO"` que existe y está habilitada
- **THEN** el sistema procesa el pedido normalmente y lo persiste con `orders.forma_pago_codigo="MERCADOPAGO"`

---

### Requirement: Validación de propiedad de la dirección (anti-leak D6)

El sistema SHALL validar que `direccion_id` (cuando se envíe) pertenezca al usuario autenticado. Si la dirección no existe O pertenece a otro usuario O está soft-deleted, el sistema SHALL responder `404 Not Found` (NUNCA `403 Forbidden`) para no filtrar la existencia de IDs ajenos.

#### Scenario: Dirección de otro usuario responde 404 (no 403)
- **WHEN** el cliente A (id=1) envía `direccion_id=99` que pertenece al cliente B (id=2)
- **THEN** el sistema responde `404 Not Found` con un mensaje genérico "Dirección no encontrada"
- **AND** la respuesta NO debe diferenciar entre "no existe" y "pertenece a otro usuario"

#### Scenario: Dirección inexistente responde 404
- **WHEN** un cliente envía `direccion_id=999999` que no existe
- **THEN** el sistema responde `404 Not Found`

#### Scenario: Dirección propia válida procesa el pedido
- **WHEN** un cliente envía `direccion_id` propio activo (no soft-deleted, `user_id` coincide)
- **THEN** el sistema captura el snapshot en `direccion_snapshot` y procesa el pedido

---

### Requirement: Retiro en local (direccion_id opcional)

El sistema SHALL aceptar pedidos sin dirección de entrega (`direccion_id` omitido o `null`). En ese caso, `orders.direccion_entrega_id` y `orders.direccion_snapshot` quedan en `NULL`, y `costo_envio` es `0.00`.

#### Scenario: Pedido sin direccion_id (retiro en local) acepta y persiste con NULL
- **WHEN** un cliente envía un body sin `direccion_id` (o con `direccion_id: null`)
- **THEN** el sistema responde `201 Created`
- **AND** `orders.direccion_entrega_id` es `NULL`
- **AND** `orders.direccion_snapshot` es `NULL`
- **AND** `orders.costo_envio` es `0.00`
- **AND** `orders.total` = `sum(cantidad × precio_snapshot)` (sin costo de envío adicional)

---

### Requirement: Cálculo del total con costo de envío fijo v1

El sistema SHALL calcular `total = sum(cantidad × precio_snapshot) + costo_envio` (RN-PE08). En v1, `costo_envio` es `50.00` cuando el pedido incluye `direccion_id` y `0.00` cuando es retiro en local.

#### Scenario: Total exacto con precios fraccionarios
- **WHEN** un cliente crea un pedido con `direccion_id` propia y 2 items: producto A (precio `19.99`, cantidad 3) y producto B (precio `10.50`, cantidad 2)
- **THEN** `orders.total` es exactamente `59.97 + 21.00 + 50.00 = 130.97` (en `Decimal`, sin pérdida de precisión: `19.99 × 3 = 59.97`, NO `60.00`)
- **AND** `orders.costo_envio` es `50.00`

#### Scenario: Total sin costo de envío en retiro en local
- **WHEN** un cliente crea un pedido sin `direccion_id` y un item (precio `100.00`, cantidad 2)
- **THEN** `orders.total` es exactamente `200.00`
- **AND** `orders.costo_envio` es `0.00`

---

### Requirement: Anti-smuggling — campos privilegiados rechazados

El sistema SHALL rechazar requests que incluyan campos privilegiados que el cliente no debe controlar (`total`, `estado_codigo`, `usuario_id`, `precio_snapshot`, `nombre_snapshot`, `direccion_snapshot`, `created_at`, `id`). El esquema Pydantic SHALL usar `extra="forbid"` tanto en `CrearPedidoRequest` como en `ItemPedidoRequest`.

#### Scenario: Request con total inyectado responde 422
- **WHEN** un cliente envía un body que incluye `"total": 0.01` (intentando bypass de cálculo)
- **THEN** el sistema responde `422 Unprocessable Entity` con un error de validación Pydantic indicando que `total` no es un campo permitido
- **AND** no se crea ningún registro

#### Scenario: Request con estado_codigo inyectado responde 422
- **WHEN** un cliente envía `"estado_codigo": "CONFIRMADO"` intentando saltarse PENDIENTE
- **THEN** el sistema responde `422 Unprocessable Entity`
- **AND** no se crea ningún registro

#### Scenario: Request con usuario_id inyectado responde 422
- **WHEN** un cliente envía `"usuario_id": 999` intentando crear un pedido a nombre de otro user
- **THEN** el sistema responde `422 Unprocessable Entity`
- **AND** no se crea ningún registro

#### Scenario: Request con precio_snapshot inyectado en un item responde 422
- **WHEN** un cliente envía un item con `"precio_snapshot": 0.01` intentando manipular el precio
- **THEN** el sistema responde `422 Unprocessable Entity`
- **AND** el sistema usa SIEMPRE el `precio` actual del producto desde BD como `precio_snapshot`, ignorando cualquier valor del cliente

---

### Requirement: Validaciones Pydantic estrictas del request

El sistema SHALL validar el request con Pydantic v2 antes de cualquier operación de base de datos: al menos 1 item, máximo 50 items, `cantidad >= 1`, `producto_id >= 1`, `forma_pago_codigo` no vacío, `notas` máximo 500 caracteres.

#### Scenario: Request con items vacío responde 422
- **WHEN** un cliente envía `"items": []`
- **THEN** el sistema responde `422 Unprocessable Entity` con un error indicando `min_length=1`

#### Scenario: Request con cantidad cero o negativa responde 422
- **WHEN** un cliente envía un item con `"cantidad": 0` o `"cantidad": -5`
- **THEN** el sistema responde `422 Unprocessable Entity` con un error de validación

#### Scenario: Request sin items responde 422
- **WHEN** un cliente envía un body sin la clave `items`
- **THEN** el sistema responde `422 Unprocessable Entity` con un error de campo requerido

#### Scenario: Notas que exceden 500 caracteres responde 422
- **WHEN** un cliente envía `"notas"` con más de 500 caracteres
- **THEN** el sistema responde `422 Unprocessable Entity`

---

### Requirement: Autenticación y autorización CLIENT obligatorias

El sistema SHALL requerir autenticación válida (JWT access token) y rol `CLIENT` para invocar `POST /api/v1/pedidos`. Requests sin token, con token inválido o de un usuario sin rol CLIENT SHALL ser rechazados.

#### Scenario: Request sin Authorization header responde 401
- **WHEN** se envía `POST /api/v1/pedidos` sin header `Authorization`
- **THEN** el sistema responde `401 Unauthorized`

#### Scenario: Request con token expirado o malformado responde 401
- **WHEN** se envía `POST /api/v1/pedidos` con `Authorization: Bearer xyz` (token inválido)
- **THEN** el sistema responde `401 Unauthorized`

#### Scenario: Usuario sin rol CLIENT responde 403
- **WHEN** un usuario con rol solo `ADMIN` (sin `CLIENT`) intenta crear un pedido
- **THEN** el sistema responde `403 Forbidden`
- **AND** no se crea ningún registro

#### Scenario: Usuario CLIENT autenticado puede crear pedido
- **WHEN** un usuario con rol `CLIENT` y token válido envía un body correcto
- **THEN** el sistema responde `201 Created`

---

### Requirement: Personalización opcional de items (INTEGER[])

El sistema SHALL aceptar opcionalmente un array de IDs de ingredientes (`personalizacion: list[int] | None`) por cada item del pedido. Si se envía, SHALL persistirse en `order_items.personalizacion` como `INTEGER[]` (PostgreSQL). La validación de existencia de los `ingredient_id` queda a cargo del frontend / pre-checkout — el backend solo valida tipo y rangos.

#### Scenario: Personalización válida se persiste como array
- **WHEN** un cliente envía un item con `"personalizacion": [3, 7, 12]`
- **THEN** el sistema persiste `order_items.personalizacion = ARRAY[3, 7, 12]`

#### Scenario: Personalización ausente persiste como NULL
- **WHEN** un cliente envía un item sin la clave `personalizacion` o con `null`
- **THEN** el sistema persiste `order_items.personalizacion = NULL`

#### Scenario: Personalización con ID no positivo responde 422
- **WHEN** un cliente envía `"personalizacion": [0, -1]`
- **THEN** el sistema responde `422 Unprocessable Entity`

---

### Requirement: Schema PedidoRead compacto en la respuesta

El sistema SHALL devolver `PedidoRead` en el response `201 Created`, con los campos `id`, `estado_codigo`, `total`, `created_at` (RN-PE08 alineado con §6.2 de la spec). El response SHALL NOT incluir los items, el historial ni los snapshots — esa información se obtiene via `GET /api/v1/pedidos/{id}` (cubierto por `order-visualization-backend`).

#### Scenario: Response 201 contiene los campos compactos
- **WHEN** un cliente crea un pedido exitoso
- **THEN** la respuesta JSON contiene exactamente las claves `id` (int), `estado_codigo` (string `"PENDIENTE"`), `total` (Decimal/string) y `created_at` (timestamp ISO 8601)
- **AND** la respuesta no incluye `items`, `historial`, `direccion_snapshot`, `precio_snapshot`
