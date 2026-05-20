# Tasks: Display de Cocina (KDS) + Rol Cocinero

> **Strict TDD**: cada tarea de implementación va precedida por su test (los tests primero, en rojo, luego el código que los pone en verde). Los tests de integración del backend le pegan a PostgreSQL real (sin mockear la DB); el WebSocket se testea con el `TestClient` de FastAPI. Frontend con vitest (`pnpm test`).
>
> **Tamaño**: el change supera con holgura las 400 líneas → **candidato a PRs encadenados**, una por slice.
>
> **Importante**: los 4 roles de la spec (`ADMIN`/`STOCK`/`PEDIDOS`/`CLIENT`) se mantienen intactos. Este change solo **agrega** `COCINA` como 5º rol. No se borra ni reasigna ningún rol existente.

## 1. Slice 1 — Agregar rol COCINA (seed + FSM RBAC)

- [ ] 1.1 Test (rojo): el seed inserta `Rol(codigo='COCINA')` (id 5) idempotentemente y un usuario `cocina@foodstore.com` con ese rol; re-ejecutar no duplica; los 4 roles existentes siguen presentes.
- [ ] 1.2 Agregar `COCINA` (id 5, `descripcion="Cocinero"`) y el usuario de prueba al seed (`scripts/seed.py`, `ON CONFLICT DO NOTHING` sobre `index_elements=["id"]`); no tocar los registros 1–4.
- [ ] 1.3 Test (rojo): `validate_transition` autoriza `{COCINA}` en `CONFIRMADO→EN_PREPARACION` y `EN_PREPARACION→TERMINADO`, sigue autorizando `{PEDIDOS}`/`{ADMIN}` en esas transiciones, y rechaza con 403 a `{COCINA}` en `TERMINADO→EN_CAMINO`, `→ENTREGADO` y cancelaciones.
- [ ] 1.4 Sumar `COCINA` a `TRANSITION_ROLES` solo en las 2 transiciones de cocina (`("CONFIRMADO","EN_PREPARACION")` y `("EN_PREPARACION","TERMINADO")`), sin remover `PEDIDOS`/`ADMIN`. El resto de `TRANSITION_ROLES` queda exactamente igual.
- [ ] 1.5 Correr la suite de backend; confirmar verde.

## 2. Slice 2 — EN_CAMINO condicional al tipo de entrega (migración + FSM)

- [ ] 2.1 Test (rojo): migración Alembic re-agrega `EN_CAMINO` al catálogo `order_states` (`es_terminal=False`, orden entre `TERMINADO` y `ENTREGADO`); `downgrade` lo elimina si no hay pedidos en ese estado.
- [ ] 2.2 Crear la migración Alembic que re-introduce `EN_CAMINO` (revierte parcialmente `20260518_0100`).
- [ ] 2.3 Test (rojo): `ALLOWED_TRANSITIONS` tiene `TERMINADO→{EN_CAMINO,ENTREGADO,CANCELADO_ADMIN}` y `EN_CAMINO→{ENTREGADO}`; `TRANSITION_ROLES` de despacho/entrega mantiene `{PEDIDOS, ADMIN}`.
- [ ] 2.4 Actualizar `ALLOWED_TRANSITIONS` y `TRANSITION_ROLES` en `state_machine.py` con `EN_CAMINO` (despacho/entrega siguen siendo `{PEDIDOS, ADMIN}`).
- [ ] 2.5 Test (rojo): branching por tipo de entrega — envío (`direccion_entrega_id NOT NULL`) rechaza `TERMINADO→ENTREGADO` directo con 422; retiro (`IS NULL`) rechaza `TERMINADO→EN_CAMINO` con 422.
- [ ] 2.6 Implementar la regla de branching en `OrderService` (en `avanzar_estado`/`transicionar_pedido`, que ya cargan el `Pedido`).
- [ ] 2.7 Actualizar el `Literal` de `nuevo_estado` en los schemas de pedidos para aceptar `EN_CAMINO`.
- [ ] 2.8 Correr la suite de backend; confirmar verde.

## 3. Slice 3 — Backend KDS (REST + WebSocket en proceso + auditoría de eventos)

- [ ] 3.1 Test (rojo): `GET /api/v1/cocina/pedidos` con `COCINA` devuelve solo `CONFIRMADO`+`EN_PREPARACION` ordenados por antigüedad de entrada a cocina; excluye `PENDIENTE`; 403 para `CLIENT`.
- [ ] 3.2 Crear `backend/features/cocina/` (router, service, schemas) y el endpoint `GET /cocina/pedidos` (orden por `creado_en` del historial de entrada a `CONFIRMADO`, RN-CO02).
- [ ] 3.3 Test (rojo): gestor de conexiones en proceso — registra, desregistra al cerrar, y `broadcast` sin conexiones no falla.
- [ ] 3.4 Implementar el gestor de conexiones WebSocket en memoria (`set` + `asyncio.Lock`, `connect`/`disconnect`/`broadcast`).
- [ ] 3.5 Test (rojo, con `TestClient`): `WS /api/v1/cocina/ws` rechaza handshake sin token y con rol `CLIENT`; acepta con `COCINA`/`ADMIN`.
- [ ] 3.6 Implementar el endpoint WebSocket con validación de JWT y rol en el handshake.
- [ ] 3.7 Test (rojo): tras una transición commiteada, se publica el evento correcto (`pedido_confirmado`, `pedido_en_preparacion`, `pedido_terminado`, `pedido_cancelado`); el fallo del broadcast no revierte la transición.
- [ ] 3.8 Publicar eventos post-commit desde el servicio del FSM (encolar hacia el event loop; best-effort).
- [ ] 3.9 Test (rojo): un avance de cocina queda en `HistorialEstadoPedido` con `cambiado_por_id` del cocinero (append-only, sin UPDATE/DELETE).
- [ ] 3.10 Verificar/ajustar la auditoría existente para el actor cocinero (reutiliza `create_historial_transicion`).
- [ ] 3.11 Registrar el router de cocina y el endpoint WebSocket en `backend/main.py`.
- [ ] 3.12 Correr la suite de backend; confirmar verde.

