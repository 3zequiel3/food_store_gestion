## Context

El flow actual de checkout es:

1. Front arma carrito en Zustand.
2. Front llama `POST /api/v1/pedidos/` → backend valida, persiste Pedido + DetallePedidos + HistorialEstadoPedido inicial. Pedido nace en `PENDIENTE`.
3. Front redirige a `/cliente/pedidos/:id/confirmacion`.
4. Si la forma de pago es online (MERCADOPAGO), el usuario clickea "Ir a pagar" → llega a `/cliente/pedidos/:id/pago` → `PaymentForm` invoca `POST /api/v1/pagos/` → backend llama a MP API → guarda `Pago` con `mp_status` real (`approved`, `pending`, `rejected`, etc.) → si es `approved`, dispara transición `PENDIENTE → CONFIRMADO`.
5. Si la forma de pago es EFECTIVO, no hay paso de pago — el pedido queda en `PENDIENTE` esperando que el local lo confirme manualmente.

Los problemas (medidos en producción/dev y bug reports):

- **Pedidos huérfanos**: cualquier cierre de browser entre paso (3) y paso (4) deja un `Pedido` en `PENDIENTE` sin `Pago` activo. Aparece en "Mis pedidos", cuenta en métricas, ensucia listados.
- **Semántica confusa**: la spec viva `order-creation` documenta `"PENDIENTE — Esperando pago"`. Eso solo es cierto para pedidos online. Para retiro+efectivo, `PENDIENTE` significa "esperando que el local lo confirme". El estado mezcla dos cosas distintas.
- **Bug visual**: las opciones de pago aparecen duplicadas en la UI del cliente (detectado por el usuario, a localizar línea exacta — probable bug en `PaymentMethodSelector` o en `CheckoutPage`).
- **Contract drift**: la spec `payments-checkout-api` recién archivada estableció "200 OK con cualquier mp_status como dato" — diseño defensivo que asume que pagos `pending`/`in_process` son legítimos. El usuario decidió que NO: solo `approved` cuenta. Operativa simple > completitud.

El stack backend es FastAPI + SQLModel + Postgres con UoW (`refactor-uow-to-context-manager` ya archivado). El front es React 19 + Zustand persist + TanStack Query + TanStack Form + Zod. MP se integra con SDK oficial `mercadopago` (Python). Estamos en Sprint 5 de la fase Backend-First.

**Stakeholders**: usuario único (dueño del proyecto), evaluadores académicos (cátedra), futuros maintainers del repo.

**Restricciones**:
- Strict TDD activado para este proyecto — tests primero, después implementación.
- pnpm en front, uv en back.
- Conventional commits sin "Co-Authored-By".
- No archivar sin OK del usuario.
- Specs vivas afectadas son fuente de verdad — deltas explícitos.

## Goals / Non-Goals

**Goals:**

- Garantizar que NUNCA exista un `Pedido` en la DB sin contexto completo: o bien con `Pago.mp_status == "approved"` (online), o bien sin Pago porque es pickup+efectivo.
- Hacer el flow de checkout atómico — un solo endpoint por ruta, una sola operación percibida por el usuario.
- Redefinir `PENDIENTE` con semántica única: "pedido recién creado, esperando que el local lo acepte".
- Simplificar la operativa: si MP no devuelve `approved`, el cliente reintenta. Sin pedidos colgados, sin estados intermedios, sin reconciliación por webhook como camino principal.
- Eliminar el bug visual de opciones de pago duplicadas.
- Mantener idempotencia del lado del cliente vía `idempotency_key` (UUID4 generado en el front).
- Cobertura TDD completa: cada camino del nuevo flow tiene test RED → GREEN antes de mergear.

**Non-Goals:**

- Verificación de firma del webhook MP (queda para futuro change `payments-webhook-signature`).
- TOCTOU / `SELECT FOR UPDATE` en el cobro (queda para `payments-concurrency-and-cleanup`).
- PII leaks en `console.log` / logs sanitizados (idem).
- Refactor del FSM **más allá de** lo declarado en D4 y D13. La matriz `ALLOWED_TRANSITIONS` y `TRANSITION_ROLES` mantienen su estructura — solo se renombra una clave (`EN_CAMINO` → `TERMINADO`), no se agregan ni quitan transiciones.
- Soporte para múltiples gateways de pago (solo MP).
- Migración automática de datos en producción.

## Decisions

### D1 — El pedido se crea POST-checkout, no PRE-checkout

