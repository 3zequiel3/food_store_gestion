# 03 — Historias de Usuario: Display de Cocina (EPIC COCINA)

> **Leer antes:** `01_rol_cocinero.md` y `02_modelo_y_reglas.md` de este mismo paquete.
> Formato consistente con `docs/Historias_de_usuario.txt` del proyecto.
> Prefijo `US-COCINA-NN` para no colisionar con las US-000..US-076 existentes.

**Resumen de la épica:**

| Historia | Funcionalidad | Prioridad |
|----------|--------------|-----------|
| US-COCINA-01 | Ver pedidos a preparar en tiempo real (núcleo del KDS) | Alta |
| US-COCINA-02 | Tomar un pedido (marcar EN_PREPARACIÓN) | Alta |
| US-COCINA-03 | Marcar pedido terminado (EN_CAMINO) | Alta |
| US-COCINA-04 | Setup del rol COCINA y acceso al KDS | Alta |
| US-COCINA-05 | Alerta visual/sonora al llegar un pedido nuevo | Media |
| US-COCINA-06 | Indicador de urgencia por tiempo de espera | Media |
| US-COCINA-07 | Marcar producto como no disponible (opcional) | Baja |
| US-COCINA-08 | Resiliencia: fallback por polling si cae el WebSocket | Media |
| US-COCINA-09 | Auditoría de avances de estado hechos por cocina | Alta |

---

## US-COCINA-01: Ver pedidos a preparar en tiempo real

- **Título**: Pantalla de cocina (KDS) en tiempo real
- **Historia**: Como **Cocinero**, quiero ver en una pantalla todos los pedidos pagados que
  debo preparar, ordenados por antigüedad y actualizados en tiempo real, para saber qué
  cocinar y en qué orden sin tener que recargar.
- **Prioridad**: Alta
- **Dependencias**: US-COCINA-04, C-08 (pedidos), C-09 (pagos)

**Criterios de Aceptación**:
- [ ] GIVEN un cocinero autenticado, WHEN entra a `/cocina`, THEN ve dos columnas: "Por preparar" (`CONFIRMADO`) y "En preparación" (`EN_PREP`).
- [ ] Cada tarjeta muestra: número de pedido, ítems con `nombre_snapshot` y `cantidad`, exclusiones de `personalizacion`, y `notas` del cliente.
- [ ] Los pedidos se listan ordenados por antigüedad ascendente (RN-CO02).
- [ ] GIVEN un pago aprobado de otro pedido, WHEN el backend emite `PEDIDO_CONFIRMADO`, THEN aparece una tarjeta nueva en "Por preparar" **sin recargar** la página.
- [ ] GIVEN un pedido en `PENDIENTE`, THEN **NO** aparece en el KDS (RN-CO01).

**Reglas de Negocio**: RN-CO01, RN-CO02, RN-CO05.

**Notas Técnicas**:
- Carga inicial: `GET /api/v1/cocina/pedidos`. Tiempo real: `WS /api/v1/cocina/ws`.
- Tiempo de entrada a cocina = `created_at` del `HistorialEstadoPedido` con `estado_hasta = CONFIRMADO`.

---

## US-COCINA-02: Tomar un pedido

- **Título**: Iniciar preparación de un pedido
- **Historia**: Como **Cocinero**, quiero marcar un pedido como "en preparación" para indicar
  que empecé a cocinarlo y que el cliente vea el avance.
- **Prioridad**: Alta
- **Dependencias**: US-COCINA-01

**Criterios de Aceptación**:
- [ ] GIVEN un pedido en `CONFIRMADO`, WHEN el cocinero presiona "Iniciar preparación", THEN el pedido pasa a `EN_PREP`.
- [ ] La tarjeta se mueve de "Por preparar" a "En preparación" en todas las pantallas conectadas (evento `PEDIDO_EN_PREPARACION`).
- [ ] Se registra en `HistorialEstadoPedido` con el cocinero como `usuario_id` (RN-CO04, RN-FS07).
- [ ] GIVEN un pedido en cualquier otro estado, WHEN se intenta pasar a `EN_PREP`, THEN se rechaza con error de transición inválida (RN-FS01).

