# Proposal: Display de Cocina (KDS) + Rol Cocinero

## Why

Food Store no tiene una pantalla dedicada para que la cocina vea, en tiempo real, los pedidos pagados que debe preparar: hoy esa operación está absorbida por el rol `PEDIDOS` sobre el listado genérico de pedidos, sin push ni vista de producción. El modelo de roles de la spec canónica (`docs/Integrador.txt` §4.2 + ERD + OBJ-03/OBJ-04) define **4 roles** — `ADMIN`, `STOCK`, `PEDIDOS`, `CLIENT` — como requisito de rúbrica, y no contempla un rol específico de cocina. Este change **agrega `COCINA` como 5º rol** (extensión documentada del feature pack, sin tocar los 4 existentes) e incorpora un Kitchen Display System (KDS) en tiempo real propio del rol cocinero.

## What Changes

### Rol COCINA (nuevo, 5º rol)
- Registro idempotente `Rol(codigo='COCINA', nombre='Cocinero')` en el seed (id 5, junto a los 4 existentes; el seed usa `ON CONFLICT DO NOTHING` sobre `id` con `descripcion`). Usuario de prueba `cocina@foodstore.com`.
- `COCINA` se **suma** (no reemplaza) en `TRANSITION_ROLES` a las transiciones de cocina `CONFIRMADO → EN_PREPARACION` y `EN_PREPARACION → TERMINADO`, junto a los `PEDIDOS`/`ADMIN` que ya las ejecutan. El resto de `TRANSITION_ROLES` queda exactamente igual.
- Autorización validada en el servicio del FSM (`validate_transition`), no solo en `require_role`: `COCINA` queda autorizado **únicamente** en esas 2 transiciones de cocina.
- Sin sub-estados internos de cocina: las 2 acciones del cocinero **son** esas 2 transiciones del FSM existente. No se agregan campos ni tablas nuevas.

### Re-introducción condicional de `EN_CAMINO` (**BREAKING** del catálogo de estados)
- Migración Alembic que **re-agrega** `EN_CAMINO` al catálogo `order_states` (revierte parcialmente `20260518_0100_rename_en_camino_to_terminado`).
- Flujo según tipo de entrega (lo decide la regla de negocio por `Pedido.direccion_entrega_id`, no el FSM puro):
  - **Envío** (`direccion_entrega_id NOT NULL`): `EN_PREPARACION → TERMINADO → EN_CAMINO → ENTREGADO`.
  - **Retiro** (`direccion_entrega_id IS NULL`): `EN_PREPARACION → TERMINADO → ENTREGADO`.
- `ALLOWED_TRANSITIONS`: `TERMINADO → {EN_CAMINO, ENTREGADO}`, `EN_CAMINO → {ENTREGADO}`. El despacho (`→ EN_CAMINO`, `→ ENTREGADO`) lo siguen ejecutando `PEDIDOS`/`ADMIN`, nunca la cocina.

### KDS en tiempo real (backend)
- `GET /api/v1/cocina/pedidos`: lista de pedidos en `CONFIRMADO` + `EN_PREPARACION`, ordenada por antigüedad de entrada a cocina. Carga inicial del KDS y fallback por polling.
- `WS /api/v1/cocina/ws?token=<JWT>`: WebSocket en proceso (mismo `main:app`, mismo puerto), JWT validado en el handshake, gestor de conexiones en memoria (`set` protegido con `asyncio`). **Sin Redis.**
- El servicio del FSM publica eventos a las conexiones activas tras commitear cada transición: `pedido_confirmado`, `pedido_en_preparacion`, `pedido_terminado`, `pedido_cancelado`.
- Auditoría: cada avance ejecutado por cocina queda en `HistorialEstadoPedido` (append-only) con el `cambiado_por_id` del cocinero.

### Alta de usuarios desde admin (nuevo)
- `POST /api/v1/admin/usuarios`: crear usuario con email, contraseña, datos personales y conjunto de roles. Hoy `admin_users` solo lista/edita; no crea.

