## ADDED Requirements

### Requirement: Endpoint GET /api/v1/pedidos role-aware

El sistema SHALL exponer `GET /api/v1/pedidos` con autenticación Bearer JWT obligatoria (`Depends(get_current_user)`). El comportamiento del endpoint MUST variar según los roles del usuario autenticado:

- Usuario con rol `CLIENT` (sin PEDIDOS ni ADMIN): el endpoint MUST filtrar automáticamente `pedido.user_id == current_user.id`. Otros pedidos NO aparecen, ni con filtros ni en el conteo total.
- Usuario con rol `PEDIDOS` o `ADMIN`: el endpoint MUST devolver pedidos de TODOS los usuarios sin filtro de ownership.
- Usuario con rol exclusivo `STOCK` (sin CLIENT/PEDIDOS/ADMIN): el endpoint MUST responder HTTP 403 (`ForbiddenError`). STOCK no tiene visibilidad de pedidos en US-051.
- Sin token o token inválido: HTTP 401.

La determinación del path (CLIENT vs admin) MUST hacerse en `OrderService.listar_pedidos(user, filtros)`, no en el router. El router solo extrae `current_user` y delega.

Response 200 OK con `PaginatedPedidos` (ver Requirement "Schema PaginatedPedidos y PedidoListItem").

#### Scenario: CLIENT solo ve sus propios pedidos
- **GIVEN** un `CLIENT` con `user_id=5` que tiene 3 pedidos propios, y existen otros 10 pedidos en el sistema de otros usuarios
- **WHEN** envía `GET /api/v1/pedidos`
- **THEN** la respuesta es 200 con `items` de longitud 3 (solo sus pedidos) y `total=3`

#### Scenario: PEDIDOS ve todos los pedidos del sistema
- **GIVEN** un usuario con rol `PEDIDOS` (sin ser dueño de ningún pedido)
- **WHEN** envía `GET /api/v1/pedidos`
- **THEN** la respuesta es 200 con todos los pedidos del sistema en `items`, paginados según `page` y `limit`

#### Scenario: ADMIN también ve todos
- **GIVEN** un usuario con rol `ADMIN`
- **WHEN** envía `GET /api/v1/pedidos`
- **THEN** la respuesta es 200 con todos los pedidos del sistema

#### Scenario: STOCK recibe 403
- **GIVEN** un usuario con rol exclusivo `STOCK`
- **WHEN** envía `GET /api/v1/pedidos`
- **THEN** la respuesta es 403 con `ForbiddenError`

#### Scenario: Sin auth retorna 401
- **WHEN** se envía `GET /api/v1/pedidos` sin header `Authorization`
- **THEN** la respuesta es 401

---

### Requirement: Filtros del endpoint listado

El endpoint `GET /api/v1/pedidos` SHALL aceptar los siguientes query params, todos opcionales:

- `estado: Literal["PENDIENTE", "CONFIRMADO", "EN_PREPARACION", "EN_CAMINO", "ENTREGADO", "CANCELADO"]` — filtra por `pedido.estado_codigo` con igualdad exacta. Cualquier otro valor MUST resultar en 422 (validación Pydantic).
- `desde: date` y `hasta: date` (ISO 8601 `YYYY-MM-DD`) — filtran por `pedido.creado_en` con rango inclusivo `creado_en >= desde AND creado_en < (hasta + 1 día)` para tratar `hasta` como "día completo". Si ambos están presentes y `desde > hasta`, MUST responder 422 con mensaje "desde no puede ser posterior a hasta" (validado por `model_validator` de Pydantic).
- `q: str` — search auto-detect: si `q` parsea a `int` (regex `^\d+$`), el sistema MUST filtrar por `pedido.id == int(q)`; en otro caso, MUST aplicar `ILIKE '%q%'` sobre la expresión `usuario.nombre || ' ' || usuario.apellido` (join con `users`). La búsqueda es case-insensitive.
- `page: int >= 1` (default 1) — número de página. Valores < 1 MUST resultar en 422.
- `limit: int 1..100` (default 20) — tamaño de página. Valores fuera de rango MUST resultar en 422.