**Decisión**: el `Pedido` se persiste solo cuando el checkout completa exitosamente. No hay "estado borrador" en la DB.

**Alternativas consideradas**:
- (a) Crear pedido en estado `BORRADOR` antes de pagar, transicionar a `PENDIENTE` post-pago. **Rechazada**: agrega un estado más al FSM, complejiza el listado de "Mis pedidos" (filtrar borradores), no resuelve el problema de huérfanos si el usuario cierra entre borrador y pago.
- (b) Crear pedido pre-pago como hoy y limpiar huérfanos con un job cron cada N minutos. **Rechazada**: el usuario los ve mientras tanto, ensucian métricas, requiere infra de job scheduler que no tenemos.
- (c) Crear pedido post-pago, el camino propuesto. **Elegida**: cero huérfanos por construcción.

**Rationale**: la única forma de garantizar "no hay pedidos huérfanos" es no persistirlos hasta tener confirmación. El carrito vive en el front (Zustand `persist`) durante el armado — si el usuario cierra el browser, lo recupera en su próxima visita; si abandona definitivamente, el browser eventualmente limpia el localStorage. Nada en la DB.

### D2 — Dos endpoints separados, no uno polimórfico

**Decisión**: `POST /api/v1/checkout/online` y `POST /api/v1/checkout/pickup-efectivo`. Schemas distintos. Sin discriminator.

**Alternativas consideradas**:
- (a) Un solo endpoint `POST /checkout` con un discriminator `tipo: "ONLINE" | "PICKUP_EFECTIVO"` y campos condicionalmente requeridos. **Rechazada**: el schema condicional con Pydantic v2 funciona pero genera OpenAPI confuso, errores de validación crípticos, y obliga al front a manejar shape variable.
- (b) Dos endpoints, schemas explícitos. **Elegida**: contratos claros, OpenAPI legible, validación trivial, errores en la dimensión correcta.

**Rationale**: las dos rutas no comparten contrato. Online requiere `card_token`, `payment_method_id`, `installments`, `idempotency_key`, identification. Pickup+efectivo no requiere nada de eso. Forzar un schema único es elegancia mal entendida.

### D3 — Modo estricto MP: solo `approved` crea pedido

**Decisión**: si MP devuelve cualquier `status != "approved"` (incluyendo `pending`, `in_process`, `authorized`, `rejected`, `cancelled`, `refunded`, otros), `POST /checkout/online` NO crea pedido y devuelve `402 Payment Required` (o `422`) con `mp_status`, `status_detail` y un mensaje user-friendly. Si MP no responde, `502 Bad Gateway` con `code="mp_unreachable"` — tampoco crea pedido.

**Alternativas consideradas**:
- (a) Aceptar `pending`/`in_process` como "pedido en revisión" — modelo que recomienda MP para Argentina. Crear pedido en `PENDIENTE` con `Pago.mp_status="pending"` y esperar el webhook. **Rechazada por decisión del usuario**: agrega operativa de seguimiento (¿qué hace el local con un pedido en revisión? ¿cocina o espera?), requiere lógica de timeout (si el webhook nunca llega, ¿el pedido se cancela?), requiere notificación al cliente cuando el pago final llega. El usuario aceptó perder esas ventas a cambio de cero ambigüedad operativa.
- (b) Modo estricto. **Elegida**.

**Rationale (decisión de producto del usuario)**: la operativa real de un local pequeño no soporta "pedido condicionado a confirmación bancaria diferida". El cocinero necesita saber si arranca o no. Cualquier pago no inmediato se trata como rechazo desde el punto de vista del flow — el cliente reintenta o usa otra tarjeta o cambia a pickup+efectivo. El webhook MP se mantiene como red de seguridad para reconciliar casos excepcionales (transición fallida post-cobro, pagos retrasados por MP que finalmente aprueban), pero no es parte del happy path.

**Costo aceptado**: perder ventas en revisión genuinas. Trade simple.

### D4 — `PENDIENTE` redefinido semánticamente: "esperando local"

**Decisión**: `PENDIENTE` significa "el pedido fue creado y está esperando que el local (rol PEDIDOS o ADMIN) lo acepte". No significa más "esperando pago" porque, en el flow nuevo, todo pedido que existe está pagado (online) o no requiere prepago (pickup+efectivo).

