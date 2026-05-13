## ADDED Requirements

### Requirement: Página Mis Pedidos (CLIENT)

El sistema SHALL renderizar la ruta `/cliente/pedidos` como `MisPedidosPage`, accesible únicamente para usuarios con rol `CLIENT`. La página MUST mostrar la lista paginada de pedidos propios consumiendo `GET /api/v1/pedidos`. Cada pedido MUST mostrar: id, estado con badge color-coded, total, fecha de creación y cantidad de ítems.

#### Scenario: CLIENT ve su lista de pedidos
- **WHEN** un CLIENT navega a `/cliente/pedidos`
- **THEN** la página muestra una lista de cards con sus pedidos ordenados por fecha DESC

#### Scenario: Lista vacía muestra estado vacío
- **WHEN** un CLIENT sin pedidos navega a `/cliente/pedidos`
- **THEN** la página muestra un mensaje de estado vacío (sin tabla ni cards)

#### Scenario: Loading muestra skeletons
- **WHEN** la petición a `/api/v1/pedidos` está en vuelo
- **THEN** la página muestra skeleton cards en lugar del contenido

---

### Requirement: Página Gestión de Pedidos (PEDIDOS/ADMIN)

El sistema SHALL renderizar la ruta `/admin/pedidos` como `PedidosAdminPage`, accesible para usuarios con roles `PEDIDOS` o `ADMIN`. La página MUST mostrar todos los pedidos del sistema con filtros: estado, rango de fechas, y búsqueda por id o nombre de cliente. Los filtros MUST sincronizarse con la URL (`useSearchParams`).

#### Scenario: PEDIDOS ve todos los pedidos con filtros
- **WHEN** un PEDIDOS navega a `/admin/pedidos`
- **THEN** ve una tabla/lista con todos los pedidos y un panel de filtros

#### Scenario: Filtro por estado actualiza la URL y la lista
- **WHEN** el usuario selecciona estado `CONFIRMADO` en el filtro
- **THEN** la URL incluye `?estado=CONFIRMADO` y la lista muestra solo pedidos CONFIRMADO

#### Scenario: Búsqueda por id de pedido
- **WHEN** el usuario escribe `42` en el campo de búsqueda
- **THEN** la lista muestra solo el pedido con id 42

---

### Requirement: Modal de Detalle de Pedido

El sistema SHALL mostrar un `OrderDetailModal` al hacer click en cualquier pedido, tanto en la vista CLIENT como en la PEDIDOS/ADMIN. El modal MUST mostrar: ítems del pedido (nombre, cantidad, precio snapshot, subtotal), timeline de historial de estados con fechas, datos de pago (forma de pago, estado del pago si existe) y dirección snapshot.

#### Scenario: Modal muestra ítems con precio snapshot
- **WHEN** el usuario hace click en un pedido
- **THEN** el modal muestra cada ítem con su precio al momento de la compra (precio_snapshot)

#### Scenario: Modal muestra timeline de estados
- **WHEN** el modal está abierto
- **THEN** se muestra el historial de estados en orden cronológico con fechas

#### Scenario: Cerrar modal con Escape o botón
- **WHEN** el usuario presiona Escape o el botón de cierre
- **THEN** el modal se cierra y la lista queda visible

---

### Requirement: Transiciones de Estado (PEDIDOS/ADMIN)

El sistema SHALL mostrar botones de transición de estado en `PedidosAdminPage` para los pedidos con estados transitables. Las transiciones válidas MUST seguir la FSM: `EN_PREPARACION → EN_CAMINO`, `EN_CAMINO → ENTREGADO`. ADMIN adicionalmente puede cancelar desde `EN_PREPARACION`. La transición MUST invocar `PATCH /api/v1/pedidos/{id}/estado` e invalidar la query de lista al completarse.

#### Scenario: PEDIDOS puede avanzar de EN_PREPARACION a EN_CAMINO
- **WHEN** un PEDIDOS hace click en "Marcar en camino" sobre un pedido EN_PREPARACION
- **THEN** el sistema llama PATCH /pedidos/{id}/estado con nuevo_estado=EN_CAMINO y actualiza la lista

#### Scenario: Pedidos en estado terminal no muestran botones
- **WHEN** un pedido está en estado ENTREGADO o CANCELADO
- **THEN** no se muestran botones de transición

#### Scenario: Error en transición muestra feedback
- **WHEN** el PATCH falla (409 o 422)
- **THEN** se muestra un mensaje de error sin cerrar el modal

---

### Requirement: OrderStatusBadge

El sistema SHALL exponer un componente `OrderStatusBadge` que recibe un `estado_codigo` y renderiza un badge con color semántico: PENDIENTE → amarillo, CONFIRMADO → azul, EN_PREPARACION → naranja, EN_CAMINO → indigo, ENTREGADO → verde, CANCELADO → rojo/muted.

#### Scenario: Badge muestra color correcto por estado
- **WHEN** `OrderStatusBadge` recibe `estado_codigo="ENTREGADO"`
- **THEN** renderiza un badge verde con el texto "Entregado"

#### Scenario: Badge muestra label en español
- **WHEN** el estado es cualquier código válido
- **THEN** el label es en español (ej. "En preparación", "En camino")