Los filtros MUST combinarse con AND (todos los presentes se aplican simultáneamente). El listado MUST ordenarse por `creado_en DESC` (más recientes primero, US-049).

#### Scenario: Filtro por estado retorna solo pedidos con ese estado
- **GIVEN** un PEDIDOS y existen 5 pedidos `CONFIRMADO`, 3 `EN_PREPARACION` y 2 `ENTREGADO`
- **WHEN** envía `GET /api/v1/pedidos?estado=CONFIRMADO`
- **THEN** la respuesta es 200 con `items` de longitud 5 y `total=5`, todos con `estado_codigo="CONFIRMADO"`

#### Scenario: Filtro por rango de fechas
- **GIVEN** un PEDIDOS y pedidos creados en 2026-01-15 (3), 2026-02-01 (2), 2026-03-10 (1)
- **WHEN** envía `GET /api/v1/pedidos?desde=2026-02-01&hasta=2026-02-28`
- **THEN** la respuesta es 200 con `items` de longitud 2 (solo los de febrero)

#### Scenario: desde posterior a hasta retorna 422
- **WHEN** se envía `GET /api/v1/pedidos?desde=2026-12-31&hasta=2026-01-01`
- **THEN** la respuesta es 422 con error indicando "desde no puede ser posterior a hasta"

#### Scenario: Filtro q numérico busca por pedido.id
- **GIVEN** un PEDIDOS y existe `pedido_id=42`
- **WHEN** envía `GET /api/v1/pedidos?q=42`
- **THEN** la respuesta es 200 con `items` de longitud 1 (el pedido 42)

#### Scenario: Filtro q string busca por nombre+apellido del cliente con ILIKE
- **GIVEN** un PEDIDOS y existen pedidos del cliente "Juan Pérez" y de "María García"
- **WHEN** envía `GET /api/v1/pedidos?q=Pérez`
- **THEN** la respuesta es 200 con `items` solo de los pedidos de Juan Pérez

#### Scenario: Filtro q insensible a mayúsculas
- **WHEN** se envía `q=PÉREZ` o `q=pérez`
- **THEN** ambas devuelven los mismos resultados (ILIKE case-insensitive)

#### Scenario: page negativo o cero retorna 422
- **WHEN** se envía `GET /api/v1/pedidos?page=0`
- **THEN** la respuesta es 422

#### Scenario: limit fuera de rango retorna 422
- **WHEN** se envía `GET /api/v1/pedidos?limit=500`
- **THEN** la respuesta es 422 con error indicando que limit debe estar entre 1 y 100

#### Scenario: estado inválido retorna 422
- **WHEN** se envía `GET /api/v1/pedidos?estado=PAGADO`
- **THEN** la respuesta es 422 (Pydantic rechaza Literal no permitido)

#### Scenario: Orden por creado_en DESC
- **GIVEN** un CLIENT con 3 pedidos creados en t1, t2, t3 (t3 más reciente)
- **WHEN** envía `GET /api/v1/pedidos`
- **THEN** `items[0]` es el pedido de t3, `items[1]` el de t2, `items[2]` el de t1

#### Scenario: Combinación de filtros (estado + fechas + q)
- **WHEN** un PEDIDOS envía `GET /api/v1/pedidos?estado=CONFIRMADO&desde=2026-02-01&q=Pérez`
- **THEN** la respuesta contiene solo pedidos CONFIRMADO de Juan Pérez creados desde 2026-02-01

---

### Requirement: Paginación y conteo total

El endpoint listado SHALL devolver un objeto `PaginatedPedidos` con la siguiente forma:

```json
{
  "items": [PedidoListItem, ...],
  "total": <int>,
  "page": <int>,
  "limit": <int>
}
```

- `total` MUST representar el conteo de pedidos que matchean los filtros aplicados, ANTES de paginar. El sistema calcula `total` con un `SELECT COUNT(*)` aplicando los mismos `WHERE` que el listado (incluyendo el filtro de ownership cuando es CLIENT).
- `items` MUST contener como máximo `limit` elementos, correspondientes a la página `page` (offset = `(page - 1) * limit`).
- Si `page` excede el número de páginas disponibles, `items` MUST ser una lista vacía y `total` MUST reflejar el conteo real (no cero).