### Frontend — vista exclusiva del cocinero
- Ruta `/cocina`: tablero Kanban con dos columnas, "Por preparar" (`CONFIRMADO`) y "En preparación" (`EN_PREPARACION`). Tarjetas con nº de pedido, ítems, exclusiones y notas; "Ver detalle" (producto + ingredientes); botón "Terminado".
- Timer de urgencia recalculado en cliente cada 15 s (RN-CO07): < 10 min normal, 10–20 min naranja, > 20 min rojo.
- Login `COCINA` → única vista `/cocina`, sin acceso al resto. Ruta excluida del auto-logout por inactividad.
- Resiliencia: indicador de "sin conexión en vivo" + polling de `GET /cocina/pedidos` cada 30 s si cae el WebSocket.
- Form de admin para crear usuarios con selector de los 3 roles más comunes: `ADMIN`, `CLIENT` (label "Cliente"), `COCINA` (label "Cocinero"). `STOCK` y `PEDIDOS` siguen existiendo y se asignan con el `PATCH /rol` ya existente.

## Capabilities

### New Capabilities
- `kitchen-display-backend`: endpoints REST (`GET /cocina/pedidos`) y WebSocket (`WS /cocina/ws`) del KDS, gestor de conexiones en proceso, publicación de eventos de cocina tras commit del FSM.
- `kitchen-display-frontend`: vista Kanban `/cocina`, suscripción al WebSocket con fallback por polling, timer de urgencia, alerta de pedido entrante y vista exclusiva del rol cocinero.
- `cocina-role-rbac`: rol `COCINA` (5º del catálogo) y su autorización por transición (`CONFIRMADO → EN_PREPARACION`, `EN_PREPARACION → TERMINADO`) validada en el servicio del FSM.
- `admin-create-user`: endpoint y formulario de alta de usuarios desde el panel de administración con selección de roles.

### Modified Capabilities
- `order-state-machine`: re-introducción de `EN_CAMINO` condicional al tipo de entrega; `COCINA` agregado a las transiciones de cocina en `TRANSITION_ROLES` (sin remover `PEDIDOS`/`ADMIN`); publicación de eventos de tiempo real tras cada transición commiteada.
- `admin-users`: incorpora el alta de usuarios (`POST`) además del listado y la edición ya existentes.
- `routing-guards`: guard de `/cocina` por rol `COCINA`/`ADMIN` y exclusión de la ruta del auto-logout por inactividad.

## Impact

- **Backend**:
  - `features/orders/state_machine.py` — agregar `EN_CAMINO` a `ALLOWED_TRANSITIONS`; sumar `COCINA` a las 2 transiciones de cocina en `TRANSITION_ROLES`; el resto sin cambios.
  - `features/orders/service.py` — regla de branching envío/retiro en `avanzar_estado`/`transicionar_pedido`; publicación de eventos en `transicionar_estado` tras commit. `_is_admin_view` no se toca (sigue contemplando `PEDIDOS`/`ADMIN`/`STOCK`).
  - Nuevo `features/cocina/` (router, service, schemas, gestor de conexiones WebSocket).
  - `features/admin_users/router.py` + `schemas.py` + `service.py` — `POST` crear usuario.
  - `scripts/seed.py` — agregar `COCINA` (id 5) y el usuario de prueba; los 4 roles existentes quedan igual.
  - Nueva migración Alembic — re-agregar `EN_CAMINO` al catálogo `order_states`.
  - `main.py` — registrar el router de cocina y el endpoint WebSocket.
  - Tests de integración en `backend/tests/` para las nuevas transiciones de `COCINA` y `EN_CAMINO`.
- **Frontend**:
  - Nuevo `frontend/src/features/cocina/` (página `/cocina`, hook de WebSocket, componentes Kanban, tarjeta, timer).
  - `frontend/src/router/AppRoute.tsx` y `frontend/src/router/guards/` — guard `/cocina` + exclusión de inactividad.
  - `frontend/src/features/admin/` — formulario de alta de usuarios con los 3 roles comunes.
  - `frontend/vite.config.ts` — `ws: true` en el proxy `/api` para el WebSocket en dev local.
- **Infra**: sin servicios nuevos. `backend/Procfile` y `docker-compose.yml` sin cambios (un solo proceso `uvicorn main:app`). Límite conocido: el push en proceso solo sirve con **una** instancia del backend.
- **Dependencias del roadmap** (`docs/CHANGES.md` #31): `auth-backend`, `order-state-machine-fsm`, `payment-mercadopago-backend`, `products-backend`, `admin-users-backend` — todas presentes en el código actual.
