# Spec Delta: kitchen-display-backend

## ADDED Requirements

### Requirement: Endpoint REST de carga inicial del KDS

El sistema SHALL exponer `GET /api/v1/cocina/pedidos`, protegido por `require_role("COCINA", "ADMIN")`, que devuelve los pedidos en estado `CONFIRMADO` y `EN_PREPARACION` ordenados por antigüedad ascendente de entrada a cocina (RN-CO02). El "tiempo de entrada a cocina" es el `creado_en` del `HistorialEstadoPedido` cuyo `estado_nuevo_codigo = "CONFIRMADO"`. Cada pedido SHALL incluir: id, `estado_codigo`, ítems (`nombre_snapshot`, `cantidad`, `personalizacion`), `notas` y el timestamp de entrada a cocina. Los pedidos en `PENDIENTE` MUST NOT aparecer (RN-CO01).

#### Scenario: Lista solo CONFIRMADO y EN_PREPARACION
- **WHEN** un usuario con rol `COCINA` invoca `GET /api/v1/cocina/pedidos`
- **THEN** la respuesta es 200 y contiene solo pedidos en `CONFIRMADO` o `EN_PREPARACION`, ninguno en `PENDIENTE`, `TERMINADO`, `EN_CAMINO`, `ENTREGADO` ni cancelados

#### Scenario: Orden por antigüedad de entrada a cocina
- **GIVEN** dos pedidos confirmados, el pedido A confirmado antes que el B
- **WHEN** se invoca `GET /api/v1/cocina/pedidos`
- **THEN** el pedido A aparece antes que el B en la lista

#### Scenario: Rol no autorizado recibe 403
- **WHEN** un usuario con solo rol `CLIENT` invoca `GET /api/v1/cocina/pedidos`
- **THEN** la respuesta es 403

### Requirement: Endpoint WebSocket del KDS con auth en el handshake

El sistema SHALL exponer `WS /api/v1/cocina/ws` que acepta el JWT del usuario (vía query param `token` o cookie de sesión) y SHALL validar ese token y el rol en el handshake antes de aceptar la conexión. Si el token falta, es inválido, o el usuario no tiene rol `COCINA` ni `ADMIN`, el handshake MUST ser rechazado (cierre del WebSocket, sin promover la conexión). La validación de auth del WebSocket MUST ser independiente del borde REST.

#### Scenario: Handshake sin token es rechazado
- **WHEN** un cliente abre `WS /api/v1/cocina/ws` sin token
- **THEN** el handshake se rechaza y la conexión se cierra

#### Scenario: Handshake con rol no autorizado es rechazado
- **WHEN** un usuario con solo rol `CLIENT` abre el WebSocket con su JWT válido
- **THEN** el handshake se rechaza y la conexión se cierra

#### Scenario: Handshake con rol COCINA es aceptado
- **WHEN** un usuario con rol `COCINA` abre el WebSocket con su JWT válido
- **THEN** el handshake es aceptado y la conexión queda registrada para recibir eventos

### Requirement: Gestor de conexiones en proceso (single-instance)

El sistema SHALL mantener un gestor de conexiones WebSocket en memoria del proceso, con un conjunto de conexiones activas protegido para concurrencia (`asyncio.Lock`). El gestor SHALL ofrecer registrar una conexión, desregistrarla al cerrarse, y difundir (`broadcast`) un evento a todas las conexiones activas. El sistema MUST funcionar correctamente con una única instancia del backend; multi-instancia queda fuera de alcance (límite conocido).

#### Scenario: Conexión se desregistra al cerrarse
- **GIVEN** una conexión WebSocket activa registrada en el gestor
- **WHEN** el cliente cierra la conexión
- **THEN** el gestor la remueve del conjunto de conexiones activas y no le envía eventos posteriores

#### Scenario: Broadcast sin conexiones no falla
- **GIVEN** ninguna conexión WebSocket activa
- **WHEN** el sistema difunde un evento de cocina
- **THEN** el evento se descarta sin error (best-effort, RN-CO05)

### Requirement: Publicación de eventos de cocina tras commit del FSM

El sistema SHALL publicar un evento a las conexiones activas del KDS **después** de commitear cada transición de estado relevante en la Unit of Work. Los eventos (léxico snake_case) SHALL ser: `pedido_confirmado` (al entrar a `CONFIRMADO`), `pedido_en_preparacion` (`CONFIRMADO → EN_PREPARACION`), `pedido_terminado` (`EN_PREPARACION → TERMINADO`), y `pedido_cancelado` (cualquier transición a un estado cancelado mientras el pedido está en fase de cocina). El payload SHALL incluir el snapshot mínimo del pedido necesario para agregar, mover o retirar una tarjeta. La publicación MUST ser best-effort: un fallo del broadcast MUST NOT revertir la transición ya commiteada.

#### Scenario: Pedido confirmado emite pedido_confirmado
- **GIVEN** una pantalla de cocina conectada
- **WHEN** un pedido transiciona a `CONFIRMADO`
- **THEN** la conexión recibe un evento `pedido_confirmado` con el snapshot del pedido

#### Scenario: Inicio de preparación emite pedido_en_preparacion
- **WHEN** un pedido transiciona `CONFIRMADO → EN_PREPARACION`
- **THEN** las conexiones activas reciben un evento `pedido_en_preparacion`

#### Scenario: Cocina terminada emite pedido_terminado
- **WHEN** un pedido transiciona `EN_PREPARACION → TERMINADO`
- **THEN** las conexiones activas reciben un evento `pedido_terminado` que indica retirar la tarjeta del KDS

#### Scenario: Cancelación en fase de cocina emite pedido_cancelado
- **WHEN** un pedido en `CONFIRMADO` o `EN_PREPARACION` transiciona a un estado cancelado
- **THEN** las conexiones activas reciben un evento `pedido_cancelado` que indica retirar la tarjeta

#### Scenario: Fallo del broadcast no revierte la transición
- **GIVEN** una transición ya commiteada en la UoW
- **WHEN** la difusión del evento falla
- **THEN** la transición permanece persistida y la operación HTTP responde con éxito
