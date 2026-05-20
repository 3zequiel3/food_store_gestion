# Design: Display de Cocina (KDS) + Rol Cocinero

## Context

Food Store es un e-commerce de delivery con backend FastAPI + SQLAlchemy 2.0 + Alembic + PostgreSQL (SQLite en tests) y frontend React 19 + Vite + TanStack Query/Table/Form + zustand. El backend es **REST puro**: no hay WebSockets ni Redis en `requirements.txt`. La operación de pedidos vive en `features/orders/` con un FSM centralizado (`state_machine.py`) y un servicio (`service.py`) que ejecuta las transiciones dentro de un Unit of Work.

Estado actual relevante al change:
- **Roles**: 4 en el catálogo (`ADMIN`=1, `STOCK`=2, `PEDIDOS`=3, `CLIENT`=4), mandados por la spec canónica `docs/Integrador.txt` §4.2 + ERD (línea 106) + objetivos OBJ-03/OBJ-04. Seed con IDs estables (`scripts/seed.py`, `ON CONFLICT DO NOTHING` sobre `index_elements=["id"]`, cada registro con `id`/`codigo`/`descripcion`).
- **FSM real** (`state_machine.py`): `PENDIENTE → CONFIRMADO → EN_PREPARACION → TERMINADO → ENTREGADO`, más cancelaciones granulares `CANCELADO`, `CANCELADO_ADMIN`, `CANCELADO_CLIENTE`. La migración `20260518_0100_rename_en_camino_to_terminado` renombró `EN_CAMINO → TERMINADO`, lo que de hecho ya resolvió la pregunta abierta PA-CO-01 del feature pack (`TERMINADO` = "comida lista, esperando despacho").
- **`TRANSITION_ROLES` actual**: las transiciones de pedidos las ejecutan `CLIENT`/`PEDIDOS`/`ADMIN` según corresponde; las de cocina (`CONFIRMADO → EN_PREPARACION`, `EN_PREPARACION → TERMINADO`) son `{PEDIDOS, ADMIN}`; el despacho/entrega (`TERMINADO → ENTREGADO`) es `{PEDIDOS, ADMIN}`.
- **El feature pack `docs/feature-display-cocina/` fue escrito contra un FSM viejo** y usa los códigos `EN_PREP` y `EN_CAMINO`. Toda referencia se traduce: `EN_PREP → EN_PREPARACION`, y la "señal de cocina terminó" es `EN_PREPARACION → TERMINADO` (no `EN_CAMINO`).
- **Avance de estado** (`OrderService.avanzar_estado` / `transicionar_pedido`): valida FSM + RBAC + ownership en una sesión read-only y luego delega a `transicionar_estado`, que abre su propia UoW con `FOR UPDATE`, aplica efectos de stock y appendea `HistorialEstadoPedido`. El commit ocurre en el `__exit__` de la UoW.
- **`admin_users`** expone GET (listado), PUT (datos), PATCH `/rol`, PATCH `/estado`. **No crea usuarios.**
- **Frontend**: feature-sliced (`frontend/src/features/<feature>/`), guards en `frontend/src/router/guards/` (`PrivateRoute` lee `useAuthStore`). No existe lógica de auto-logout por inactividad todavía.