#### Scenario: Paginación correcta con offset
- **GIVEN** un PEDIDOS y 25 pedidos totales en el sistema
- **WHEN** envía `GET /api/v1/pedidos?page=2&limit=10`
- **THEN** la respuesta es 200 con `items` de longitud 10 (pedidos 11..20 en orden DESC), `total=25`, `page=2`, `limit=10`

#### Scenario: Última página parcial
- **GIVEN** 25 pedidos totales
- **WHEN** envía `?page=3&limit=10`
- **THEN** `items` tiene longitud 5 (pedidos 21..25), `total=25`

#### Scenario: Página fuera de rango devuelve items vacío
- **GIVEN** 25 pedidos totales
- **WHEN** envía `?page=10&limit=10`
- **THEN** `items=[]`, `total=25`, `page=10`, `limit=10` (no 404)

#### Scenario: total respeta filtros
- **GIVEN** un CLIENT con 3 pedidos propios y 10 pedidos ajenos en el sistema
- **WHEN** envía `GET /api/v1/pedidos`
- **THEN** `total=3` (no 13)

---

### Requirement: Schema PaginatedPedidos y PedidoListItem

El sistema SHALL definir los siguientes schemas Pydantic en `backend/features/orders/schemas.py`:

`PedidoListItem` (compact, sin items/historial/pagos) MUST contener:
- `id: int`
- `estado_codigo: str` (uno de los 6 códigos del FSM)
- `total: Decimal` (serializado como string en JSON para preservar precisión)
- `costo_envio: Decimal`
- `forma_pago_codigo: str`
- `creado_en: datetime`
- `items_count: int` (cantidad de filas en `order_items` para ese pedido)

`PaginatedPedidos` MUST contener:
- `items: list[PedidoListItem]`
- `total: int`
- `page: int`
- `limit: int`

`PedidoListItem` NO incluye items, historial, pagos, ni datos del cliente (no eager-load en la lista — ver D4 del design para el motivo).

#### Scenario: Response de listado no contiene relaciones eager-loaded
- **WHEN** un CLIENT consulta su listado
- **THEN** cada elemento en `items` contiene solo los campos compactos enumerados arriba
- **AND** NO contiene `items` (filas de order_items), `historial`, `pagos`, ni `direccion_snapshot`

#### Scenario: items_count refleja la cantidad de DetallePedido del pedido
- **GIVEN** un pedido con 3 filas en `order_items`
- **WHEN** el cliente consulta el listado
- **THEN** el `PedidoListItem` correspondiente tiene `items_count=3`

#### Scenario: total se serializa como string Decimal-safe
- **WHEN** un pedido tiene `total=19.99`
- **THEN** el JSON response contiene `"total": "19.99"` (no `19.99` como número con potencial pérdida de precisión)

---

### Requirement: Endpoint GET /api/v1/pedidos/{id} role-aware con detalle completo

El sistema SHALL exponer `GET /api/v1/pedidos/{pedido_id}` con autenticación Bearer JWT obligatoria. El endpoint MUST:

- Para usuario con rol `CLIENT` (sin PEDIDOS ni ADMIN): solo permitir acceso si `pedido.user_id == current_user.id`. Caso contrario MUST responder 404 (anti-leak, ver Requirement "Anti-leak 404").
- Para usuario con rol `PEDIDOS` o `ADMIN`: permitir acceso a cualquier pedido existente.
- Para usuario con rol exclusivo `STOCK`: 403 (`ForbiddenError`), idéntico al endpoint listado.
- Sin auth: 401.

Response 200 OK con `PedidoDetalle` (ver Requirement "Schema PedidoDetalle").

Si el pedido no existe (cualquier rol): 404 con `NotFoundError("Pedido no encontrado")`.

#### Scenario: CLIENT consulta su propio pedido — 200 OK
- **GIVEN** un `CLIENT` con `user_id=5` dueño del pedido `id=10`
- **WHEN** envía `GET /api/v1/pedidos/10`
- **THEN** la respuesta es 200 con `PedidoDetalle` completo (items, historial, pagos, dirección snapshot)

