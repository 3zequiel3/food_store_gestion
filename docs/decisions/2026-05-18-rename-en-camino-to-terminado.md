# D13 — Rename `EN_CAMINO` → `TERMINADO` (vocabulario unificado retiro/envío)

**Fecha:** 2026-05-18  
**Change:** checkout-pay-first-flow  
**Estado:** Aceptado

## Contexto

El usuario fue explícito sobre querer "un flujo de estados consistente independientemente si es retiro en local o envío". El código `EN_CAMINO` es semánticamente incorrecto para retiro en local — el cliente no "va en camino", va al mostrador.

La spec `order-state-machine` documentaba `EN_CAMINO` como "pedido listo para entrega", pero el nombre del código no reflejaba la realidad del pickup.

## Decisión

El código de estado `EN_CAMINO` se renombra a `TERMINADO` en toda la base de código y datos persistidos.

`TERMINADO` significa: **"pedido listo para ser retirado del local o entregado al cliente"**.

La transición `EN_PREPARACION → EN_CAMINO → ENTREGADO` pasa a ser `EN_PREPARACION → TERMINADO → ENTREGADO`.

La matriz `ALLOWED_TRANSITIONS` y `TRANSITION_ROLES` **mantiene su forma** — solo cambia la clave.

## Alternativas consideradas

### (a) Mantener `EN_CAMINO` y agregar `TERMINADO` como estado paralelo solo para pickup

**Rechazada porque:**
- Bifurca el FSM en dos caminos según tipo de entrega
- Complica la UI (labels condicionales)
- Complica los métricos (¿contar EN_CAMINO + TERMINADO como uno solo?)
- Va exactamente contra el objetivo de "flujo unificado" que pidió el usuario

### (b) Mantener `EN_CAMINO` y documentar la nueva semántica sin renombrar

**Rechazada porque:**
- `EN_CAMINO` es semánticamente incorrecto para pickup — el cliente no "va en camino"
- Forzar la nueva semántica sobre el código equivocado genera lecturas confusas en código y UI
- El nombre del código debe matchear el dominio

### (c) Renombrar a `TERMINADO` (elegida)

**Ventajas:**
- El código matchea el dominio
- Una sola lectura para retiro y envío
- Sin bifurcación
- Semánticamente correcto: el pedido está "terminado" (listo), no "en camino"

## Alcance del rename

### Backend
- `backend/features/orders/state_machine.py`: `ALLOWED_TRANSITIONS`, `TRANSITION_ROLES`
- `backend/features/orders/schemas.py`: Literal de `AvanzarEstadoRequest` y validators
- `backend/scripts/seed.py`: semilla de `estados_pedido`
- Tests en `backend/tests/integration/` y `backend/tests/conftest.py`

### Frontend
- `OrderFilters.tsx`: mapping de labels
- `OrderTimeline.tsx`: labels de estados
- `OrderStatusBadge.tsx`: colors y labels
- `OrderStateActions.tsx`: acciones por estado
- `orders.types.ts`: tipo `EstadoCodigo`
- `PedidosPorEstadoChart.tsx`: color mapping

### DB (migración Alembic)
```sql
UPDATE estados_pedido SET codigo = 'TERMINADO' WHERE codigo = 'EN_CAMINO';
UPDATE orders SET estado_codigo = 'TERMINADO' WHERE estado_codigo = 'EN_CAMINO';
UPDATE order_state_history SET estado_anterior_codigo = 'TERMINADO' WHERE estado_anterior_codigo = 'EN_CAMINO';
UPDATE order_state_history SET estado_nuevo_codigo = 'TERMINADO' WHERE estado_nuevo_codigo = 'EN_CAMINO';
```

### Documentación
- `backend/README.md` línea 237 (enum del estado)
- Specs vivas afectadas

## Costo

~15-20 archivos tocados de forma mecánica. Tests del FSM deben actualizar los literales `"EN_CAMINO"` → `"TERMINADO"`.

La migración es idempotente y reversible (downgrade restaura `EN_CAMINO`).

## Diferencia con D4 (rename semántico de PENDIENTE)

En D4 se mantuvo el código `PENDIENTE` y se cambió la semántica de "esperando pago" a "esperando local". ¿Por qué acá sí renombramos?

- `PENDIENTE` es genérico: sostiene ambas semánticas ("esperando X")
- `EN_CAMINO` es específico: no sostiene "listo para retirar"

El costo de renombrar `PENDIENTE` → `RECIBIDO` era mayor que el costo de documentar. El costo de mantener `EN_CAMINO` para pickup era mayor que el rename.

## Referencias

- Spec: `openspec/specs/order-state-machine/spec.md`
- Migración: `backend/alembic/versions/20260518_0100_rename_en_camino_to_terminado.py`
- Implementación: `backend/features/orders/state_machine.py`
