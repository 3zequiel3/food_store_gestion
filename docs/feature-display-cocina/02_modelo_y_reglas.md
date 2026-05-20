# 02 — Modelo de datos, reglas de negocio y arquitectura de tiempo real (delta)

> **Leer antes:** `knowledge-base/04_modelo_de_datos.md`, `knowledge-base/05_reglas_de_negocio.md` (RN-FS),
> `knowledge-base/07_flujos_principales.md` (Flujo 5 — Avance de Estado FSM), `knowledge-base/08_arquitectura_propuesta.md`.

---

## A. Modelo de datos: ¿qué se agrega?

**Punto clave (y es un acierto, no una limitación): la versión v1 NO necesita tablas
nuevas.** El modelo actual ya tiene todo lo que el KDS consume. Reutilizar antes que
inventar.

| Necesidad del KDS | Cómo se resuelve con el modelo actual |
|-------------------|---------------------------------------|
| Listar pedidos a preparar | `Pedido` filtrado por `estado_codigo IN ('CONFIRMADO', 'EN_PREP')` |
| Mostrar los ítems de cada pedido | `DetallePedido` (`nombre_snapshot`, `cantidad`, `subtotal`) |
| Mostrar personalización ("sin cebolla") | `DetallePedido.personalizacion` (IDs de ingredientes excluidos) |
| Notas del cliente | `Pedido.notas` |
| **Timer de urgencia** (cuánto hace que espera) | `HistorialEstadoPedido.created_at` del registro `estado_hasta = CONFIRMADO` → es el momento en que el pedido entró a la cola de cocina |
| Marcar producto sin stock | `Producto.disponible` (BOOLEAN ya existente) |

> **No agregues columnas ni tablas "por las dudas".** Si justificás una necesidad real
> (ej. una nota interna de cocina distinta de la nota del cliente), podés proponer un
> campo `Pedido.nota_cocina TEXT NULL`. Pero arrancá sin él. Toda dependencia nueva se
> justifica en el `proposal.md` (regla dura del proyecto).

### Nota sobre el código de estado

Recordá la distinción ya documentada en la KB: el **código en BD** es `EN_PREP`
(`EstadoPedido.codigo VARCHAR(20)`), y el **nombre display** es `"En Preparación"`
(`EstadoPedido.nombre`). El KDS muestra el `nombre`; el FSM y los filtros usan el `codigo`.

---

## B. Reglas de negocio (nuevas) — prefijo `RN-CO`

| ID | Regla |
|----|-------|
| **RN-CO01** | La cocina **solo ve** pedidos en estado `CONFIRMADO` y `EN_PREP`. Un pedido en `PENDIENTE` (sin pago aprobado) **no aparece** en el KDS. |
| **RN-CO02** | El KDS lista los pedidos **ordenados por antigüedad ascendente** (el que entró primero a `CONFIRMADO`, primero), usando el `created_at` del historial de entrada a cocina. |
| **RN-CO03** | El rol `COCINA` solo puede ejecutar las transiciones `CONFIRMADO → EN_PREP` y `EN_PREP → EN_CAMINO`. Cualquier otra transición solicitada por un cocinero retorna **403**, aunque el endpoint le permita el acceso. La validación es en el servicio del FSM, no solo en el `require_role`. |
| **RN-CO04** | Todo avance de estado ejecutado por la cocina se registra en `HistorialEstadoPedido` (append-only) con `usuario_id` = el cocinero que lo ejecutó y `estado_desde`/`estado_hasta` correspondientes (consistente con RN-FS07). |
| **RN-CO05** | Cuando un pedido pasa a `CONFIRMADO` (por aprobación de pago), el backend **emite un evento en tiempo real** hacia las pantallas de cocina conectadas (ver §D). Si no hay ninguna conectada, el evento se descarta sin error (best-effort en v1 single-instance). |
| **RN-CO06** | Cuando un pedido sale de la fase de cocina (pasa a `EN_CAMINO`) o es **cancelado**, el backend emite el evento correspondiente para que el KDS **retire** ese pedido de la pantalla. |
| **RN-CO07** | **Urgencia por tiempo**: el KDS resalta visualmente los pedidos según el tiempo transcurrido desde su entrada a cocina. Umbrales sugeridos: **< 10 min** normal, **10–20 min** advertencia (naranja), **> 20 min** urgente (rojo). El timer se recalcula en el cliente cada 15 s. |
| **RN-CO08** | *(Opcional, US-COCINA-07)* La cocina puede marcar `Producto.disponible = false`. Esto **no** modifica `stock_cantidad` (eso es de `STOCK`): es un apagado temporal de disponibilidad. El catálogo público deja de ofrecer el producto. |

> **Importante:** estas reglas **no contradicen** ninguna RN existente. RN-CO03 y RN-CO04
> son refinamientos de RN-FS01 / RN-FS07 para el nuevo rol. RN-CO08 reutiliza el campo
> `disponible` ya documentado en `04_modelo_de_datos.md`.

---

## C. Delta del FSM (autorización por transición)

El FSM **no cambia de forma** (mismos 6 estados, mismas transiciones válidas). Lo que
cambia es **quién puede ejecutar** cada transición. Tabla actualizada (🆕 = celda nueva):