**Alternativas consideradas**:
- (a) Renombrar el código a `RECIBIDO` o `ESPERA_LOCAL` para que el código matchee la semántica. **Rechazada**: rompería el FSM existente, requeriría migración de datos en archivo, deltaría specs de `order-state-machine` recién archivadas. El nombre `PENDIENTE` es suficientemente genérico para sostener la nueva semántica.
- (b) Mantener `PENDIENTE` con semántica nueva, documentar el rename semántico en specs. **Elegida**: cero churn de código, claridad por documentación.

**Rationale**: el costo de renombrar > el costo de documentar. `PENDIENTE` como "estado inicial del pedido" es interpretable correctamente sin más. La spec `order-state-machine` recibe el delta del rename semántico.

### D5 — Pedido + Pago en una sola transacción UoW

**Decisión**: en `CheckoutService.crear_pedido_online`, después de que MP devuelva `approved`, abrir un único `UnitOfWork` y dentro de él:
1. `INSERT Pedido` (estado `PENDIENTE`).
2. Flush para obtener `pedido_id`.
3. `INSERT N × DetallePedido`.
4. `INSERT HistorialEstadoPedido` inicial.
5. `INSERT Pago` con `mp_status="approved"`, `mp_payment_id`, `pedido_id`, `external_reference=idempotency_key`.
6. Commit.

Si cualquiera de estos pasos falla, la UoW hace rollback completo. El cobro a MP ya ocurrió — esto deja un incidente operativo (cliente cobrado sin pedido). Se registra con `logger.exception(...)` incluyendo `mp_payment_id`, `idempotency_key`, `user_id`, payload del carrito. El webhook MP (que sigue activo) puede reconciliar si llega después con el mismo `external_reference` — crearía el pedido con la información que tiene.

**Alternativas consideradas**:
- (a) Dos transacciones separadas (Pedido en una, Pago en otra). **Rechazada**: ventana entre commits puede ver Pedido sin Pago.
- (b) Crear Pago primero, Pedido después en la misma transacción. **Rechazada**: `Pago.pedido_id` es FK NOT NULL — necesitamos `pedido_id` antes de insertar Pago.
- (c) Una UoW, orden Pedido → flush → Pago. **Elegida**.

**Rationale**: la atomicidad transaccional es la única garantía operativa. El edge case "MP cobra, persistencia falla" es un riesgo aceptado y monitoreado (es < 0.01% en operativa normal, y existe la red de seguridad del webhook).

### D6 — `external_reference` = `idempotency_key`, no `str(pedido_id)`

**Decisión**: cuando `CheckoutService` llama a `sdk.payment().create(...)`, pasa `external_reference = idempotency_key` (UUID4 del front). El `Pago.external_reference` se persiste con ese UUID. El webhook MP reconcilia por `external_reference == idempotency_key`.

**Alternativas consideradas**:
- (a) Pre-generar `pedido_id` consultando `nextval('orders_id_seq')` antes de llamar a MP. Usarlo como `external_reference = str(pedido_id)`. **Rechazada**: pre-generar IDs sin insertar genera gaps en la secuencia (no es un problema en Postgres pero feels weird), y obliga al `CheckoutService` a conocer detalles del sequence.
- (b) Usar el `idempotency_key` (UUID4 generado por el front) como `external_reference`. **Elegida**: el UUID ya es único, ya está en el request, no requiere conocer el schema de la DB.

**Rationale**: el `idempotency_key` cumple los dos roles que tenía `pedido_id` en MP: identificador único y eslabón de reconciliación. Cambio mecánico, sin pérdida de información.

**Impacto en webhook**: `PaymentService.procesar_webhook` cambia de `pedido_id = int(external_reference)` a `pago = repo.find_by_external_reference(external_reference)` → `pedido_id = pago.pedido_id`. Una indirección más, despreciable.

### D7 — Migración de datos: dev/testing limpio, prod manual

**Decisión**: en dev/testing se ejecuta un script SQL idempotente que elimina pedidos en `PENDIENTE` que no tienen `Pago` asociado activo (`mp_status IN ('approved')`). En producción, NO se ejecuta automáticamente. El usuario evalúa manualmente y decide qué hacer caso por caso (probable: borrarlos todos, son huérfanos por definición; o bien dejarlos y marcarlos como `CANCELADO_ADMIN` con motivo "huérfano legacy").

**Alternativas consideradas**:
- (a) Script automático en producción al deployar. **Rechazada por decisión del usuario**: producción puede tener datos que el usuario quiere preservar/auditar antes de borrar.
- (b) Solo dev/testing automático, prod manual. **Elegida**.

