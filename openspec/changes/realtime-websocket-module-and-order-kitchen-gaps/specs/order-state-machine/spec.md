<!--
NOTE ON SPEC↔CODE DIVERGENCE: the live order-state-machine spec describes a
EN_CAMINO→TERMINADO rename that is NOT present in the running code
(backend/features/orders/state_machine.py still has EN_CAMINO). These deltas
target the CURRENT code matrix and do not re-litigate the rename. The
requirement names below match the running module's structure.
-->

## MODIFIED Requirements

### Requirement: FSM define transiciones válidas

El sistema SHALL aceptar solo las transiciones de estado de pedido definidas explícitamente en `ALLOWED_TRANSITIONS` de `backend/features/orders/state_machine.py`. La matriz vigente, tras este change, es:

- `PENDIENTE → {CANCELADO, CANCELADO_ADMIN, CANCELADO_CLIENTE, CONFIRMADO}`
- `CONFIRMADO → {EN_PREPARACION, CANCELADO_ADMIN}` — **se REMUEVE `ENTREGADO`** (atajo que saltea la cocina, P3.10).
- `EN_PREPARACION → {TERMINADO, CANCELADO_ADMIN}`
- `TERMINADO → {EN_CAMINO, ENTREGADO, CANCELADO_ADMIN}`
- `EN_CAMINO → {ENTREGADO}`
- `ENTREGADO`, `CANCELADO`, `CANCELADO_ADMIN`, `CANCELADO_CLIENTE` son terminales (sin salientes).

Cualquier intento fuera de esta lista MUST ser rechazado con `BusinessRuleError` (HTTP 422) por `validate_transition()`.

#### Scenario: CONFIRMADO no puede saltar a ENTREGADO
- **WHEN** se invoca `validate_transition("CONFIRMADO", "ENTREGADO", {"ADMIN"})`
- **THEN** se levanta `BusinessRuleError` — `ENTREGADO` ya no está en `ALLOWED_TRANSITIONS["CONFIRMADO"]`

#### Scenario: Transición FSM válida pasa la validación
- **WHEN** se invoca `validate_transition("CONFIRMADO", "EN_PREPARACION", {"PEDIDOS"})`
- **THEN** retorna sin levantar excepción

#### Scenario: Estado terminal no transiciona
- **WHEN** se intenta llevar un pedido `ENTREGADO` a cualquier otro estado
- **THEN** la respuesta es 422

### Requirement: Permisos por transición (RBAC dinámico)

El sistema SHALL validar, en cada transición manual, que el usuario actor tenga al menos uno de los roles autorizados para esa transición específica, según `TRANSITION_ROLES` de `state_machine.py`. La matriz vigente, tras este change, incluye:

| Transición                          | Roles autorizados              |
|-------------------------------------|--------------------------------|
| `PENDIENTE → CANCELADO`             | CLIENT, PEDIDOS, ADMIN         |
| `PENDIENTE → CANCELADO_CLIENTE`     | CLIENT                         |
| `PENDIENTE → CANCELADO_ADMIN`       | ADMIN, PEDIDOS                 |
| `PENDIENTE → CONFIRMADO`            | PEDIDOS, ADMIN (ver nota webhook) |
| `CONFIRMADO → EN_PREPARACION`       | PEDIDOS, ADMIN, COCINA         |
| `CONFIRMADO → CANCELADO_ADMIN`      | PEDIDOS, ADMIN                 |
| `EN_PREPARACION → TERMINADO`        | PEDIDOS, ADMIN, COCINA         |
| `EN_PREPARACION → CANCELADO_ADMIN`  | ADMIN (solo) — RN-RB08         |
| `TERMINADO → EN_CAMINO`             | PEDIDOS, ADMIN                 |
| `TERMINADO → ENTREGADO`             | PEDIDOS, ADMIN                 |
| `TERMINADO → CANCELADO_ADMIN`       | ADMIN — **AÑADIDA** (P3.9)     |
| `EN_CAMINO → ENTREGADO`             | PEDIDOS, ADMIN                 |

Se REMUEVE la entrada `CONFIRMADO → ENTREGADO` (P3.10, ya no es transición FSM válida). Si el usuario no tiene rol válido, la respuesta MUST ser 403 (`ForbiddenError`).

#### Scenario: ADMIN cancela un pedido en TERMINADO
- **GIVEN** un pedido en `TERMINADO`
- **WHEN** un usuario `ADMIN` solicita la transición a `CANCELADO_ADMIN`
- **THEN** la transición se ejecuta — `ADMIN` está en `TRANSITION_ROLES[("TERMINADO", "CANCELADO_ADMIN")]` (antes daba 403 por faltar la entrada)

#### Scenario: PEDIDOS no puede cancelar desde TERMINADO
- **WHEN** un usuario `PEDIDOS` (sin ADMIN) solicita `TERMINADO → CANCELADO_ADMIN`
- **THEN** la respuesta es 403 — solo ADMIN