**Reglas de Negocio**: RN-CO03, RN-CO04, RN-FS01, RN-FS07.

**Notas Técnicas**:
- Endpoint: `PATCH /api/v1/pedidos/{id}/estado` con body `{ "nuevo_estado": "EN_PREP", "motivo": null }`.
- La autorización de la transición para rol `COCINA` se valida en el servicio del FSM (RN-CO03).

---

## US-COCINA-03: Marcar pedido terminado

- **Título**: Marcar pedido listo / despacho
- **Historia**: Como **Cocinero**, quiero marcar un pedido como terminado para sacarlo de mi
  pantalla y avisar que está listo para despacho/entrega.
- **Prioridad**: Alta
- **Dependencias**: US-COCINA-02

**Criterios de Aceptación**:
- [ ] GIVEN un pedido en `EN_PREP`, WHEN el cocinero presiona "Listo", THEN el pedido pasa a `EN_CAMINO`.
- [ ] La tarjeta **desaparece** del KDS en todas las pantallas conectadas (evento `PEDIDO_EN_CAMINO`, RN-CO06).
- [ ] Se registra en `HistorialEstadoPedido` (RN-CO04).
- [ ] La transición solo es válida desde `EN_PREP` (RN-FS01).

**Reglas de Negocio**: RN-CO03, RN-CO04, RN-CO06, RN-FS01.

**Notas Técnicas**:
- Endpoint: `PATCH /api/v1/pedidos/{id}/estado` con body `{ "nuevo_estado": "EN_CAMINO" }`.
- **Recordatorio de diseño (PA-CO-01):** en la v1 no hay estado `LISTO` separado; `EN_CAMINO` es la señal de "cocina terminó".

---

## US-COCINA-04: Setup del rol COCINA y acceso al KDS

- **Título**: Alta del rol Cocinero y guard de ruta
- **Historia**: Como **Administrador**, quiero que exista el rol `COCINA` y que solo los
  usuarios con ese rol (o PEDIDOS/ADMIN) accedan a la pantalla de cocina.
- **Prioridad**: Alta
- **Dependencias**: C-02 (auth, RBAC, `require_role`)

**Criterios de Aceptación**:
- [ ] GIVEN el seed de roles, THEN existe el registro `Rol(codigo='COCINA', nombre='Cocinero')` (idempotente, `ON CONFLICT DO NOTHING`).
- [ ] El admin puede asignar/quitar el rol `COCINA` a un usuario (reutiliza US-005).
- [ ] GIVEN un usuario sin rol `COCINA`/`PEDIDOS`/`ADMIN`, WHEN intenta `GET /api/v1/cocina/pedidos`, THEN recibe **403**.
- [ ] GIVEN un usuario sin token, WHEN abre el WebSocket, THEN el handshake se rechaza (**401**/cierre).
- [ ] El frontend muestra `/cocina` en la navegación solo para roles autorizados.
- [ ] La ruta `/cocina` queda excluida del auto-logout por inactividad.

**Reglas de Negocio**: RN-RB09, RN-RB10, RN-CO03.

**Notas Técnicas**:
- Agregar `COCINA` a `require_role` de los endpoints de cocina y de avance de estado.
- Validar el JWT también en el handshake del WebSocket (no solo en REST).

---

## US-COCINA-05: Alerta al llegar un pedido nuevo

- **Título**: Aviso visual y sonoro de pedido entrante
- **Historia**: Como **Cocinero**, quiero un aviso (sonido + flash) al llegar un pedido nuevo,
  para no tener que mirar la pantalla todo el tiempo.
- **Prioridad**: Media
- **Dependencias**: US-COCINA-01

**Criterios de Aceptación**:
- [ ] WHEN el KDS recibe `PEDIDO_CONFIRMADO`, THEN reproduce un beep (Web Audio API, sin archivos externos) y hace un flash visual breve.
- [ ] Hay un toggle de sonido ON/OFF visible que persiste entre sesiones (`localStorage`).

**Reglas de Negocio**: RN-CO05.