#### Scenario: PEDIDOS consulta pedido de cualquier cliente — 200 OK
- **GIVEN** un usuario con rol `PEDIDOS` y existe pedido `id=10` perteneciente al cliente `user_id=5`
- **WHEN** envía `GET /api/v1/pedidos/10`
- **THEN** la respuesta es 200 con `PedidoDetalle` completo

#### Scenario: ADMIN consulta cualquier pedido — 200 OK
- **GIVEN** un `ADMIN`
- **WHEN** envía `GET /api/v1/pedidos/10`
- **THEN** la respuesta es 200 con `PedidoDetalle` completo

#### Scenario: Pedido inexistente — 404
- **WHEN** un usuario (cualquier rol válido) envía `GET /api/v1/pedidos/9999` y el pedido no existe
- **THEN** la respuesta es 404 con `NotFoundError`

#### Scenario: STOCK sin acceso — 403
- **GIVEN** un usuario con rol exclusivo `STOCK`
- **WHEN** envía `GET /api/v1/pedidos/10`
- **THEN** la respuesta es 403

#### Scenario: Sin auth — 401
- **WHEN** se envía `GET /api/v1/pedidos/10` sin token
- **THEN** la respuesta es 401

---

### Requirement: Anti-leak 404 cuando CLIENT pide pedido ajeno

El sistema SHALL responder HTTP 404 (`NotFoundError("Pedido no encontrado")`) cuando un usuario con rol `CLIENT` (sin PEDIDOS ni ADMIN) intenta acceder vía `GET /api/v1/pedidos/{pedido_id}` a un pedido que existe pero cuyo `user_id` no coincide con el suyo.

La respuesta MUST ser estructuralmente idéntica al caso "el pedido no existe": mismo status (404), mismo cuerpo (`NotFoundError`, mismo mensaje en español: "Pedido no encontrado"), mismo path de ejecución (no branching condicional que pudiera generar timing diferente).

El service MUST invocar `repository.get_pedido_completo(pedido_id, user_id=current_user.id)` para CLIENT y dejar que el filtro `WHERE pedido.user_id = :user_id` en la query unifique ambos casos. Si retorna `None`, raise `NotFoundError`. NO se permite la implementación alternativa "primero fetcheo sin filtro, después chequeo ownership y decido 403 vs 404".

Usuarios con rol `PEDIDOS` o `ADMIN` SHALL saltearse este filtro: el service invoca `get_pedido_completo(pedido_id, user_id=None)` y el repo NO aplica filtro de ownership.

#### Scenario: CLIENT consulta pedido de otro cliente — 404 (no 403)
- **GIVEN** un `CLIENT` con `user_id=5` y existe el pedido `id=99` perteneciente a `user_id=7`
- **WHEN** envía `GET /api/v1/pedidos/99`
- **THEN** la respuesta es 404 con `NotFoundError("Pedido no encontrado")`
- **AND** la respuesta NO debe ser 403, NO debe mencionar ownership, NO debe diferenciar este caso de un pedido inexistente

#### Scenario: Pedido inexistente y pedido ajeno son indistinguibles para el CLIENT
- **GIVEN** un `CLIENT` con `user_id=5`
- **WHEN** envía dos requests, uno a `/api/v1/pedidos/99` (existe pero ajeno) y otro a `/api/v1/pedidos/9999` (no existe)
- **THEN** ambas respuestas son 404 con cuerpos estructuralmente idénticos (mismo schema de error, mismo mensaje)

#### Scenario: PEDIDOS ve pedido sin filtro de ownership
- **GIVEN** un usuario con rol `PEDIDOS` (no es dueño de ningún pedido)
- **WHEN** envía `GET /api/v1/pedidos/99` (existe, pertenece a `user_id=7`)
- **THEN** la respuesta es 200 con `PedidoDetalle` del pedido 99

---

### Requirement: Schema PedidoDetalle con items, historial y pagos

El sistema SHALL definir `PedidoDetalle` en `backend/features/orders/schemas.py` con la siguiente estructura:

- `id: int`
- `user_id: int` (id del cliente dueño del pedido)
- `estado_codigo: str`
- `total: Decimal`
- `costo_envio: Decimal`
- `forma_pago_codigo: str`
- `direccion_snapshot: str | None` (texto inmutable capturado al crear el pedido)
- `notas: str | None`
- `creado_en: datetime`
- `actualizado_en: datetime | None`
- `items: list[ItemDetalle]`
- `historial: list[HistorialItem]`
- `pagos: list[PagoSummary]` (lista vacía si no tiene pagos asociados)

`ItemDetalle` MUST contener:
- `id: int`
- `producto_id: int`
- `nombre_snapshot: str`
- `precio_snapshot: Decimal`
- `cantidad: int`
- `personalizacion: list[int] | None`

`HistorialItem` MUST contener:
- `id: int`
- `estado_anterior_codigo: str | None` (NULL para la transición inicial PENDIENTE)
- `estado_nuevo_codigo: str`
- `cambiado_por_id: int | None` (NULL = SISTEMA, p. ej. webhook)
- `motivo: str | None`
- `creado_en: datetime`

`PagoSummary` MUST contener:
- `id: int`
- `status: str` (estado del pago: `approved`, `pending`, `rejected`, etc., según `payment-mercadopago-backend`)
- `monto: Decimal`
- `fecha: datetime` (timestamp del pago)

Todos los `Decimal` SHALL serializarse como string en JSON.

`historial` MUST ordenarse por `creado_en ASC` (transiciones en orden cronológico). `pagos` MUST ordenarse por `fecha DESC`. `items` MUST ordenarse por `id ASC` (orden estable de inserción).

#### Scenario: Detalle incluye items con snapshots
- **GIVEN** un pedido con 2 items (producto A con `precio_snapshot=100.00, nombre_snapshot="Pizza"`, producto B con `precio_snapshot=50.00, nombre_snapshot="Empanada"`)
- **WHEN** se consulta el detalle
- **THEN** `items` contiene exactamente 2 entradas con los snapshots arriba (no el `precio` actual del producto)

#### Scenario: Detalle incluye historial completo cronológico
- **GIVEN** un pedido que pasó por PENDIENTE → CONFIRMADO → EN_PREPARACION → EN_CAMINO → ENTREGADO
- **WHEN** se consulta el detalle
- **THEN** `historial` contiene 5 entradas, ordenadas por `creado_en ASC`:
  - `[0]: estado_anterior=null, estado_nuevo=PENDIENTE` (creación)
  - `[1]: estado_anterior=PENDIENTE, estado_nuevo=CONFIRMADO, cambiado_por_id=null` (SISTEMA / webhook)
  - `[2..4]: ...` con `cambiado_por_id` del operador correspondiente

#### Scenario: Detalle incluye pagos cuando existen
- **GIVEN** un pedido CONFIRMADO con un pago `approved` por `199.99` el `2026-03-10T14:30:00Z`
- **WHEN** se consulta el detalle
- **THEN** `pagos` contiene exactamente 1 entrada con `status="approved"`, `monto="199.99"`, `fecha` correspondiente

#### Scenario: Detalle de pedido PENDIENTE sin pagos
- **GIVEN** un pedido PENDIENTE sin pagos asociados
- **WHEN** se consulta el detalle
- **THEN** `pagos` es una lista vacía `[]` (no `null`)

#### Scenario: Detalle incluye direccion_snapshot
- **GIVEN** un pedido creado con `direccion_snapshot="Av Siempre Viva 742"`
- **WHEN** se consulta el detalle
- **THEN** el campo `direccion_snapshot` contiene exactamente `"Av Siempre Viva 742"`

#### Scenario: Detalle de pedido de retiro en local (sin dirección)
- **GIVEN** un pedido creado sin `direccion_id` (retiro en local)
- **WHEN** se consulta el detalle
- **THEN** `direccion_snapshot` es `null` y `costo_envio` es `"0.00"`

