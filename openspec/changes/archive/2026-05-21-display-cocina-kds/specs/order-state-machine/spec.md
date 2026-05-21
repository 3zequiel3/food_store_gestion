# Spec Delta: order-state-machine

## MODIFIED Requirements

### Requirement: FSM define transiciones válidas

El sistema SHALL aceptar solo las siguientes transiciones de estado de pedido, definidas explícitamente en una constante `ALLOWED_TRANSITIONS` del módulo `backend/features/orders/state_machine.py`:

- `PENDIENTE → CONFIRMADO` (solo automática / aceptación del local, ver Req. siguiente).
- `PENDIENTE → CANCELADO` (y variantes `CANCELADO_ADMIN`, `CANCELADO_CLIENTE`).
- `CONFIRMADO → EN_PREPARACION`.
- `CONFIRMADO → CANCELADO_ADMIN`.
- `EN_PREPARACION → TERMINADO`.
- `EN_PREPARACION → CANCELADO_ADMIN`.
- `TERMINADO → EN_CAMINO`.
- `TERMINADO → ENTREGADO`.
- `EN_CAMINO → ENTREGADO`.

`EN_CAMINO` se **re-introduce** al catálogo como nodo del FSM entre `TERMINADO` y `ENTREGADO`. La elección entre `TERMINADO → EN_CAMINO` y `TERMINADO → ENTREGADO` la decide una regla de negocio según el tipo de entrega del pedido (ver requirement de branching por tipo de entrega), no `ALLOWED_TRANSITIONS` por sí sola.

Cualquier intento de transición fuera de esta lista MUST ser rechazado con `BusinessRuleError` (HTTP 422) por `validate_transition()`.

`ENTREGADO`, `CANCELADO`, `CANCELADO_ADMIN` y `CANCELADO_CLIENTE` son estados terminales — no se permite ninguna transición saliente desde ellos (RN-FS06).

#### Scenario: Transición FSM válida pasa la validación
- **WHEN** `validate_transition("CONFIRMADO", "EN_PREPARACION", {"COCINA"})` se invoca
- **THEN** retorna sin levantar excepción

#### Scenario: Transición FSM inválida es rechazada
- **WHEN** `validate_transition("PENDIENTE", "ENTREGADO", {"ADMIN"})` se invoca
- **THEN** se levanta `BusinessRuleError` con detalle "Transición 'PENDIENTE' → 'ENTREGADO' no permitida"

#### Scenario: EN_CAMINO es origen válido hacia ENTREGADO
- **WHEN** `validate_transition("EN_CAMINO", "ENTREGADO", {"ADMIN"})` se invoca
- **THEN** retorna sin levantar excepción

#### Scenario: TERMINADO admite EN_CAMINO y ENTREGADO en el FSM
- **WHEN** se inspecciona `ALLOWED_TRANSITIONS["TERMINADO"]`
- **THEN** contiene tanto `"EN_CAMINO"` como `"ENTREGADO"`

#### Scenario: Estado terminal no transiciona
- **WHEN** el ADMIN invoca `PATCH` para llevar un pedido `ENTREGADO` a cualquier otro estado
- **THEN** la respuesta es 422 — `ENTREGADO` no figura en `ALLOWED_TRANSITIONS` como origen

#### Scenario: CANCELADO es terminal
- **WHEN** se intenta transicionar un pedido en `CANCELADO` a cualquier otro estado
- **THEN** la respuesta es 422

### Requirement: Rename del código `EN_CAMINO` a `TERMINADO` (vocabulario unificado retiro/envío)

`EN_CAMINO` deja de ser un alias eliminado: el sistema SHALL re-introducir `EN_CAMINO` como estado propio del catálogo `order_states`, distinto de `TERMINADO`, mediante una migración Alembic que revierte parcialmente `20260518_0100_rename_en_camino_to_terminado`. `TERMINADO` mantiene su semántica de "comida lista, esperando despacho o retiro"; `EN_CAMINO` representa el reparto en curso de un pedido de envío a domicilio.

Tras esta migración el nodo `TERMINADO` tiene:
- Entrante: `EN_PREPARACION → TERMINADO` (roles PEDIDOS, ADMIN, COCINA).
- Salientes: `TERMINADO → EN_CAMINO` (roles PEDIDOS, ADMIN, solo envíos) y `TERMINADO → ENTREGADO` (roles PEDIDOS, ADMIN, solo retiros).

El alcance de la re-introducción incluye:

1. **Backend datos**: migración Alembic que vuelve a insertar la fila `order_states.codigo = "EN_CAMINO"` (con `orden` entre `TERMINADO` y `ENTREGADO`, `es_terminal=False`). La migración MUST tener `downgrade()` que la elimine de forma segura (solo si no hay pedidos en ese estado).
2. **Backend código**: `state_machine.py` agrega `EN_CAMINO` a `ALLOWED_TRANSITIONS` y `TRANSITION_ROLES`; los schemas que tipan `nuevo_estado` lo aceptan como valor válido.
3. **Frontend**: los tipos y componentes de pedidos (`orders.types.ts`, `OrderTimeline`, `OrderStatusBadge`, `OrderStateActions`, charts de métricas) reconocen `EN_CAMINO` con un label adecuado a envío ("En camino").

**Justificación**: el rename del 18-may había unificado retiro y envío bajo `TERMINADO`, pero el despacho de envíos necesita un estado propio que distinga "listo" de "en reparto". Documentado en D4 del design.

#### Scenario: Migración Alembic re-agrega EN_CAMINO al catálogo
- **GIVEN** una DB cuyo catálogo `order_states` no contiene `"EN_CAMINO"`
- **WHEN** se ejecuta `alembic upgrade head` con la migración del change
- **THEN** existe una fila `order_states.codigo = "EN_CAMINO"` con `es_terminal=False`

#### Scenario: ALLOWED_TRANSITIONS reconoce EN_CAMINO
- **WHEN** se inspecciona `backend/features/orders/state_machine.py`
- **THEN** `ALLOWED_TRANSITIONS["TERMINADO"]` incluye `"EN_CAMINO"` y `ALLOWED_TRANSITIONS["EN_CAMINO"]` incluye `"ENTREGADO"`

#### Scenario: Frontend muestra label de envío para EN_CAMINO
- **WHEN** un usuario ve un pedido cuyo estado actual es `EN_CAMINO`
- **THEN** el `OrderStatusBadge` muestra "En camino" (o equivalente de reparto en curso)

#### Scenario: Downgrade elimina EN_CAMINO de forma segura
- **GIVEN** una DB migrada con `EN_CAMINO` en el catálogo y sin pedidos en ese estado
- **WHEN** se ejecuta `alembic downgrade -1`
- **THEN** la fila `EN_CAMINO` se elimina del catálogo sin dejar FKs colgando

### Requirement: Permisos por transición (RBAC dinámico)

El sistema SHALL validar, en cada transición manual, que el usuario actor tenga al menos uno de los roles autorizados para esa transición específica. La matriz vive en `TRANSITION_ROLES` del módulo `state_machine.py`. Los 4 roles de la spec (`ADMIN`/`STOCK`/`PEDIDOS`/`CLIENT`) se mantienen intactos; este change solo **agrega** `COCINA` a las 2 transiciones de cocina y re-introduce `EN_CAMINO`. La matriz resultante:

| Transición                          | Roles autorizados              |
|-------------------------------------|--------------------------------|
| `PENDIENTE → CANCELADO`             | CLIENT, PEDIDOS, ADMIN         |
| `PENDIENTE → CANCELADO_CLIENTE`     | CLIENT                         |
| `PENDIENTE → CANCELADO_ADMIN`       | PEDIDOS, ADMIN                 |
| `CONFIRMADO → EN_PREPARACION`       | PEDIDOS, ADMIN, COCINA         |
| `CONFIRMADO → CANCELADO_ADMIN`      | PEDIDOS, ADMIN                 |
| `EN_PREPARACION → TERMINADO`        | PEDIDOS, ADMIN, COCINA         |
| `EN_PREPARACION → CANCELADO_ADMIN`  | ADMIN (solo)                   |
| `TERMINADO → EN_CAMINO`             | PEDIDOS, ADMIN                 |
| `TERMINADO → ENTREGADO`             | PEDIDOS, ADMIN                 |
| `EN_CAMINO → ENTREGADO`             | PEDIDOS, ADMIN                 |

El despacho y la entrega los siguen ejecutando `PEDIDOS`/`ADMIN` (sin cambios respecto del estado actual); las transiciones de cocina (`CONFIRMADO → EN_PREPARACION`, `EN_PREPARACION → TERMINADO`) **suman** `COCINA` a los `PEDIDOS`/`ADMIN` que ya las ejecutaban. Si el usuario no tiene ningún rol válido para la transición pedida, el sistema MUST responder HTTP 403 con `ForbiddenError`.

#### Scenario: COCINA avanza un pedido a EN_PREPARACION
- **WHEN** un usuario con rol `COCINA` envía `PATCH` con `nuevo_estado="EN_PREPARACION"` sobre un pedido en `CONFIRMADO`
- **THEN** la transición se ejecuta — `COCINA` está en `TRANSITION_ROLES[("CONFIRMADO", "EN_PREPARACION")]`