## 4. Slice 4 — Alta de usuarios desde admin (POST nuevo)

- [ ] 4.1 Test (rojo): `POST /api/v1/admin/usuarios` crea usuario con roles; 201 con `AdminUserResponse` sin `password_hash`; password hasheada con bcrypt.
- [ ] 4.2 Test (rojo): email duplicado → 409; rol inexistente → 422; `roles=[]` → 422; sin `ADMIN` → 403.
- [ ] 4.3 Agregar `AdminCreateUserRequest` (email, password, nombre, apellido, telefono opcional, roles `min_length=1`, `extra="forbid"`) en `backend/features/admin_users/schemas.py`.
- [ ] 4.4 Implementar `create_usuario` en `AdminUserService` (hashing, unicidad de email, validación de códigos de rol) dentro de UoW.
- [ ] 4.5 Agregar el endpoint `POST` en `backend/features/admin_users/router.py` con `require_role("ADMIN")`.
- [ ] 4.6 Correr la suite de backend; confirmar verde.

## 5. Slice 5 — Frontend Kanban /cocina (vista exclusiva del cocinero)

- [ ] 5.1 Test (rojo): guard de `/cocina` permite `COCINA`/`ADMIN` y bloquea `CLIENT` (403); login `COCINA` redirige a `/cocina`.
- [ ] 5.2 Crear la ruta `/cocina` y su guard de rol en `frontend/src/router/` (AppRoute + guards); redirect de login para `COCINA`.
- [ ] 5.3 Test (rojo): exclusión de `/cocina` del auto-logout por inactividad; otras rutas siguen disparándolo.
- [ ] 5.4 Implementar el efecto/hook de auto-logout por inactividad excluyendo `/cocina`.
- [ ] 5.5 Test (rojo): el cliente API expone `GET /api/v1/cocina/pedidos` y el hook de WebSocket; agregar `ws: true` al proxy `/api` en `frontend/vite.config.ts`.
- [ ] 5.6 Crear `frontend/src/features/cocina/` (api client, hook de WebSocket con TanStack Query para carga inicial + cache).
- [ ] 5.7 Test (rojo): el tablero renderiza 2 columnas (CONFIRMADO/EN_PREPARACION), tarjeta con ítems/exclusiones/notas, "Ver detalle" con producto+ingredientes.
- [ ] 5.8 Implementar el tablero Kanban y la tarjeta de pedido.
- [ ] 5.9 Test (rojo): acciones "Iniciar preparación" (CONFIRMADO→EN_PREPARACION) y "Terminado" (EN_PREPARACION→TERMINADO) mueven/retiran la tarjeta.
- [ ] 5.10 Implementar las acciones de avance contra el endpoint de transición.
- [ ] 5.11 Test (rojo): eventos del WebSocket agregan/mueven/retiran tarjetas sin recargar (`pedido_confirmado`/`pedido_en_preparacion`/`pedido_terminado`/`pedido_cancelado`).
- [ ] 5.12 Conectar los eventos del WebSocket al estado del tablero.
- [ ] 5.13 Test (rojo): al caer el WS, indicador "sin conexión en vivo" + polling cada 30 s; al reconectar, vuelve al push y refresca.
- [ ] 5.14 Implementar la resiliencia (indicador + polling de fallback + reconexión).
- [ ] 5.15 Test (rojo): timer de urgencia recalculado cada 15 s — normal (<10m), naranja (10-20m), rojo (>20m).
- [ ] 5.16 Implementar el timer de urgencia (cálculo en cliente desde el timestamp de entrada a cocina).
- [ ] 5.17 (Opcional, US-COCINA-05) Test + implementación de alerta sonora (Web Audio API) + flash visual con toggle persistente en `localStorage`.
- [ ] 5.18 Test (rojo): formulario de alta de usuarios con selector de 3 roles comunes (labels español, códigos `ADMIN`/`CLIENT`/`COCINA`); el alta crea el usuario.
- [ ] 5.19 Implementar el formulario de alta de usuarios en el panel de admin (TanStack Form). `STOCK`/`PEDIDOS` se siguen asignando con el `PATCH /rol` existente.
- [ ] 5.20 Correr `pnpm test`; confirmar verde.

## 6. Cierre

- [ ] 6.1 Correr backend (pytest) y frontend (`pnpm test`) completos; ambos en verde.
- [ ] 6.2 Verificar manualmente el flujo KDS end-to-end con una instancia: confirmar pedido → aparece en /cocina → iniciar → terminar → desaparece; despacho PEDIDOS/ADMIN según tipo de entrega.
- [ ] 6.3 Revisión humana del usuario antes de archivar (regla de oro: nunca archivar sin OK).