#### Scenario: motivo de cancelación aparece en historial
- **GIVEN** un pedido CONFIRMADO cancelado por un PEDIDOS con `motivo="Cliente pidió reembolso"`
- **WHEN** se consulta el detalle
- **THEN** existe en `historial` una entrada con `estado_anterior_codigo="CONFIRMADO"`, `estado_nuevo_codigo="CANCELADO"`, `motivo="Cliente pidió reembolso"`

---

### Requirement: Eager loading controlado en detalle

El sistema SHALL ejecutar `selectinload(Pedido.items, Pedido.historial, Pedido.pagos)` cuando se carga el detalle vía `OrderRepository.get_pedido_completo(pedido_id, user_id)`. El query del listado NO MUST eager-loadear ninguna de estas relaciones — solo cargar campos de `Pedido` (con subquery para `items_count`).

Esto evita N+1 al listar muchos pedidos y mantiene el detalle eficiente (4 queries totales: una para el pedido + tres `IN` para items/historial/pagos, en lugar de una por cada item).

#### Scenario: Listado no dispara queries adicionales por relación
- **GIVEN** un usuario que consulta `GET /api/v1/pedidos` con `limit=20` y existen 20 pedidos
- **WHEN** se ejecuta el endpoint
- **THEN** el log de SQL muestra solo 2 queries: el `COUNT(*)` para `total` y el `SELECT` paginado de orders (más subquery para `items_count`). No hay queries adicionales por relaciones de cada pedido.

#### Scenario: Detalle ejecuta selectinload para items, historial y pagos
- **GIVEN** un pedido con 5 items, 4 transiciones de historial y 1 pago
- **WHEN** se consulta `GET /api/v1/pedidos/{id}`
- **THEN** el log de SQL muestra el SELECT principal sobre orders + 3 queries `SELECT ... WHERE pedido_id IN (...)` (una por relación). NO hay una query por cada item/historial/pago individual.

---

### Requirement: OrderService.listar_pedidos y get_pedido_detalle son los únicos puntos de RBAC dinámico

El sistema SHALL encapsular la lógica role-aware (decidir si filtra por `user_id` o no) en `OrderService.listar_pedidos(user, filtros)` y `OrderService.get_pedido_detalle(user, pedido_id)`. El router NO debe contener lógica condicional basada en roles — solo extrae `current_user`, llama al service, y mapea excepciones a HTTP status codes.

La decisión de "filtrar por ownership" se basa en si el usuario tiene rol `PEDIDOS` o `ADMIN` (no filtra) versus solo `CLIENT` (filtra por `user_id == current_user.id`). El rol `STOCK` exclusivo se rechaza con `ForbiddenError` en el service (o vía `Depends(require_role(...))` del router; ver tasks.md para la elección de implementación).

#### Scenario: Service decide path admin para usuario con rol PEDIDOS
- **WHEN** `OrderService.listar_pedidos(user=<PEDIDOS>, filtros=...)` se invoca
- **THEN** internamente invoca `repository.list_with_filter(user_id=None, ...)` (sin filtro de ownership)

#### Scenario: Service decide path client para CLIENT puro
- **WHEN** `OrderService.listar_pedidos(user=<CLIENT solo>, filtros=...)` se invoca con `user.id=5`
- **THEN** internamente invoca `repository.list_with_filter(user_id=5, ...)`

#### Scenario: Service rechaza STOCK con ForbiddenError
- **WHEN** `OrderService.listar_pedidos(user=<STOCK exclusivo>, filtros=...)` se invoca
- **THEN** se levanta `ForbiddenError("Rol STOCK no autorizado para listar pedidos")`

#### Scenario: Service decide path client en detalle para CLIENT
- **WHEN** `OrderService.get_pedido_detalle(user=<CLIENT, id=5>, pedido_id=10)` se invoca
- **THEN** internamente llama `repository.get_pedido_completo(pedido_id=10, user_id=5)`

#### Scenario: Service decide path admin en detalle para ADMIN
- **WHEN** `OrderService.get_pedido_detalle(user=<ADMIN>, pedido_id=10)` se invoca
- **THEN** internamente llama `repository.get_pedido_completo(pedido_id=10, user_id=None)`