**Rationale**: principio de mínima intervención automática en datos productivos. El script para dev/testing vive en `backend/scripts/cleanup_orphan_orders.sql` o equivalente.

### D8 — Carrito en Zustand `persist` (ya implementado, reforzar)

**Decisión**: el `cartStore` ya usa `persist` con `localStorage`. Verificar que sigue funcionando correctamente después del refactor del flow. Tests explícitos: (a) agregar item → cerrar tab → reabrir → item presente; (b) checkout exitoso → `clearCart()` invocado → localStorage limpio.

**Alternativas consideradas**:
- (a) Persistir en backend (carrito server-side). **Rechazada**: agrega infra innecesaria; el carrito es estado UI, no de dominio.
- (b) Sin persistencia (sesión-only). **Rechazada**: empeora UX en el caso "cerré sin querer".
- (c) `persist` con localStorage (status quo). **Elegida**.

**Rationale**: el `persist` ya existe (`zustand/middleware`). Solo verificamos el contrato.

### D9 — Bug de opciones de pago duplicadas — fix puntual con root cause

**Decisión**: identificar el archivo:línea del bug en la fase de auditoría (Grupo 1 de tasks). Las hipótesis a verificar:
- (a) `PaymentMethodSelector` renderiza el mismo array dos veces por un `useEffect` sin dependencias o un `key` mal puesto.
- (b) El array de formas de pago se duplica en el state por un `setState(prev => [...prev, ...nuevas])` accidental.
- (c) Hay dos instancias del componente montadas (e.g. `<PaymentMethodSelector />` aparece dos veces en el render tree).

Fix mecánico una vez identificado: corregir el origen, agregar test de regresión que cuenta `radio` elements del componente.

**Alternativas consideradas**: ninguna — es un bug.

### D10 — `POST /pedidos/` y `POST /pagos/` se eliminan (no 410 Gone)

**Decisión**: ambos endpoints se eliminan de `router.py`. No se mantienen como `410 Gone` con mensaje deprecado.

**Alternativas consideradas**:
- (a) Eliminar. **Elegida**.
- (b) Devolver `410 Gone` con `detail`. **Rechazada**: el único cliente es el front, que migra atómicamente en el mismo PR. Agregar `410 Gone` solo ensucia OpenAPI con un endpoint que no debería existir.

**Rationale**: el `grep` confirma que solo el front consume estos endpoints (`frontend/src/features/checkout/services/orders.service.ts` para `POST /pedidos/`, `frontend/src/features/payments/services/payments.service.ts` para `POST /pagos/`). Migración atómica = eliminación segura.

### D11 — Validación server-side total: nunca confiar en el front para totales

**Decisión**: el `CheckoutService` recalcula `total` server-side a partir de los `items` del request (lee precios actuales de `productos`) y el costo de envío (`50.00` si hay `direccion_id`, `0.00` si pickup). El `total` recalculado es el que se pasa a MP y se persiste. El front puede enviar un `total_estimado` informativo, pero el backend lo IGNORA.

**Rationale**: anti-smuggling. Misma regla que ya está en `order-creation` para `precio_snapshot` (RN-PE08). Se hereda al nuevo capability.

### D12 — Idempotencia con `idempotency_key` del front

**Decisión**: el front genera un UUID4 al iniciar el checkout y lo envía como `idempotency_key` en el body. El backend pasa ese valor como `X-Idempotency-Key` a MP (header oficial de MP API). Además, antes de llamar a MP, el backend hace un lookup en `pagos` por `external_reference = idempotency_key` para detectar reintentos: si ya existe un Pago con ese key, devuelve el resultado de la operación previa (no re-cobra).

**Alternativas consideradas**:
- (a) Idempotencia solo via MP (sin lookup local). **Rechazada**: MP devuelve el mismo `payment_id` ante un retry con mismo `X-Idempotency-Key`, pero si nuestra DB no completó la persistencia previa (D5 falló), repetir la lógica nos puede dejar inconsistentes. Mejor detectar primero.
- (b) Idempotencia via MP + lookup local. **Elegida**.

**Rationale**: defensa en profundidad. El UUID4 es el ancla que conecta cliente, MP y nuestra DB.

### D13 — Rename `EN_CAMINO` → `TERMINADO` (vocabulario unificado retiro/envío)