| Desde | Hacia | Roles autorizados |
|-------|-------|-------------------|
| `PENDIENTE` | `CONFIRMADO` | Sistema (auto, pago aprobado) |
| `PENDIENTE` | `CANCELADO` | Cliente / Pedidos / Admin |
| `CONFIRMADO` | `EN_PREP` | **Cocina** 🆕 / Pedidos / Admin |
| `CONFIRMADO` | `CANCELADO` | Pedidos / Admin (restaura stock) |
| `EN_PREP` | `EN_CAMINO` | **Cocina** 🆕 / Pedidos / Admin |
| `EN_PREP` | `CANCELADO` | **Solo Admin** (restaura stock) |
| `EN_CAMINO` | `ENTREGADO` | Pedidos / Admin (**cocina no**) |
| `ENTREGADO` | — (terminal) | — |
| `CANCELADO` | — (terminal) | — |

Diagrama de la **fase de cocina** dentro del FSM completo:

```
                                            ┌──────── fase de cocina ────────┐
PENDIENTE ──(pago)──> CONFIRMADO ──[COCINA]──> EN_PREP ──[COCINA]──> EN_CAMINO ──[PEDIDOS]──> ENTREGADO
                          │                       │
                          │                       └──[ADMIN]──> CANCELADO
                          └──[PEDIDOS/ADMIN]──> CANCELADO
```

---

## D. Arquitectura de tiempo real (la parte nueva de infra)

Food Store hoy es REST puro. Esta feature **agrega una capa de push**. Diseño de
referencia para la v1 **single-instance**:

### Backend (FastAPI)

1. **Endpoint WebSocket** `WS /api/v1/cocina/ws?token=<JWT>`:
   - Valida el JWT en el handshake; rechaza si no tiene rol `COCINA`/`PEDIDOS`/`ADMIN`.
   - Registra la conexión en un **gestor de conexiones en proceso** (un `set` de
     WebSockets activos, protegido para concurrencia con `asyncio`).
2. **Publicación de eventos**: dentro del servicio del FSM (el mismo que ya hace
   `avanzar_estado` en el Flujo 5), después de commitear la transición en la UoW, se
   publica un evento a las conexiones activas. Eventos definidos:

   | Evento | Se dispara cuando | Efecto en el KDS |
   |--------|-------------------|------------------|
   | `PEDIDO_CONFIRMADO` | `PENDIENTE → CONFIRMADO` (pago aprobado) | Aparece una tarjeta nueva en "Por preparar" |
   | `PEDIDO_EN_PREPARACION` | `CONFIRMADO → EN_PREP` | La tarjeta se mueve a "En preparación" |
   | `PEDIDO_EN_CAMINO` | `EN_PREP → EN_CAMINO` | La tarjeta **desaparece** del KDS |
   | `PEDIDO_CANCELADO` | cualquier `→ CANCELADO` en fase de cocina | La tarjeta **desaparece** del KDS |

3. **Endpoint REST de respaldo** `GET /api/v1/cocina/pedidos`: devuelve la lista actual
   (`CONFIRMADO` + `EN_PREP`, ordenada por antigüedad). Lo usa el KDS para la **carga
   inicial** y como **fallback por polling** si el WebSocket se cae.

### Frontend (React + Vite, KDS en `/cocina`)

- Al montar: `GET /api/v1/cocina/pedidos` (estado inicial) y abre el WebSocket.
- Layout de **columnas por estado**: "Por preparar" (`CONFIRMADO`) y "En preparación"
  (`EN_PREP`). Cada tarjeta muestra: nº de pedido, ítems (`nombre_snapshot` × `cantidad`),
  exclusiones de `personalizacion`, `notas` del cliente y el **timer de urgencia**.
- Reacciona a los eventos del WebSocket para mover/agregar/quitar tarjetas sin recargar.
- **Resiliencia**: si el WebSocket se desconecta, muestra un indicador y activa **polling
  de `GET /api/v1/cocina/pedidos` cada 30 s**; al reconectar, vuelve al push.
- El timer (`RN-CO07`) se recalcula en el cliente cada 15 s con `setInterval`.

### Decisiones de infra que SÍ son tuyas (documentalas en `design.md`)

- **WebSocket vs SSE**: SSE es más simple para push unidireccional. Elegí y justificá.
- **Single vs multi-instancia**: la v1 en proceso solo funciona con **una** instancia del
  backend. Si vas a multi-instancia, necesitás un bus externo (Redis Pub/Sub). Dejalo como
  límite conocido si quedás en single-instance.
- **Alerta sonora / flash visual** al llegar `PEDIDO_CONFIRMADO`: opcional (US-COCINA-05),
  se hace con Web Audio API en el cliente, sin archivos externos.

---

## E. Pregunta abierta documentada — `PA-CO-01`

**¿Conviene un estado intermedio `LISTO` entre `EN_PREP` y `EN_CAMINO`?**

- **Decisión actual (v1):** **No.** La cocina marca `EN_PREP → EN_CAMINO` como señal de
  "terminado". Modelo simple, sin migración de catálogo de estados.
- **Cuándo reconsiderarlo:** si el negocio necesita distinguir "la comida está lista en el
  mostrador" de "el repartidor la retiró y salió". Ahí un estado `LISTO` (entre `EN_PREP`
  y `EN_CAMINO`) permitiría que cocina marque `EN_PREP → LISTO` y el despacho marque
  `LISTO → EN_CAMINO`. Implica: nuevo registro en `EstadoPedido` (seed + migración
  Alembic), actualizar el mapa de transiciones del FSM y la tabla de autorización.
- **Recomendación pedagógica:** dejalo para una v2. Si tu equipo quiere el desafío, es un
  buen ejercicio de evolución de esquema con Alembic + datos de catálogo.