**Notas Técnicas**:
- El sonido requiere una interacción previa del usuario con la página (política de autoplay del navegador). Documentar este límite.

---

## US-COCINA-06: Indicador de urgencia por tiempo

- **Título**: Resaltado de pedidos demorados
- **Historia**: Como **Cocinero**, quiero que los pedidos que llevan mucho tiempo esperando se
  destaquen, para priorizar los más urgentes.
- **Prioridad**: Media
- **Dependencias**: US-COCINA-01

**Criterios de Aceptación**:
- [ ] Cada tarjeta muestra el tiempo transcurrido desde su entrada a `CONFIRMADO`.
- [ ] < 10 min: estilo normal. 10–20 min: advertencia (naranja). > 20 min: urgente (rojo).
- [ ] El timer se recalcula en el cliente cada 15 s sin recargar.

**Reglas de Negocio**: RN-CO07.

**Notas Técnicas**:
- El cálculo es 100% en el cliente a partir del timestamp que envía el backend. Umbrales configurables.

---

## US-COCINA-07: Marcar producto como no disponible (opcional)

- **Título**: Apagado temporal de disponibilidad por cocina
- **Historia**: Como **Cocinero**, quiero marcar un producto como agotado temporalmente cuando
  se me acaba un ingrediente, para que deje de ofrecerse en el catálogo.
- **Prioridad**: Baja
- **Dependencias**: US-COCINA-04, C-04 (productos)

**Criterios de Aceptación**:
- [ ] WHEN el cocinero marca un producto como no disponible, THEN `Producto.disponible = false`.
- [ ] Esto **no** modifica `stock_cantidad` (RN-CO08).
- [ ] El catálogo público (US-018) deja de ofrecer el producto / lo muestra como "no disponible".

**Reglas de Negocio**: RN-CO08.

**Notas Técnicas**:
- Endpoint sugerido: `PATCH /api/v1/cocina/productos/{id}/disponibilidad` con `{ "disponible": false }`.
- **Decisión a tomar:** este permiso solapa con `STOCK`. Si tu equipo prefiere no dárselo a cocina, dejá esta US fuera de la v1 y documentalo. Es perfectamente válido.

---

## US-COCINA-08: Resiliencia del KDS ante caída del WebSocket

- **Título**: Fallback por polling
- **Historia**: Como **Cocinero**, quiero que la pantalla siga funcionando aunque se corte la
  conexión en tiempo real, para no perder pedidos.
- **Prioridad**: Media
- **Dependencias**: US-COCINA-01

**Criterios de Aceptación**:
- [ ] GIVEN el WebSocket desconectado, THEN el KDS muestra un indicador de "sin conexión en vivo" y hace `GET /api/v1/cocina/pedidos` cada 30 s.
- [ ] WHEN el WebSocket reconecta, THEN vuelve al modo push y refresca el estado actual.

**Reglas de Negocio**: RN-CO05, RN-CO06.

**Notas Técnicas**:
- Al reconectar, hacer un fetch completo evita perder eventos ocurridos durante la desconexión (la v1 single-instance no guarda eventos perdidos).

---

## US-COCINA-09: Auditoría de avances de estado hechos por cocina

- **Título**: Trazabilidad de las acciones de cocina
- **Historia**: Como **Administrador**, quiero que cada avance de estado hecho por un cocinero
  quede auditado, para tener trazabilidad de quién preparó y despachó cada pedido.
- **Prioridad**: Alta
- **Dependencias**: US-COCINA-02, US-COCINA-03

**Criterios de Aceptación**:
- [ ] GIVEN una transición ejecutada por cocina, THEN se inserta un registro en `HistorialEstadoPedido` (append-only) con `estado_desde`, `estado_hasta`, `usuario_id` del cocinero y `created_at`.
- [ ] NUNCA se hace UPDATE ni DELETE sobre `HistorialEstadoPedido` (RN-FS07).

**Reglas de Negocio**: RN-CO04, RN-FS07, RN-FS09.

**Notas Técnicas**:
- Reutiliza el mismo `HistorialEstadoPedido` y el mismo flujo de auditoría del FSM (Flujo 5). No requiere tabla nueva.