Las decisiones de alcance fueron **cerradas con el usuario el 2026-05-20** (engram `sdd/c-11-display-cocina/design-decisions`, obs #3270). La consolidación de roles 5→3 que se había considerado quedó **CANCELADA**: la spec canónica mandata 4 roles y los `.txt` ganan sobre cualquier `.md`. Este documento traduce las decisiones corregidas a arquitectura; no las reabre.

## Goals / Non-Goals

**Goals:**
- Agregar `COCINA` como 5º rol del catálogo, sin tocar los 4 roles existentes ni el FSM/auditoría existentes.
- Dar a la cocina una vista en tiempo real (KDS) de los pedidos a preparar, alimentada por push y resiliente a la caída del canal.
- Autorizar a `COCINA` exactamente en las 2 transiciones de cocina, validado en el dominio (FSM), no solo en el borde HTTP, sumándolo a los roles que ya las ejecutan.
- Re-introducir `EN_CAMINO` para que el despacho de envíos a domicilio tenga un estado propio, sin afectar el flujo de retiro en local.
- Permitir al admin dar de alta usuarios con rol.

**Non-Goals:**
- Consolidar, eliminar o reasignar los roles existentes (`ADMIN`/`STOCK`/`PEDIDOS`/`CLIENT`): la spec los mandata y se mantienen intactos.
- Multi-instancia del backend (el push es en proceso; multi-instancia queda como límite documentado).
- Tablas o columnas nuevas en el modelo de pedidos (el modelo actual cubre el KDS).
- Sub-estados internos de cocina (`cocina_estado`) o un estado `LISTO` separado: `TERMINADO` ya cumple esa función.
- Estaciones de cocina, multi-sucursal, mesas/rondas/mozo (descartados en el feature pack).
- Refund flow, suscripciones u otros proveedores de pago.
- Reemplazar el outbox/Redis Streams: la v1 usa pub/sub en proceso, best-effort.

## Decisions

### D1 — Rol COCINA como 5º registro de catálogo idempotente (no consolidación)
Los 4 roles de la spec (`ADMIN`/`STOCK`/`PEDIDOS`/`CLIENT`) se **mantienen intactos**. `COCINA` se **agrega** como 5º rol: `Rol(codigo='COCINA', ...)` insertado en el seed con `ON CONFLICT DO NOTHING`. La relación usuario↔rol sigue siendo N:M vía `UsuarioRol`. Usuario de prueba: `cocina@foodstore.com`.

> **Nota de implementación detectada en el código real**: el seed actual hace el `ON CONFLICT` sobre `index_elements=["id"]` con IDs fijos (1–4) y cada registro lleva `id`/`codigo`/`descripcion` (no `nombre`). El nuevo rol `COCINA` toma el id 5 con `descripcion="Cocinero"` (o equivalente). No se borra ni reasigna ningún id existente.

**Alternativa considerada**: consolidar a 3 roles (borrar `STOCK`/`PEDIDOS`, que `ADMIN` los absorba). **Descartada**: `docs/Integrador.txt` §4.2, el ERD (línea 106) y OBJ-03/OBJ-04 mandatan los 4 roles como requisito de rúbrica. Borrarlos contradiría la spec canónica, que gana sobre cualquier `.md`. El change solo **suma** `COCINA` — blast radius mucho menor: no toca los ~26 endpoints de catálogo ni saca `PEDIDOS` del FSM.

### D2 — Sin migración de re-mapeo de roles
Como no se borra ni reasigna ningún rol existente, **no hay migración de datos de roles**. La única migración del change es la de `EN_CAMINO` (D4). El seed solo agrega `COCINA` (idempotente).

### D3 — Autorización de COCINA en el FSM, no solo en el borde HTTP
El endpoint de avance de estado y el de cocina permiten el acceso a `COCINA`/`ADMIN` vía `require_role`, pero **qué transición** puede hacer cada rol vive en `validate_transition` (`state_machine.py`). `COCINA` se **agrega** (sin remover los roles ya presentes) a `TRANSITION_ROLES` solo en:
- `("CONFIRMADO", "EN_PREPARACION")`: de `{PEDIDOS, ADMIN}` a `{PEDIDOS, ADMIN, COCINA}`
- `("EN_PREPARACION", "TERMINADO")`: de `{PEDIDOS, ADMIN}` a `{PEDIDOS, ADMIN, COCINA}`

El resto de `TRANSITION_ROLES` queda exactamente como está hoy (`PEDIDOS` sigue en todas sus transiciones, incluido el despacho). Cualquier otra transición pedida por un cocinero (p. ej. `TERMINADO → EN_CAMINO`, `→ ENTREGADO`, cualquier `CANCELADO_*`) devuelve **403** porque `COCINA` no está en su `TRANSITION_ROLES`. Esto cumple RN-CO03 con doble defensa (borde + dominio).

**Alternativa considerada**: chequear el rol solo en `require_role`. Descartada: dejaría a un cocinero ejecutar despacho/cancelación si llega al endpoint genérico de transición. El dominio debe ser la autoridad.

### D4 — `EN_CAMINO` re-introducido, branching por tipo de entrega (no por el FSM puro)
La migración Alembic re-agrega `EN_CAMINO` al catálogo `order_states` (revierte parcialmente `20260518_0100`). El FSM permite ambas salidas desde `TERMINADO`:
- `ALLOWED_TRANSITIONS["TERMINADO"] = {"EN_CAMINO", "ENTREGADO", "CANCELADO_ADMIN"}`
- `ALLOWED_TRANSITIONS["EN_CAMINO"] = {"ENTREGADO"}`
- `TRANSITION_ROLES`: `("TERMINADO","EN_CAMINO") = {PEDIDOS, ADMIN}`, `("EN_CAMINO","ENTREGADO") = {PEDIDOS, ADMIN}`, `("TERMINADO","ENTREGADO") = {PEDIDOS, ADMIN}` (mantiene los roles de despacho/entrega ya existentes).

**Qué salida es válida la decide una regla de negocio en el servicio**, no el FSM puro:
- **Envío** (`Pedido.direccion_entrega_id NOT NULL`): el camino correcto es `TERMINADO → EN_CAMINO → ENTREGADO`. Saltar `TERMINADO → ENTREGADO` directo se rechaza con `BusinessRuleError`.
- **Retiro** (`direccion_entrega_id IS NULL`): no hay reparto; `TERMINADO → ENTREGADO` es directo y `→ EN_CAMINO` se rechaza.

El despacho y la entrega son **siempre de `PEDIDOS`/`ADMIN`** (los roles que ya los ejecutan); la cocina nunca toca `EN_CAMINO` ni `ENTREGADO`.

**Alternativa considerada**: dejar el branching dentro de `ALLOWED_TRANSITIONS`. Descartada: `ALLOWED_TRANSITIONS` no conoce el `Pedido` concreto (es un mapa estático de códigos). La condición "tiene dirección de envío" es dato de instancia → vive en el servicio, que sí carga el `Pedido`.

### D5 — Tiempo real = WebSocket en proceso (no SSE), single-instance
- **Endpoint** `WS /api/v1/cocina/ws?token=<JWT>` en el mismo `main:app` y mismo puerto (`8000` local, `$PORT` en prod vía `Procfile`).
- **Auth en el handshake**: el JWT se valida en el `accept` del WebSocket (no solo en REST). Si falta o no tiene rol `COCINA`/`ADMIN`, se cierra la conexión (close code 1008 / rechazo).
- **Gestor de conexiones en memoria**: un módulo singleton mantiene un `set` de WebSockets activos, con accesos protegidos por `asyncio.Lock`. `connect`, `disconnect`, `broadcast(event)`.
- **Publicación**: el servicio del FSM, **después** de commitear la transición en la UoW (no antes), publica el evento correspondiente. Como `transicionar_estado` es sync y corre en un threadpool, el broadcast se encola hacia el event loop (`asyncio.run_coroutine_threadsafe` o una cola asíncrona consumida por una task del loop). Si no hay conexiones, el evento se descarta sin error (best-effort, RN-CO05).
- **Eventos** (léxico snake_case): `pedido_confirmado`, `pedido_en_preparacion`, `pedido_terminado`, `pedido_cancelado`. `pedido_cancelado` cubre cualquier `→ CANCELADO`/`CANCELADO_ADMIN`/`CANCELADO_CLIENTE` que ocurra mientras el pedido está en fase de cocina, para que el KDS retire la tarjeta.
- **Payload**: el evento lleva el snapshot mínimo del pedido que el KDS necesita para mover/agregar/quitar una tarjeta (id, estado, ítems, notas, timestamp de entrada a cocina).

**Alternativa considerada — SSE**: el feature pack lo sugiere como más simple para push unidireccional. **Descartada por decisión explícita del usuario**: se eligió WebSocket. El tradeoff (SSE sería más simple para un solo sentido) queda registrado pero la decisión está cerrada.

**Límite conocido (a documentar y aceptar)**: el pub/sub en proceso solo funciona con **una** instancia del backend. Con múltiples instancias, un evento publicado en la instancia A no llega a la pantalla conectada a la instancia B. Multi-instancia requeriría un bus externo (Redis Pub/Sub). El feature pack respalda esto (README.md:49-50, 118). En prod single-instance (Procfile, un `uvicorn`) es correcto.

### D6 — Endpoint REST de respaldo + carga inicial
`GET /api/v1/cocina/pedidos` devuelve `CONFIRMADO` + `EN_PREPARACION` ordenados por antigüedad de entrada a cocina (RN-CO02). El "tiempo de entrada a cocina" es el `creado_en` del `HistorialEstadoPedido` cuyo `estado_nuevo_codigo = CONFIRMADO`. Lo usa el frontend para la carga inicial y como fallback por polling cuando el WS está caído. Idempotente y consistente con el push: al reconectar, un fetch completo re-sincroniza (la v1 no guarda eventos perdidos).

### D7 — Vista exclusiva del cocinero en frontend
- Ruta `/cocina` protegida por un guard de rol (`COCINA`/`ADMIN`). Login `COCINA` redirige a `/cocina` como única vista; el resto del shell no se le muestra.
- Tablero Kanban de 2 columnas (`CONFIRMADO` = "Por preparar", `EN_PREPARACION` = "En preparación"). Tarjeta: nº de pedido, ítems (`nombre_snapshot` × `cantidad`), exclusiones de `personalizacion`, `notas`. "Ver detalle" abre producto + ingredientes. Botón "Terminado" ejecuta `EN_PREPARACION → TERMINADO`.
- Timer de urgencia recalculado en cliente cada 15 s desde el timestamp de entrada a `CONFIRMADO`: < 10 min normal, 10–20 min naranja, > 20 min rojo (RN-CO07).
- **Auto-logout por inactividad**: hoy no existe en el código. Se diseña como parte de esta feature de modo que `/cocina` quede **excluida** del temporizador (la pantalla vive encendida durante el turno). El guard/efecto de inactividad ignora la ruta `/cocina`.
- Resiliencia: si el WS se desconecta, indicador de "sin conexión en vivo" + polling de `GET /cocina/pedidos` cada 30 s; al reconectar vuelve al push y refresca.
- Datos por TanStack Query (carga inicial + polling de fallback); el WS empuja invalidaciones/eventos al cache.

### D8 — Alta de usuarios desde admin
`POST /api/v1/admin/usuarios` (require `ADMIN`): email, contraseña, nombre, apellido, teléfono opcional, lista de roles (`min_length=1`, `extra="forbid"`). Reutiliza el hashing y la validación de unicidad de email del registro existente. El form de admin ofrece los 3 roles más comunes con labels en español: `ADMIN` ("Admin"), `CLIENT` ("Cliente") y `COCINA` ("Cocinero"); los códigos que viajan al backend son `ADMIN`/`CLIENT`/`COCINA` (RN-71: léxico de código en mayúsculas para códigos de catálogo; labels UI en español). Los roles `STOCK` y `PEDIDOS` siguen existiendo y se asignan con el `PATCH /rol` ya existente (no por este formulario de alta), evitando saturar el form con los 5 roles.

## Risks / Trade-offs

- **[Push en proceso solo sirve single-instance]** → Documentado como límite conocido (D5). Prod corre un único `uvicorn` (Procfile). Si se escala horizontalmente, se necesita Redis Pub/Sub; queda como evolución, no como deuda silenciosa.
- **[Broadcast desde código sync hacia el event loop async]** → `transicionar_estado` es sync (corre en threadpool de FastAPI). Mitigación: encolar el evento hacia el loop con `run_coroutine_threadsafe` o una `asyncio.Queue` drenada por una task; nunca bloquear el commit de la UoW por el broadcast. El broadcast es **post-commit** y best-effort: si falla, no revierte la transición.
- **[`COCINA` con acceso al endpoint genérico de transición podría intentar despachar]** → Mitigado por D3: el RBAC por transición en el dominio rechaza con 403 cualquier transición fuera de las 2 de cocina.
- **[Salto de estado inválido por tipo de entrega]** → La regla de envío/retiro (D4) vive en el servicio y rechaza `TERMINADO → ENTREGADO` directo en envíos y `TERMINADO → EN_CAMINO` en retiros. Tests cubren ambas ramas.
- **[Autoplay de audio bloqueado por el navegador]** (alerta sonora, US-COCINA-05, opcional) → El beep (Web Audio API) requiere interacción previa del usuario; se documenta el límite y se ofrece toggle persistente en `localStorage`.
- **[Eventos perdidos durante una desconexión del WS]** → La v1 no los recupera; el fallback por polling y el fetch completo al reconectar re-sincronizan el estado (D6).
- **[SQLite en tests no soporta `ARRAY(Integer)` de `personalizacion`]** → Ya manejado en el código real (`OperationalError` → items vacíos). Los tests de integración del KDS le pegan a PostgreSQL real; el WebSocket se testea con el `TestClient` de FastAPI.

## Migration Plan

1. **Slice 1 (rol COCINA)**: el seed agrega `COCINA` (id 5) idempotentemente + usuario `cocina@foodstore.com`; se suma `COCINA` a las 2 transiciones de cocina en `TRANSITION_ROLES` (sin remover roles existentes). Sin migración de datos. Rollback: quitar `COCINA` del seed y de `TRANSITION_ROLES`.
2. **Slice 2 (EN_CAMINO condicional)**: migración Alembic re-agrega `EN_CAMINO` al catálogo `order_states` (con su `orden` entre `TERMINADO` y `ENTREGADO`, `es_terminal=False`); `ALLOWED_TRANSITIONS` y la regla de branching envío/retiro en el servicio. Rollback: `downgrade` elimina `EN_CAMINO` (solo seguro si no hay pedidos en ese estado).
3. **Slice 3 (backend KDS + WS)**: router `features/cocina/`, gestor de conexiones, publicación de eventos post-commit; registro en `main.py`. Sin migración de datos.
4. **Slice 4 (alta de usuarios admin)**: `POST` en `admin_users`. Sin migración.
5. **Slice 5 (frontend Kanban)**: feature `frontend/src/features/cocina/`, guard de ruta, exclusión de inactividad, `ws: true` en el proxy de Vite. Sin migración.

> Tamaño estimado > 400 líneas → **candidato a PRs encadenados**, una por slice, en el orden anterior.

## Open Questions

- **US-COCINA-07 (cocina marca producto no disponible)**: opcional, prioridad baja, y solapa con la responsabilidad de stock del rol `STOCK`. Recomendación: **dejarla fuera de la v1** y documentarla como evolución. Si el usuario la quiere dentro, se agrega un endpoint `PATCH /cocina/productos/{id}/disponibilidad` sin tocar `stock_cantidad` (RN-CO08).
