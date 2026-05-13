# Design — order-state-machine-fsm

## Context

### Estado actual del backend (verificado en código, 2026-05-12)

El módulo `backend/features/orders/` ya tiene el ciclo de creación de pedidos completo (change #14 archivado) y la transición PENDIENTE→CONFIRMADO disparada por el webhook de MercadoPago (change #15 archivado). En concreto:

- **`OrderService.transicionar_estado(pedido_id, estado_anterior, estado_nuevo, actor_id=None)`** ya existe en `backend/features/orders/service.py:167-208`. Abre su propio `with UnitOfWork()`, busca el pedido con `find_by_id()`, valida que el estado actual coincida con `estado_anterior` (si no, lanza `InvalidStateTransitionError` que mapea a HTTP 409), cambia `estado_codigo`, hace `flush`, crea historial vía `create_historial_transicion()`, y refresca. `actor_id=None` significa SISTEMA (webhook).
- **`PaymentService.procesar_webhook()`** (en `backend/features/payments/service.py`, change #15) llama `transicionar_estado(pedido_id, "PENDIENTE", "CONFIRMADO", actor_id=None)` cuando llega `payment.status == "approved"`. Esta línea es contrato vivo que no puede romperse.
- **`OrderRepository.find_by_id(pedido_id)`** existe (sin lock — busca por id + `eliminado_en IS NULL`). Se reemplazará por `get_pedido_for_update()`.
- **`OrderRepository.create_historial_transicion(pedido_id, estado_anterior_codigo, estado_nuevo_codigo, actor_id)`** existe — hay que extenderla para aceptar `motivo`.
- **`InvalidStateTransitionError(ConflictError)`** ya existe en `backend/shared/exceptions.py:61` con `code="state_transition_conflict"` → HTTP 409. Reutilizar.
- **Modelo `HistorialEstadoPedido`** (en `backend/features/orders/models.py:161-207`) hereda de `AppendOnlyBaseModel` (sin UPDATE ni DELETE físico). Falta la columna `motivo` (RN-FS09).
- **Estado `EN_PREPARACION`** (no `EN_PREP`) confirmado en `backend/scripts/seed.py:74`, `conftest.py`, y `Historias_de_usuario.txt`. El `Integrador.txt §3.4` usa `EN_PREP` solo como abreviación visual del diagrama, no como código.
- **Roles**: M:N vía `user_roles` pivot. `usuario.roles` retorna `list[Rol]` con `Rol.nombre` en {ADMIN, STOCK, PEDIDOS, CLIENT} (RN-RB01).
- **Patrón de auth**: `Depends(get_current_user)` retorna `Usuario`; `Depends(require_role("X"))` filtra por rol estático. Para FSM necesitamos RBAC **dinámico** (el rol válido depende de la transición pedida), así que el router solo usa `get_current_user`.

### Por qué importa entender lo que ya existe

El propose anterior trabajó como si #15 no existiera y propuso reescribir `transicionar_estado()`. Eso habría roto el webhook silenciosamente. Este design parte de la premisa opuesta: **`transicionar_estado()` es el punto de entrada compartido entre webhook y endpoint manual**. Lo extendemos sin reemplazarlo.

### Constraints

- **Backwards compatibility**: la firma `transicionar_estado(pedido_id, estado_anterior, estado_nuevo, actor_id=None)` debe seguir invocable tal cual desde `PaymentService`. Solo se permite **agregar kwargs opcionales**.
- **STRICT TDD**: cada artefacto de código se prueba primero, se implementa después. Modulo `state_machine.py` con tests puros antes de cualquier capa de servicio.
- **UoW único por operación**: nada de "fan out" a múltiples UoW; la transición + historial + side-effects de stock viven en la misma transacción (RN-FS04).
- **Lexicón castellano**: `avanzar_estado`, `transicionar_estado`, `AvanzarEstadoRequest`, `EN_PREPARACION` (sin acentos). Snake_case en JSON.

## Goals / Non-Goals

**Goals:**

1. Completar la FSM definida en RN-FS01 a RN-FS09 sin reescribir la API existente.
2. Implementar RBAC por transición conforme RN-FS08 + RN-RB08.
3. Decrementar stock atómicamente en CONFIRMADO (RN-FS03, RN-FS04) y restaurarlo en cancelaciones desde CONFIRMADO/EN_PREPARACION (RN-FS05).
4. Permitir transiciones manuales desde `PATCH /api/v1/pedidos/{id}/estado` con doble defensa contra confirmación manual (RN-FS02).
5. Registrar `motivo` en cada transición (RN-FS09) sin romper filas históricas.
6. Eliminar la race condition latente del webhook reemplazando `find_by_id()` por `SELECT FOR UPDATE`.

**Non-Goals:**

- No se cambia la lógica de creación de pedido (`crear_pedido` queda intacta).
- No se cambia el flujo de pago ni el cliente de MercadoPago.
- No se implementa el endpoint de visualización de pedidos (`GET /pedidos/{id}`) — eso es #17.
- No se implementa la UI de gestión de estados — eso es frontend posterior.
- No se persiste un audit log adicional fuera de `HistorialEstadoPedido` (el modelo append-only ya cumple RN-FS07).
- No se permite editar/eliminar entradas del historial (RN-03, RN-PA02 — `AppendOnlyBaseModel` lo impide a nivel ORM).
- No se modela `motivo` como entidad relacionada — es texto libre máx. 500 caracteres en `order_state_history`.

## Decisions

### D1 — Arquitectura de 2 capas (alto nivel + bajo nivel)

**Decisión**: Mantener `OrderService.transicionar_estado()` como **capa de bajo nivel** (sin FSM, sin RBAC — solo cambio de estado + historial + side-effects de stock condicionales) y crear `OrderService.avanzar_estado(user_id, pedido_id, nuevo_estado, motivo)` como **capa de alto nivel** que valida FSM, RBAC y ownership, y luego delega a `transicionar_estado()`.

**Por qué**:
- El webhook llama desde un contexto SISTEMA (sin `user_id`, sin rol). Si metiéramos validación de rol dentro de `transicionar_estado()`, romperíamos el webhook o nos forzaría un `if actor_id is None: skip RBAC` que ensucia el contrato.
- `transicionar_estado()` ya tiene cliente vivo (#15). Reescribir su firma o agregar checks de roles obligatorios sería un breaking change.
- Separa preocupaciones: la pieza de bajo nivel garantiza atomicidad y side-effects de inventario; la pieza de alto nivel garantiza autorización.

**Alternativa rechazada**: tener un único `avanzar_estado()` que acepta `actor=None|user` y branchea. Más feo, más bugs, y obliga a tocar la línea del webhook.

### D2 — Side-effects de stock viven en `transicionar_estado()`, no en `avanzar_estado()`

**Decisión**: El decremento (PENDIENTE→CONFIRMADO) y la restauración (→CANCELADO desde CONFIRMADO o EN_PREPARACION) se aplican dentro de `transicionar_estado()`, no en la capa de alto nivel.

**Por qué**:
- Cuando el webhook de #15 confirma un pedido, el stock **también** debe decrementarse (RN-FS03). Si el decremento estuviera solo en `avanzar_estado()`, el webhook no lo dispararía.
- La regla "stock cambia cuando el estado cambia a/desde el estado correcto" es invariante del dominio, no de la fuente de la transición. Encapsularla en la operación atómica es lo correcto.
- Mantiene la UoW única (RN-FS04 — todo o nada).

**Alternativa rechazada**: poner el decremento en `avanzar_estado()` y obligar al webhook a llamar a una función separada. Más superficie de error, más duplicación.

### D3 — FSM como constante Python en módulo aislado `state_machine.py`

**Decisión**: Las transiciones válidas y la matriz de roles viven en `backend/features/orders/state_machine.py` como dicts plain Python, no en BD ni en tablas:

```python
ALLOWED_TRANSITIONS = {
    "PENDIENTE":      {"CANCELADO"},
    "CONFIRMADO":     {"EN_PREPARACION", "CANCELADO"},
    "EN_PREPARACION": {"EN_CAMINO", "CANCELADO"},
    "EN_CAMINO":      {"ENTREGADO"},
    "ENTREGADO":      set(),
    "CANCELADO":      set(),
}

TRANSITION_ROLES = {
    ("PENDIENTE",     "CANCELADO"):      {"CLIENT", "PEDIDOS", "ADMIN"},
    ("CONFIRMADO",    "EN_PREPARACION"): {"PEDIDOS", "ADMIN"},
    ("CONFIRMADO",    "CANCELADO"):      {"PEDIDOS", "ADMIN"},
    ("EN_PREPARACION","EN_CAMINO"):      {"PEDIDOS", "ADMIN"},
    ("EN_PREPARACION","CANCELADO"):      {"ADMIN"},          # RN-RB08
    ("EN_CAMINO",     "ENTREGADO"):      {"PEDIDOS", "ADMIN"},
}
```

Nota: `("PENDIENTE", "CONFIRMADO")` NO aparece en `TRANSITION_ROLES` porque solo el webhook (capa de bajo nivel, SISTEMA) la ejecuta — RN-FS02.

**Por qué**: testeable sin BD, fácil de revisar diff, fácil de razonar. La FSM cambia poco; cuando cambie, queremos saberlo vía git diff.

**Alternativa rechazada**: tabla `state_transitions` en BD. Sobre-ingeniería para algo que es una constante del dominio.

### D4 — `validate_transition()` levanta excepciones específicas

**Decisión**: `validate_transition(desde, hacia, user_roles)` lanza:
- `BusinessRuleError("Transición '<desde>' → '<hacia>' no permitida")` (HTTP 422) si la transición no está en `ALLOWED_TRANSITIONS`.
- `ForbiddenError(...)` (HTTP 403) si la transición existe pero el usuario no tiene ninguno de los roles requeridos.

**Por qué**: semántica HTTP correcta. "Transición prohibida por FSM" es regla de negocio (422). "No tenés permiso para hacer esta acción" es autorización (403). El front debe poder distinguir las dos para mostrar mensajes adecuados.

**Alternativa rechazada**: usar `InvalidStateTransitionError` para todo. Pierde la diferencia entre "fenómeno imposible" y "permiso insuficiente".

Nota: `InvalidStateTransitionError` (HTTP 409) sigue existiendo y se levanta desde `transicionar_estado()` cuando el estado actual del pedido **no coincide** con `estado_anterior` (race condition, doble click, idempotencia).

### D5 — `avanzar_estado()` rechaza `CONFIRMADO` con doble defensa

**Decisión**:
1. **Capa Pydantic**: `AvanzarEstadoRequest.nuevo_estado: Literal["CANCELADO", "EN_PREPARACION", "EN_CAMINO", "ENTREGADO"]`. Si llega `"CONFIRMADO"`, FastAPI responde 422 antes de tocar el service.
2. **Capa service**: aún si alguien construye la request directo en código y se saltea Pydantic, `avanzar_estado()` chequea `if nuevo_estado == "CONFIRMADO": raise BusinessRuleError(...)` antes de cualquier otra cosa.

**Por qué**: RN-FS02 es crítico. La confirmación implica decremento de stock real — un bug que la permita manualmente sería un agujero de inventario. Defensa en profundidad.

### D6 — Restauración de stock en cancelaciones desde CONFIRMADO **o** EN_PREPARACION

**Decisión**: `transicionar_estado()` restaura stock cuando la transición es `(CONFIRMADO|EN_PREPARACION) → CANCELADO`. No restaura en PENDIENTE→CANCELADO (porque el stock no se había decrementado).

**Por qué**: RN-FS05 dice "al cancelar un pedido que ya fue CONFIRMADO". EN_PREPARACION es un sucesor de CONFIRMADO, así que el stock ya fue decrementado. La cancelación desde ahí debe restaurarlo. En PENDIENTE no hay nada que restaurar.

### D7 — `motivo` obligatorio en cancelaciones desde estados "con stock decrementado"

**Decisión**: `avanzar_estado()` exige `motivo: str` (no vacío, no solo espacios) cuando la transición es `(CONFIRMADO|EN_PREPARACION) → CANCELADO`. Lo deja opcional en PENDIENTE→CANCELADO y en transiciones de avance.

**Por qué**: US-044 explícitamente lista "el motivo de cancelación" como dato a registrar para cancelaciones de pedidos que ya estaban activos. Cancelar un pedido recién creado (PENDIENTE) suele ser por "no quiero más" — exigir motivo ahí es fricción innecesaria.

### D8 — `transicionar_estado()` reemplaza `find_by_id()` por `get_pedido_for_update()`

**Decisión**: Agregar `OrderRepository.get_pedido_for_update(pedido_id)` con `.with_for_update()` y usarla dentro de `transicionar_estado()`.

**Por qué**: el webhook de #15 actualmente usa `find_by_id()` (sin lock). Si MercadoPago reenvía el webhook (lo hace ante timeout) y dos workers procesan en paralelo, ambos podrían leer `estado_codigo="PENDIENTE"` y los dos podrían intentar cambiarlo. El segundo lanzaría `InvalidStateTransitionError` (porque tras el commit del primero, el estado ya es CONFIRMADO), pero el segundo `decrement_stock` podría haberse ejecutado antes del check. Con `FOR UPDATE`, el segundo worker espera; cuando obtiene el lock, lee `CONFIRMADO` y aborta limpio.

**Trade-off**: en SQLite (tests no-pg) `.with_for_update()` es no-op. Los tests de concurrencia se marcan `@pytest.mark.pg_only` (patrón ya establecido en #14).

### D9 — Idempotencia heredada: re-procesamiento del webhook responde 409

**Decisión**: No agregar lógica de "si ya está en CONFIRMADO, no hagas nada". Mantener que `transicionar_estado()` lanza `InvalidStateTransitionError` cuando `pedido.estado_codigo != estado_anterior`.

**Por qué**:
- Es el comportamiento actual y los tests de #15 lo validan.
- 409 es la respuesta correcta para "intentaste avanzar desde un estado que ya cambió".
- El consumer (PaymentService) tiene que decidir qué hacer con 409. En el webhook, eso significa "ya lo procesé antes, ack al MP y listo" — ese manejo vive en `PaymentService.procesar_webhook()`, no acá.

### D10 — Naming: `EN_PREPARACION` (sin tilde, sin abreviar)

**Decisión**: Usar `EN_PREPARACION` consistentemente: en código Python, en literals Pydantic, en seed, en migration, en tests, en JSON.

**Por qué**: ya está así en `backend/scripts/seed.py:74`, `conftest.py` (líneas 250 y 258), `Descripcion.txt`, y `Historias_de_usuario.txt`. `Integrador.txt §3.4` solo lo abrevia como `EN_PREP` en el diagrama ASCII visual del FSM, no como código del estado. La spec **viva** (seed + tests) ya escogió `EN_PREPARACION`.

**Alternativa rechazada**: usar `EN_PREP`. Romper la consistencia con seed/tests existentes. No.

### D11 — Migration nullable de `motivo`

**Decisión**: La columna nueva `motivo` en `order_state_history` es `VARCHAR(500) NULL`. Sin default. Sin backfill.

**Por qué**:
- Las filas históricas (creadas por #14 y #15) no tienen motivo. Backfillearlas a `""` sería mentir.
- RN-FS09 lo pide "como dato a registrar", no como NOT NULL. La obligatoriedad se aplica condicionalmente en `avanzar_estado()` (D7), no a nivel de schema.
- Migration up/down es trivial: `add_column` / `drop_column`. Rollback seguro.

### D12 — RBAC dinámico vive en el service, no en el router

**Decisión**: El endpoint usa `Depends(get_current_user)` sin filtro de rol. `avanzar_estado()` recibe `user_id` y consulta los roles del usuario internamente — luego matchea contra `TRANSITION_ROLES[(desde, hacia)]`.

**Por qué**: el rol válido **depende de la transición pedida**. `require_role("X")` estático no sirve. Y la lógica "qué rol puedo usar para esta transición" pertenece al dominio FSM, no a la capa HTTP.

**Implementación**: dentro del service, después de cargar el pedido y antes de transicionar, hacer:
```python
user = user_repo.find_by_id_with_roles(user_id)
user_roles = {r.nombre for r in user.roles}
validate_transition(pedido.estado_codigo, nuevo_estado, user_roles)
```

**Verificado en código**: `UserRepository.find_by_id_with_roles()` YA existe en `backend/features/users/repository.py:27-43` con `selectinload(Usuario.roles)` para evitar `DetachedInstanceError`. NO requiere implementación nueva — solo importar y usar. Ver D14 para el flujo completo de instanciación.

### D13 — Ownership CLIENT: solo cancela los pedidos que le pertenecen

**Decisión**: En `avanzar_estado()`, si el usuario tiene rol CLIENT (y NO tiene otro rol más privilegiado), validar que `pedido.user_id == user_id`. Si no, lanzar `NotFoundError` (no `ForbiddenError`) — patrón anti-leak ya establecido en `crear_pedido` (D6 de #14).

**Por qué**: RN-RB05 ("CLIENT solo opera sobre sus propios datos"). Anti-leak: si devolviéramos 403, el cliente sabría que ese pedido existe (filtración de IDs). 404 mantiene la opacidad.

**Aclaración**: si el usuario tiene rol PEDIDOS o ADMIN, esa validación se saltea — los gestores ven cualquier pedido.

### D14 — `avanzar_estado()` usa sesión directa de lectura, NO UoW propia

**Decisión**: `avanzar_estado()` NO abre `with UnitOfWork() as uow:`. En su lugar:

```python
def avanzar_estado(self, user_id, pedido_id, nuevo_estado, motivo=None) -> Pedido:
    # Check 1 — defensa contra CONFIRMADO manual (D5)
    if nuevo_estado == "CONFIRMADO":
        raise BusinessRuleError("CONFIRMADO solo se setea automáticamente vía webhook de pago")

    # Lectura directa de solo lectura (sin UoW, sin lock) — patrón análogo
    # a auth/dependencies.py:get_current_user
    session = get_session_factory()()
    try:
        order_repo = OrderRepository(session)
        user_repo = UserRepository(session)
        pedido = order_repo.find_by_id(pedido_id)
        if pedido is None:
            raise NotFoundError(...)
        user = user_repo.find_by_id_with_roles(user_id)  # ya existe (verificado)
        user_roles = {r.nombre for r in user.roles}
        # ownership (D13)
        if user_roles == {"CLIENT"} and pedido.user_id != user_id:
            raise NotFoundError(...)
        # FSM + RBAC (D3, D4)
        validate_transition(pedido.estado_codigo, nuevo_estado, user_roles)
        # motivo condicional (D7)
        if nuevo_estado == "CANCELADO" and pedido.estado_codigo in {"CONFIRMADO", "EN_PREPARACION"}:
            if not motivo or not motivo.strip():
                raise BusinessRuleError(...)
        estado_actual = pedido.estado_codigo
    finally:
        session.close()

    # Delegar a transicionar_estado (abre SU propia UoW con FOR UPDATE)
    return self.transicionar_estado(
        pedido_id=pedido_id,
        estado_anterior=estado_actual,
        estado_nuevo=nuevo_estado,
        actor_id=user_id,
        motivo=motivo,
    )
```

**Por qué**:
- Si `avanzar_estado` abriera su propia UoW para leer pedido + roles, y después cerrara para delegar a `transicionar_estado` (que abre OTRA UoW con `FOR UPDATE`), tendríamos **dos UoW anidadas/secuenciales** con potencial inconsistencia.
- Si `avanzar_estado` mantuviera la UoW abierta hasta después de delegar, el `FOR UPDATE` de `transicionar_estado` correría dentro de la sesión de `avanzar_estado` — confusión de scope.
- La sesión directa de lectura es **idiomática del proyecto** (ver `auth/dependencies.py:get_current_user` y `get_optional_user`): operaciones de solo-lectura no necesitan UoW completa.
- La race entre las dos lecturas (la de `avanzar_estado` y la de `transicionar_estado`) es **benigna**: si el estado del pedido cambió entre la lectura inicial y el lock pesimista de la segunda, `transicionar_estado` lanza `InvalidStateTransitionError` (409). El usuario reintenta — comportamiento idempotente correcto.

**Alternativa rechazada — `avanzar_estado` con UoW propia que cierra antes de delegar**: dos transacciones secuenciales, lock liberado entre medio. No aporta valor sobre la sesión directa.

**Alternativa rechazada — `avanzar_estado` sin delegar, duplicando lógica**: rompe el principio DRY y la arquitectura de 2 capas (D1).

**Verificado en código existente**: `UserRepository.find_by_id_with_roles()` ya está implementado en `backend/features/users/repository.py:27-43` con `selectinload(Usuario.roles)`. NO requiere agregar métodos nuevos al UserRepository.

**Consecuencias**:
- + Patrón consistente con auth dependencies (lecturas no transaccionales).
- + Una sola transacción real (la de `transicionar_estado`), que es la que importa para atomicidad.
- + Race benigna manejada por idempotencia (409).
- − Hay dos lecturas del pedido (una sin lock para validar, otra con FOR UPDATE para aplicar). Costo despreciable (mismo PK, query rápido).

## Risks / Trade-offs

- **R1: Romper la API de `transicionar_estado()` que consume el webhook de #15**
  → **Mitigación**: solo agregar kwargs **opcionales** con defaults. Test de regresión explícito en la suite: `test_webhook_confirma_pedido_sigue_funcionando_tras_extension`. Correr la suite completa de #15 antes de mergear.

- **R2: Race condition al cambiar `find_by_id()` por `FOR UPDATE`**
  → **Mitigación**: el cambio **mejora** la concurrencia, no la empeora. Los tests existentes pasan en SQLite (no-op) y se valida en BD dev real con un test concurrente marcado `pg_only`.

- **R3: Decremento de stock falla en mitad de transacción**
  → **Mitigación**: UoW rollback garantizado (`__exit__` en `UnitOfWork`). Si `decrement_stock_for_items` lanza, ni el cambio de estado ni el historial se persisten. RN-FS04 satisfecho.

- **R4: CLIENT cancela pedido ajeno**
  → **Mitigación**: D13 — ownership check con 404 antes de transicionar.

- **R5: Confirmación manual accidental (RN-FS02)**
  → **Mitigación**: doble defensa de D5. Tests explícitos: `test_avanzar_estado_rechaza_confirmado_via_pydantic` y `test_avanzar_estado_rechaza_confirmado_via_service`.

- **R6: Motivo demasiado largo (DoS por tamaño)**
  → **Mitigación**: `Field(max_length=500)` en Pydantic + `VARCHAR(500)` en BD. Mensaje 422 si excede.

- **R7: La migration deja la BD inconsistente si falla a medias**
  → **Mitigación**: `add_column` con `NULL` y sin constraints es atómico en Postgres. Si falla, ya no hay nada que limpiar. Probar `alembic upgrade head && alembic downgrade -1 && alembic upgrade head` en BD dev antes de mergear.

- **R8: Test suite explota porque varios tests existentes usan `find_by_id` en `transicionar_estado` o asumían stock invariante en CONFIRMADO**
  → **Mitigación**: los tests existentes no acceden a `find_by_id` interna — usan el endpoint o `PaymentService`. Si algún test mockea `find_by_id`, se reemplaza por `get_pedido_for_update`. **Adicional crítico**: los 14 tests de `test_payments.py` (#15) que ejercitan `procesar_webhook()` ahora verán **decremento de stock** como side-effect nuevo. Si alguno hace `assert producto.stock_cantidad == X` esperando el valor pre-confirmación, va a fallar. Task 8.1 corre esa suite primero para detectar regresiones; si fallan, actualizar los asserts para reflejar el nuevo invariante (stock decrementado tras CONFIRMADO).

## Migration Plan

1. **Pre-deploy**: correr `alembic upgrade head` para agregar columna `motivo`.
2. **Deploy del código**: la línea del webhook que llama a `transicionar_estado()` sigue exactamente igual; el código nuevo solo agrega kwargs opcionales y side-effects condicionales.
3. **Verificación post-deploy**: smoke test del webhook (puede ser con MP sandbox) — confirma que un pago aprobado decrementa stock y crea historial.
4. **Rollback (si hace falta)**:
   - Revertir el deploy del código.
   - `alembic downgrade -1` para quitar `motivo` (las filas que la rellenaron ya no existen porque cancelaciones nuevas no se hicieron).

## Open Questions

Ninguna que bloquee la implementación. Todas las decisiones están cerradas contra el código real verificado y las RN canónicas.