**Decisión**: el código de estado `EN_CAMINO` se renombra a `TERMINADO` en toda la base de código y datos persistidos. `TERMINADO` significa "pedido listo para ser retirado del local o entregado al cliente". La transición `EN_PREPARACION → EN_CAMINO → ENTREGADO` pasa a ser `EN_PREPARACION → TERMINADO → ENTREGADO`. La matriz `ALLOWED_TRANSITIONS` y `TRANSITION_ROLES` mantiene su forma — solo cambia la clave.

**Alternativas consideradas**:
- (a) Mantener `EN_CAMINO` y agregar `TERMINADO` como estado paralelo solo para pickup. **Rechazada**: bifurca el FSM en dos caminos según tipo de entrega, complica la UI y los métricos, va exactamente contra el objetivo de "flujo unificado" que pidió el usuario.
- (b) Mantener `EN_CAMINO` y documentar la nueva semántica sin renombrar (como hicimos con `PENDIENTE` en D4). **Rechazada**: `EN_CAMINO` es semánticamente incorrecto para retiro en local — el cliente no "va en camino", va al mostrador. Forzar la nueva semántica sobre el código equivocado genera lecturas confusas en código y UI.
- (c) Renombrar a `TERMINADO`. **Elegida**: el código matchea el dominio, una sola lectura, sin bifurcación.

**Rationale**: el usuario fue explícito sobre querer "un flujo de estados consistente independientemente si es retiro en local o envío". El nombre `TERMINADO` cumple esa promesa. La diferencia con el rename rechazado de D4 (PENDIENTE) es que ahí el nombre genérico SÍ sostenía la nueva semántica; acá `EN_CAMINO` claramente NO sostiene "listo para retirar".

**Alcance del rename**:
- **Backend**: `backend/features/orders/state_machine.py` (`ALLOWED_TRANSITIONS`, `TRANSITION_ROLES`), `backend/features/orders/schemas.py` (Literal de `AvanzarEstadoRequest` y validators), `backend/scripts/seed.py` (semilla de `estados_pedido`), tests en `backend/tests/integration/` y `backend/tests/conftest.py`.
- **Frontend**: `OrderFilters.tsx`, `OrderTimeline.tsx`, `OrderStatusBadge.tsx`, `OrderStateActions.tsx`, `orders.types.ts` (tipo `EstadoCodigo`), `PedidosPorEstadoChart.tsx` (color mapping).
- **DB**: migración Alembic con tres UPDATEs idempotentes:
  ```sql
  UPDATE estados_pedido SET codigo = 'TERMINADO' WHERE codigo = 'EN_CAMINO';
  UPDATE orders SET estado_codigo = 'TERMINADO' WHERE estado_codigo = 'EN_CAMINO';
  UPDATE order_state_history SET estado_anterior_codigo = 'TERMINADO' WHERE estado_anterior_codigo = 'EN_CAMINO';
  UPDATE order_state_history SET estado_nuevo_codigo = 'TERMINADO' WHERE estado_nuevo_codigo = 'EN_CAMINO';
  ```
  + reverso simétrico en `downgrade()`.
- **Documentación**: `backend/README.md` línea 237, specs vivas.

**Costo**: ~15-20 archivos tocados de forma mecánica. Tests del FSM deben actualizar los literales `"EN_CAMINO"` → `"TERMINADO"`. La migración es idempotente y reversible.

## Risks / Trade-offs

- **[Riesgo] MP aprueba el pago, persistencia falla → cliente cobrado sin pedido** → Mitigación: (a) logging exhaustivo (`mp_payment_id`, `idempotency_key`, `user_id`, payload, stack trace), (b) el webhook MP sigue activo y puede crear el pedido a posteriori usando `external_reference == idempotency_key`, (c) el cliente tiene la opción de contactar soporte mostrando el `mp_payment_id`. Probabilidad esperada: < 0.01%.

- **[Riesgo] Pérdida de ventas "en revisión" por modo estricto (D3)** → Mitigación: aceptado explícitamente por el usuario. Documentar en `docs/decisions/checkout-strict-mode.md` o en la spec viva del nuevo capability. Si en el futuro la operativa lo justifica, este change tiene un sucesor natural `checkout-pending-review` que reintroduce el camino.

- **[Riesgo] Bug visual no reproducible localmente** → Mitigación: en la fase de auditoría (Grupo 1, task 1.3), capturar el bug en un test de Vitest + Testing Library antes de fixearlo. Si no es reproducible en tests, abrir un browser test con Chrome DevTools MCP.

- **[Riesgo] Datos huérfanos en producción** → Mitigación: D7 — el usuario decide manualmente qué hacer. Script de cleanup disponible pero no automático.