#### Scenario: CONFIRMADO→ENTREGADO ya no tiene entrada RBAC
- **WHEN** se inspecciona `TRANSITION_ROLES`
- **THEN** no existe la clave `("CONFIRMADO", "ENTREGADO")`

## ADDED Requirements

### Requirement: CONFIRMADO no se dispara manualmente desde la UI de admin

El sistema SHALL impedir que la UI de administración ofrezca una acción manual "Confirmar pedido" que lleve un pedido `PENDIENTE → CONFIRMADO`. `CONFIRMADO` se setea por el flujo de pago/webhook, no por un botón manual. El conjunto de acciones de admin para un pedido `PENDIENTE` MUST limitarse a las cancelaciones/rechazo permitidas.

#### Scenario: La UI de admin no muestra "Confirmar pedido" en PENDIENTE
- **WHEN** un ADMIN abre el detalle de un pedido en `PENDIENTE`
- **THEN** no se ofrece un botón que dispare `PENDIENTE → CONFIRMADO`; las acciones disponibles son de rechazo/cancelación

#### Scenario: El backend sigue bloqueando CONFIRMADO manual del CLIENT
- **WHEN** se invoca `avanzar_estado(nuevo_estado="CONFIRMADO")` desde un camino humano no autorizado
- **THEN** se levanta `BusinessRuleError` ("CONFIRMADO solo se setea automáticamente vía webhook de pago")

### Requirement: Guarda de disponibilidad de ingredientes bloquea el avance a cocina

El sistema SHALL impedir que un pedido avance en las transiciones `CONFIRMADO → EN_PREPARACION` y `EN_PREPARACION → TERMINADO` si ALGUNA de sus líneas requiere un ingrediente con `activo = false` que NO esté excluido en la `personalizacion` de esa línea. La guarda es **consciente de exclusiones por línea** pero se evalúa a **nivel de pedido**: alcanza con que una sola línea requiera un ingrediente no disponible (no excluido) para bloquear todo el pedido. La guarda corre en la capa de servicio (lee líneas + ingredientes del producto + `activo`) ANTES de `validate_transition`; `state_machine.py` permanece puro. El bloqueo se levanta automáticamente cuando el ingrediente vuelve a `activo = true` (la guarda re-lee `activo` en cada intento). Al bloquear, se levanta `BusinessRuleError` (HTTP 422) nombrando el ingrediente faltante.

Esta guarda NO modifica `ALLOWED_TRANSITIONS` ni `TRANSITION_ROLES` — disponibilidad es un dato dinámico, no una arista estática de la FSM.

#### Scenario: Pedido de una línea con ingrediente no disponible se bloquea
- **GIVEN** un pedido en `CONFIRMADO` con una sola línea cuyo producto requiere el ingrediente 7
- **AND** `Ingrediente(7).activo = false`
- **AND** la línea NO excluye el ingrediente 7 en su `personalizacion`
- **WHEN** se intenta `CONFIRMADO → EN_PREPARACION`
- **THEN** se levanta `BusinessRuleError` (422) que nombra el ingrediente 7 — el pedido no avanza

#### Scenario: Si todas las líneas excluyen el ingrediente no disponible, el pedido avanza
- **GIVEN** un pedido en `CONFIRMADO` cuyo único producto que usa el ingrediente 7 lo tiene excluido en TODAS las líneas (`personalizacion` lo contiene)
- **AND** `Ingrediente(7).activo = false`
- **WHEN** se intenta `CONFIRMADO → EN_PREPARACION`
- **THEN** la guarda permite el avance — ninguna línea requiere el ingrediente no disponible

#### Scenario: Pedido de dos líneas, una excluye y la otra requiere — se bloquea
- **GIVEN** un pedido con dos líneas: la línea A excluye el ingrediente 7, la línea B lo requiere (no lo excluye)
- **AND** `Ingrediente(7).activo = false`
- **WHEN** se intenta `EN_PREPARACION → TERMINADO`
- **THEN** se bloquea con `BusinessRuleError` (422) — la línea B requiere el ingrediente no disponible, y la guarda opera a nivel de pedido

#### Scenario: El bloqueo se levanta cuando el ingrediente vuelve a estar disponible
- **GIVEN** un pedido bloqueado porque el ingrediente 7 tenía `activo = false`
- **WHEN** un ADMIN resuelve el faltante y `Ingrediente(7).activo` vuelve a `true`
- **AND** se reintenta la transición a cocina
- **THEN** la guarda ya no bloquea y la transición procede (sujeta a FSM/RBAC normales)

#### Scenario: La guarda no afecta transiciones fuera de cocina
- **GIVEN** un pedido con un ingrediente `activo = false`
- **WHEN** se intenta una transición que no es `CONFIRMADO → EN_PREPARACION` ni `EN_PREPARACION → TERMINADO` (por ejemplo una cancelación)
- **THEN** la guarda de disponibilidad no interviene