#### Scenario: PEDIDOS sigue avanzando un pedido a EN_PREPARACION
- **WHEN** un usuario con rol `PEDIDOS` envía `PATCH` con `nuevo_estado="EN_PREPARACION"` sobre un pedido en `CONFIRMADO`
- **THEN** la transición se ejecuta — `PEDIDOS` permanece en `TRANSITION_ROLES[("CONFIRMADO", "EN_PREPARACION")]`

#### Scenario: COCINA no puede despachar a EN_CAMINO
- **WHEN** un usuario con solo rol `COCINA` envía `PATCH` con `nuevo_estado="EN_CAMINO"` sobre un pedido en `TERMINADO`
- **THEN** la respuesta es 403 — el despacho es de `PEDIDOS`/`ADMIN`

#### Scenario: ADMIN despacha un envío a EN_CAMINO
- **WHEN** un usuario con rol `ADMIN` envía `PATCH` con `nuevo_estado="EN_CAMINO"` sobre un pedido de envío en `TERMINADO`
- **THEN** la transición se ejecuta

#### Scenario: CLIENT no puede avanzar un pedido a EN_PREPARACION
- **WHEN** un usuario con rol `CLIENT` (sin otros roles) envía `PATCH` con `nuevo_estado="EN_PREPARACION"` sobre un pedido en `CONFIRMADO`
- **THEN** la respuesta es 403

## ADDED Requirements

### Requirement: Branching de despacho condicional al tipo de entrega

El sistema SHALL elegir la transición de salida de `TERMINADO` según el tipo de entrega del pedido, determinado por `Pedido.direccion_entrega_id`:

- **Envío** (`direccion_entrega_id NOT NULL`): el camino válido es `TERMINADO → EN_CAMINO → ENTREGADO`. Un intento de `TERMINADO → ENTREGADO` directo MUST ser rechazado con `BusinessRuleError` (422).
- **Retiro** (`direccion_entrega_id IS NULL`): el camino válido es `TERMINADO → ENTREGADO` directo. Un intento de `TERMINADO → EN_CAMINO` MUST ser rechazado con `BusinessRuleError` (422).

Esta regla vive en el servicio (`OrderService`), que carga el `Pedido` concreto, no en `ALLOWED_TRANSITIONS` (que es un mapa estático de códigos sin conocimiento de la instancia).

#### Scenario: Envío exige pasar por EN_CAMINO
- **GIVEN** un pedido de envío (`direccion_entrega_id` no nulo) en estado `TERMINADO`
- **WHEN** un ADMIN intenta `TERMINADO → ENTREGADO` directo
- **THEN** la respuesta es 422

#### Scenario: Envío válido pasa por EN_CAMINO y luego ENTREGADO
- **GIVEN** un pedido de envío en `TERMINADO`
- **WHEN** un ADMIN ejecuta `TERMINADO → EN_CAMINO` y luego `EN_CAMINO → ENTREGADO`
- **THEN** ambas transiciones se ejecutan correctamente

#### Scenario: Retiro va directo a ENTREGADO
- **GIVEN** un pedido de retiro (`direccion_entrega_id` nulo) en `TERMINADO`
- **WHEN** un ADMIN ejecuta `TERMINADO → ENTREGADO`
- **THEN** la transición se ejecuta correctamente

#### Scenario: Retiro no admite EN_CAMINO
- **GIVEN** un pedido de retiro en `TERMINADO`
- **WHEN** un ADMIN intenta `TERMINADO → EN_CAMINO`
- **THEN** la respuesta es 422

### Requirement: Publicación de eventos de tiempo real tras commit de transición

El sistema SHALL publicar un evento hacia las pantallas de cocina conectadas después de commitear cada transición de estado relevante en la Unit of Work del servicio del FSM. La publicación SHALL ocurrir post-commit y SHALL ser best-effort: un fallo del broadcast MUST NOT revertir la transición. Los eventos son `pedido_confirmado`, `pedido_en_preparacion`, `pedido_terminado` y `pedido_cancelado` (ver capability `kitchen-display-backend`).

#### Scenario: Transición a EN_PREPARACION publica evento post-commit
- **GIVEN** una pantalla de cocina conectada
- **WHEN** un pedido transiciona `CONFIRMADO → EN_PREPARACION` y la UoW commitea
- **THEN** se publica `pedido_en_preparacion` después del commit

#### Scenario: Fallo del broadcast no afecta la transición
- **GIVEN** una transición ya commiteada
- **WHEN** la publicación del evento falla
- **THEN** la transición permanece persistida y la respuesta HTTP es exitosa