- **[Riesgo] `idempotency_key` reutilizado entre carritos distintos** → Mitigación: el front genera un nuevo UUID4 cada vez que el usuario navega a `/cliente/checkout`. Si se queda en la página y reintenta tras un fallo, el mismo UUID se reutiliza (es el comportamiento deseado de la idempotencia). Si vuelve al carrito y entra a checkout otra vez, un UUID nuevo.

- **[Riesgo] Tests del FSM ya archivados caen por el rename `EN_CAMINO → TERMINADO` (D13)** → Mitigación: la matriz `ALLOWED_TRANSITIONS` y `TRANSITION_ROLES` mantiene su forma (mismas transiciones, mismos roles), solo se renombra una clave. Tests que comparan literales contra `"EN_CAMINO"` se actualizan mecánicamente a `"TERMINADO"`. Migración Alembic incluida en este change actualiza filas existentes en `estados_pedido`, `orders.estado_codigo`, `order_state_history.estado_anterior_codigo`/`estado_nuevo_codigo`. Tarea declarada en Grupo 4 nuevo.

- **[Riesgo] Race condition entre response del checkout y webhook MP** → Mitigación: el webhook ya tiene idempotencia (`InvalidStateTransitionError` 409 si el estado ya cambió). Si el webhook llega antes del response al cliente, el pedido ya está creado y en `PENDIENTE` (no cambia de estado porque ya está ahí). Si llega después, igual — todo consistente.

- **[Trade-off] Operativa simple > completitud** → Aceptado. Documentado en D3.

- **[Trade-off] Modificar una spec recién archivada (`payments-checkout-api`)** → Aceptado. La evolución de specs es esperada en SDD. El delta de este change documenta el por qué.

## Migration Plan

1. **Pre-merge (desarrollo)**:
   - Crear branch `feat/checkout-pay-first-flow`.
   - Implementar Grupo 1–11 de tasks (TDD).
   - Validación local con back + front (Grupo 10).
   - Bug de opciones de pago duplicadas verificado con browser tools.
   - PR review.

2. **Deploy a testing**:
   - Ejecutar migraciones (no hay nuevas, solo seeds si aplica).
   - Ejecutar `backend/scripts/cleanup_orphan_orders.sql` para limpiar pedidos huérfanos en testing.
   - Smoke test manual: checkout online approved, checkout online rejected, checkout pickup+efectivo.

3. **Deploy a producción** (cuando aplique):
   - Ejecutar migraciones (no hay nuevas).
   - NO ejecutar cleanup automático (D7). El usuario decide manualmente.
   - Smoke test manual.

4. **Rollback**:
   - El change es BREAKING en endpoints. Rollback = revertir el merge en código y volver a deploy. Los datos persistidos durante la ventana del nuevo flow (pedidos con Pago aprobado en una UoW única) son válidos para ambos flows — no requieren cleanup al volver. Los pedidos que se hubieran intentado crear y rechazado por D3 (modo estricto) no existen en la DB, no hay nada que limpiar.
   - Tiempo estimado de rollback: 1 deploy.

## Open Questions

- ¿El script de cleanup en dev/testing debería ejecutarse en CI antes de cada suite, o solo manualmente? — Recomendación: solo manualmente, evitar acoplar CI a un script destructivo. Si los tests crean huérfanos como parte de su setup, los deben limpiar en `tearDown` propio. Confirmar con el usuario en Grupo 1.

- ¿El `PaymentForm` queda como componente reutilizable o se inlinea dentro del `CheckoutPage`? — Recomendación: dejarlo como componente reutilizable, pero invocado desde dentro del `CheckoutPage` en el step de pago (no como página separada). Esto preserva la separación de responsabilidades (form de tarjeta = lógica encapsulada) y permite testearlo aislado.

- ¿Qué pasa con `PaymentResultPage` (`/cliente/pagos/resultado` o similar)? — Recomendación: se elimina si solo se usa post-PaymentPage. Si tiene otro uso (e.g. retorno desde MP Checkout Pro), se evalúa en Grupo 9.

- ¿La spec `checkout-validation` necesita más cambios que la pequeña navegación, o queda como está? — Recomendación: solo navegación. La validación pre-checkout sigue siendo válida; lo que cambia es a dónde va después.

- ¿Documentamos la decisión D3 (modo estricto) en `docs/decisions/`? — Recomendación: sí, archivo nuevo `docs/decisions/2026-05-17-checkout-strict-mode.md`. Se crea en Grupo 11.
