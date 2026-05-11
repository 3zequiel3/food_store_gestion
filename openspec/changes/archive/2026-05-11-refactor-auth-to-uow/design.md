# Design: refactor-auth-to-uow

## Context

### Estado actual (post `refactor-uow-to-context-manager`)

El refactor anterior (archivado 2026-05-11) migró los 5 features de dominio al patrón **service-driven UoW**:

```python
class CategoryService:
    def __init__(self) -> None:
        pass

    def create(self, data: CategoryCreate) -> Categoria:
        with UnitOfWork() as uow:
            uow.register_repository("categorias", CategoryRepository(uow.session))
            return uow.categorias.create(data)
        # __exit__ hace commit (o rollback en exc) + close
```

El router queda libre de `Depends(get_uow)` y `uow.commit()`:

```python
@router.post("/")
async def create_category(data: CategoryCreate):
    service = CategoryService()
    return service.create(data)
```

**Auth quedó FUERA** del scope con justificación explícita (D6 del design archivado):

> "`auth/service.py` y `auth/router.py` usan `Session` directa via `Depends(get_db)`, patrón distinto al UoW. Se difiere a un change separado para no inflar este scope."

Hoy auth es **el único feature** que sigue el patrón viejo `Depends(get_db)`:

```python
# router.py — patrón viejo
@router.post("/register")
async def register(request: Request, data: RegisterRequest, db=Depends(get_db)):
    service = AuthService(db)
    user = await service.register(data)
    return await service._create_token_pair(user)  # ← segunda llamada al service
```

```python
# service.py — patrón viejo
class AuthService:
    def __init__(self, session: Session):
        self.session = session
        self.refresh_token_repo = RefreshTokenRepository(session)

    async def register(self, data: RegisterRequest) -> Usuario:
        # ... crea Usuario + UsuarioRol con flush(), sin commit
        return user  # commit lo hace get_db() al yield-out
```

### Bug latente confirmado (R1 del explore)

El `register` actual NO es atómico de forma explícita. La secuencia es:

1. `AuthService.register(data)` → `session.add(user)` + `flush()` + `session.add(user_role)` + `flush()` + `session.refresh(user)` + `return user`.
2. Router recibe `user`, llama `service._create_token_pair(user)` → `session.add(refresh_token_db)` + `flush()` + `return TokenPairResponse(...)`.
3. Router retorna, `get_db()` sale del `try: yield db` y ejecuta `db.commit()` — Usuario + UsuarioRol + RefreshToken se persisten en UN solo commit.

Esto **funciona** en práctica (la atomicidad emergente la garantiza la sesión compartida + commit único de `get_db`), pero:

- **La responsabilidad transaccional vive en el adapter HTTP** (`get_db`), no en el caso de uso (service). Anti-clean-architecture.
- **El invariante "register es atómico" no es legible** en el código del service — depende de un mecanismo externo.
- **Si alguien cambia el router** (ej. agrega un `service.method()` adicional entre `register` y `_create_token_pair` que falla), el rollback parcial puede dejar usuarios sin token pair.

### Surface area transversal

`get_current_user` y `require_role` son consumidos por **22 endpoints fuera de auth**:
- categories: 3 endpoints (POST/PUT/DELETE con `require_role`)
- products: 8 endpoints (CRUD + relations con `require_role`)
- ingredients: 3 endpoints
- addresses: 5 endpoints
- users: 3 endpoints (`/me`)

Cualquier cambio de firma o semántica de estas dependencies se propaga a TODO el backend autenticado.

### Decisiones cerradas previas heredadas

- **Patrón target idéntico al refactor anterior** (servicio abre UoW, router solo traduce HTTP). NO se reabre la discusión vs spec del integrador §7.1 — esa decisión ya está tomada y archivada.
- **`UnitOfWork` con `__enter__` / `__exit__`** disponible y funcional.
- **Monkeypatch de `get_session_factory`** en `conftest.py` ya existe y cubre el inyecto de sesión SQLite en tests.

## Goals / Non-Goals

**Goals:**

- Migrar `AuthService` al patrón service-driven UoW idéntico a los otros 5 features (consistencia arquitectónica).
- Corregir el bug latente de atomicidad en `register`: Usuario + UsuarioRol + RefreshToken en una transacción explícita, owned by el service.
- Eliminar `get_db()` del contrato público — cierra la deuda técnica del refactor anterior.
- Convertir `AuthService` a sync (eliminar `async def` sin `await`).
- Preservar el contrato HTTP de auth byte-by-byte: 0 cambios visibles al cliente.

**Non-Goals:**

- Migrar `get_current_user` a `with UnitOfWork()` completo (excepción D1, ver Decisions).
- Tocar la firma pública de `get_current_user` o `require_role` (los 22 endpoints downstream son intocables).
- Refactorizar el módulo `security.py` (`hash_password`, `verify_password`, JWT helpers) — son funciones puras sin DB.
- Cambiar el `RefreshTokenRepository` — sigue siendo un repo simple SQLAlchemy.
- Agregar nuevos tests de auth — la suite existente (15 tests) cubre el contrato HTTP que se preserva.

## Decisions

### D1: `get_current_user` y `get_optional_user` usan **sesión directa**, no UoW completo

**Decisión.** Las auth dependencies abren una sesión SQLAlchemy directa (vía `get_session_factory()()` con `try/finally` para cerrar), NO un `with UnitOfWork()`.

**Why.**

- `get_current_user` ejecuta exactamente **1 SELECT** (`SELECT * FROM users WHERE id = ? AND is_active AND eliminado_en IS NULL`).
- `get_optional_user` lo mismo (delega a `get_current_user`).
- Son **middleware HTTP de autenticación**, no operaciones de negocio. Conceptualmente NO son casos de uso.
- `UnitOfWork` está pensado para operaciones multi-tabla con commit explícito. Para read-only sin escrituras, el overhead de `register_repository`, `commit` en `__exit__`, etc., es semánticamente confuso (no hay nada que comitear).
- La sesión directa es **explícitamente read-only por contrato** (documentado en docstring) — si alguien intenta escribir desde una dependency de auth, está usando el mecanismo equivocado.

**Alternatives considered.**

- **A1: `get_current_user` abre `with UnitOfWork() as uow:` y devuelve el usuario.** Rechazado: agrega `commit` innecesario en `__exit__` para una operación read-only; mezcla conceptos (dependency HTTP vs caso de uso).
- **A2: `get_current_user` recibe `uow: UnitOfWork = Depends(...)` y la sesión viaja desde el endpoint.** Rechazado: estaríamos reintroduciendo `Depends` transaccional que el refactor anterior eliminó. Además el endpoint ya abrió su propio UoW para la operación de negocio — duplicaríamos sesiones.
- **A3: cachear el usuario en `request.state`.** Rechazado: fuera de scope, cambia semántica visible y agrega complejidad.

**Consequences.**

- (+) Performance: una sola operación, sin overhead transaccional.
- (+) Lectura clara: "esto es middleware HTTP, no caso de uso".
- (−) Asimetría con services: el lector debe entender que auth deps son una excepción justificada.
- (−) Si alguien futuro hace una escritura en `get_current_user` (ej. "actualizar last_login_at"), el commit NO ocurre. Mitigación: docstring explícito + comentario inline que prohíbe escrituras.
- Patrón concreto:

```python
def get_current_user(token: Optional[str] = Depends(oauth2_scheme)) -> Usuario:
    if not token:
        raise UnauthorizedError("Token de autenticación requerido")
    payload = decode_access_token(token)
    # ... validación ...
    session = get_session_factory()()
    try:
        user = session.execute(query).scalar_one_or_none()
        if not user:
            raise UnauthorizedError(...)
        return user
    finally:
        session.close()
```

### D2: `require_role` NO se modifica

**Decisión.** `require_role(*roles)` se mantiene intacto.

**Why.**

- Su implementación actual delega 100% en `get_current_user` (vía `Depends(get_current_user)`).
- NO toca `get_db` directamente. NO abre sesión propia.
- Si `get_current_user` se refactoriza correctamente, `require_role` hereda el comportamiento sin cambios.

**Alternatives considered.**

- **A1: Refactorizar `require_role` para abrir sesión propia.** Rechazado: duplicaría lógica de sesión; sin justificación funcional.

**Consequences.**

- (+) Cero riesgo de regresión en los 14 endpoints que usan `require_role`.
- (+) Menos código tocado, menos surface area de bugs.

### D3: `get_db()` se elimina del contrato público

**Decisión.** `backend/shared/database.py` deja de exportar `get_db()`. La función se elimina por completo (no se mantiene como "interno" — sin consumidores, sin razón de existir).

**Why.**

- Post-refactor, **ningún módulo de producción** usa `get_db`:
  - Router de auth: refactorizado a `AuthService().register(...)` sin `db`.
  - `dependencies.py` (auth): refactorizado a sesión directa.
  - Otros features: ya estaban refactorizados al UoW.
- `conftest.py` ya tiene un mecanismo superior: monkeypatch de `get_session_factory` (heredado del refactor anterior).
- `backend/dependencies.py:4` tiene un NOTE obsoleto que menciona `get_db` — se actualiza al eliminar la función.
- Mantener `get_db` "por si acaso" es **deuda técnica zombie**: código sin consumidores que aparece en grep results y confunde.

**Alternatives considered.**

- **A1: Mantener `get_db` como helper privado (`_get_db`).** Rechazado: no hay consumidores; agregar un underscore no es una mejora real.
- **A2: Deprecar con `DeprecationWarning` por una versión.** Rechazado: no hay versioning de API interno; el proyecto es solo backend interno; agregar deprecation noise sin razón.

**Consequences.**

- (+) Una sola forma de obtener sesiones: `UnitOfWork()` o `get_session_factory()()`. Sin alternativas legacy.
- (+) Limpieza del docstring obsoleto que mencionaba `get_uow` (función ya eliminada).
- (−) Si algún módulo externo (script de seed, herramienta de admin) usaba `get_db`, se rompe. Mitigación: `rg "from backend.shared.database import get_db"` antes del cleanup; los únicos matches deben ser auth (que se refactoriza) y conftest (que se limpia).

### D4: `register()` cambia firma — retorna `TokenPairResponse` directamente (CRÍTICO)

**Decisión.** `AuthService.register(data: RegisterRequest) -> TokenPairResponse`. La creación de Usuario + UsuarioRol + RefreshToken vive **dentro de un único `with UnitOfWork()`**. El router hace una sola llamada al service.

**Why.**

- Cierra el bug latente R1: hoy `register` retorna `Usuario` y el router llama `_create_token_pair(user)` por separado. Si `_create_token_pair` falla por cualquier razón (ej. error de DB en el `INSERT refresh_tokens`), Usuario + UsuarioRol ya fueron `flushed()` y dependen del `rollback` implícito de `get_db()` — una promesa transaccional NO declarada en el código.
- Con la nueva firma, el invariante es **explícito**: las 3 inserciones viven en el mismo `with`. Si cualquiera falla, `__exit__` hace rollback de todas.
- Alinea el output del service con el output del router (`TokenPairResponse`) — desaparece la asimetría "service devuelve user, router devuelve tokens".

**Alternatives considered.**

- **A1: `register` sigue devolviendo `Usuario` pero abre UoW completo internamente; el router llama `_create_token_pair` por separado fuera del with.** Rechazado: el problema de atomicidad NO se resuelve — `_create_token_pair` quedaría fuera del with del register, abriendo un segundo UoW. Si el segundo falla, el primer commit ya persistió Usuario + UsuarioRol.
- **A2: `register` devuelve un dict `{user, token_pair}` para flexibilidad.** Rechazado: el único consumidor de `register` es el endpoint POST /register que devuelve TokenPairResponse. YAGNI.
- **A3: introducir un nuevo método público `register_and_login()` separado de `register`.** Rechazado: agrega API surface sin beneficio; el endpoint actual ya hace exactamente eso.

**Consequences.**

- (+) Atomicidad explícita garantizada en código y test.
- (+) Router de `register` se simplifica: una sola llamada al service.
- (−) **BREAKING en interfaz interna** del service: cualquier consumidor de `AuthService.register(...)` que esperaba `Usuario` se rompe. Mitigación: `rg "AuthService\(.*\)\.register"` → único consumidor es el router de auth, que se refactoriza en el mismo change. NO hay otros consumidores en el backend.
- (−) Tests unitarios que llamen directamente `AuthService().register(data)` esperando `Usuario` se rompen. Mitigación: NO hay tests unitarios del service que hagan eso; los 15 tests de `test_auth.py` son tests HTTP que pasan por el router.
- Patrón concreto:

```python
def register(self, data: RegisterRequest) -> TokenPairResponse:
    with UnitOfWork() as uow:
        uow.register_repository("refresh_tokens", RefreshTokenRepository(uow.session))
        # check existing email
        existing = uow.session.execute(
            select(Usuario).where(Usuario.email.ilike(data.email), Usuario.eliminado_en.is_(None))
        ).scalar_one_or_none()
        if existing:
            raise ConflictError("El email ya está registrado")
        # create user + role
        user = Usuario(...)
        uow.session.add(user)
        uow.session.flush()
        uow.session.add(UsuarioRol(user_id=user.id, role_id=self.ROLE_CLIENT_ID))
        uow.session.flush()
        uow.session.refresh(user)
        # create token pair within same transaction
        return self._create_token_pair(user, uow.session)
```

### D5: `AuthService` pasa de `async def` a `def` (sync)

**Decisión.** Todos los métodos públicos y privados de `AuthService` se declaran `def` (sync). El router se mantiene `async def` (por compatibilidad con `@limiter.limit` y el ecosistema FastAPI).

**Why.**

- Verificación empírica: en `backend/features/auth/service.py` actual hay **0 ocurrencias de `await`** dentro del cuerpo de los métodos `async def`. SQLAlchemy sync no requiere `await`. `_create_token_pair` no awaitea nada. El `async def` es ornamental.
- `async def` sin `await` es **antipattern**: marca al método como awaitable pero introduce overhead del event loop sin razón. Es honesto declararlo `def`.
- FastAPI sabe llamar handlers sync o async indistintamente. El router puede ser `async def login(...)` y llamar `service.login(...)` sync sin problemas — FastAPI lo ejecuta en un threadpool si es necesario.
- El router se mantiene `async def` porque `@limiter.limit` (slowapi) decora `async` handlers en su forma idiomática y la convención del repo es `async def` en routers.

**Alternatives considered.**

- **A1: Mantener `async def` en el service "por consistencia futura".** Rechazado: la consistencia futura es hipotética; el código actual es ruido. Si en el futuro se introduce async I/O real (ej. async SQLAlchemy), se convierte en ese momento.
- **A2: Convertir también el router a `def` sync.** Rechazado: riesgo no justificado de interacción con slowapi; convención del repo es async routers; los otros 5 features tienen routers async.

**Consequences.**

- (+) Código honesto sobre lo que realmente hace.
- (+) Menos overhead semántico para el lector.
- (−) Si alguien convierte futuro el repo a async DB, hay que volver a tocar el service. Costo bajo.

### D6: `_create_token_pair` se mantiene como helper privado, recibe `session` explícita

**Decisión.** `_create_token_pair(self, user: Usuario, session: Session) -> TokenPairResponse` — recibe la sesión del UoW activo del caller. NO abre su propio UoW.

**Why.**

- `_create_token_pair` es llamado desde 3 lugares: `register`, `login`, `refresh`. Cada uno ya abrió su `with UnitOfWork()`. Si `_create_token_pair` abre el suyo propio, tendríamos 2 sesiones simultáneas para la misma operación → potencial deadlock, definitivamente fuera del invariante transaccional.
- Pasarle `session` explícita lo hace **honestamente dependiente** de un contexto transaccional externo. El tipo en la firma documenta el contrato.
- Es un helper privado (`_`), no parte de la API pública. No hay riesgo de "uso incorrecto" externo.

**Alternatives considered.**

- **A1: Inlinear `_create_token_pair` en cada caller.** Rechazado: el código se duplica 3 veces (~25 líneas cada uno). DRY violado sin razón.
- **A2: `_create_token_pair` abre su propio UoW.** Rechazado: rompe atomicidad de `register` y `refresh` (que necesitan crear el RefreshToken en la misma tx que el resto de la operación).
- **A3: `_create_token_pair` recibe `uow: UnitOfWork`.** Considerado, pero la única dependencia interna es la session — pasar el UoW completo es overhead conceptual sin beneficio. La session es el contrato mínimo necesario.

**Consequences.**

- (+) Atomicidad preservada en register/refresh.
- (+) DRY mantenido.
- (−) Helper privado con firma "rara" (recibe session externa). Mitigación: docstring explícito que documente el contrato.

### D7: Orden de cleanup de `conftest.py`

**Decisión.** El cleanup de `override_get_db` en `conftest.py` se hace **al final** de los tasks, NO al principio.

**Why.**

- Si se elimina `override_get_db` antes de refactorizar `dependencies.py`, los tests de auth fallan en CI porque `get_current_user` sigue usando `Depends(get_db)` que apunta a Postgres (no a SQLite del test).
- La fixture `_patch_uow_session_factory` (existente, heredada del refactor anterior) NO cubre `get_db` — solo cubre `UnitOfWork()` que internamente llama `get_session_factory`. Si `get_current_user` aún usa `Depends(get_db)`, ese path NO está monkey-patched.
- Por lo tanto el orden seguro es: **(1) refactorizar `dependencies.py` y `service.py` para no depender de `get_db`** → **(2) verificar tests verdes** → **(3) eliminar `override_get_db` y `get_db()`** → **(4) verificar tests verdes de nuevo**.

**Alternatives considered.**

- **A1: Hacer el cleanup en paralelo con el refactor.** Rechazado: aumenta riesgo de fallar tests intermedios y no saber qué cambio causó la falla.

**Consequences.**

- (+) Cada commit deja la suite verde.
- (+) Si algo falla, el bisect es trivial.

### D8: `get_optional_user` se refactoriza junto con `get_current_user`

**Decisión.** `get_optional_user` se refactoriza en el mismo step que `get_current_user`. NO se difiere.

**Why.**

- `get_optional_user` ya delega en `get_current_user` (línea 141: `return await get_current_user(token, db)`). Si cambia la firma de `get_current_user` (deja de aceptar `db`), `get_optional_user` SE ROMPE inmediatamente.
- No hay forma de hacer el cambio "parcial" — son interdependientes.

**Alternatives considered.**

- Ninguna razonable.

**Consequences.**

- Ambas funciones se refactorizan en el mismo commit (parte del task 1.2).

## Risks / Trade-offs

### R1 — Atomicidad de `register` post-refactor

[Riesgo] Si el refactor se hace mal (ej. `_create_token_pair` queda fuera del `with` de `register`), el bug latente persiste.

→ **Mitigación**: tasks específicos (3.2-3.3) sobre estructurar `register` con un único `with`; scenarios de atomicidad en la spec delta que se vuelven test cases obligatorios.

### R2 — Sesión directa en `get_current_user` permite escritura silenciosa

[Riesgo] Si alguien futuro agrega `session.add(...)` o `session.execute(UPDATE ...)` dentro de `get_current_user`, el cambio NO se comitea (no hay `__exit__` que comitee).

→ **Mitigación**: docstring explícito "READ-ONLY — no writes allowed"; comentario inline; PR review.

### R3 — Propagación a 22 endpoints downstream

[Riesgo] Si accidentalmente cambia la firma o el comportamiento de `get_current_user` (ej. omitir el chequeo de `is_active`), 22 endpoints en 5 features se rompen.

→ **Mitigación**: el contrato externo de `get_current_user` y `require_role` se mantiene IDÉNTICO (mismo input, mismo output, mismas exceptions); correr la suite completa (no solo `test_auth.py`) después del refactor; los tests de `test_categories`, `test_products`, etc., usan auth_headers y son la red de seguridad.

### R4 — Orden de cleanup en conftest.py

[Riesgo] Eliminar `override_get_db` antes de refactorizar `dependencies.py` rompe los 15 tests de auth.

→ **Mitigación**: D7 establece el orden explícito; tasks 1, 2, 3 refactorizan código; task 4 limpia conftest; task 5 elimina `get_db()`.

### R5 — Flush intermedios en `refresh`

[Riesgo] `refresh()` hace `flush()` después de `revoke_all_user_tokens` (UPDATE bulk) y `mark_token_as_revoked` (UPDATE single) para que los cambios sean visibles antes del SELECT en `_create_token_pair`. Si por error se eliminan estos `flush()` al refactorizar, el SELECT post-UPDATE devuelve datos stale.

→ **Mitigación**: task explícito sobre preservar `uow.session.flush()` intermedios; los `flush()` son válidos dentro de `with UnitOfWork()` — solo `commit` se difiere al `__exit__`. Verificación: `test_refresh_token_replay_detection` cubre este path.

### R6 — `register` retorna `TokenPairResponse` rompe consumidores externos

[Riesgo] Si algún script de seed, fixture de test, o herramienta usa `AuthService().register(...)` esperando `Usuario`, se rompe.

→ **Mitigación**: `rg "service\.register|AuthService.*\.register" backend/` antes del refactor. Verificación previa: único consumidor es `router.py:54` que se refactoriza en el mismo change.

### R7 — Conftest monkeypatch cubre todos los paths de sesión

[Riesgo] El monkeypatch existente de `get_session_factory` solo cubre los paths donde se llama `get_session_factory()` directamente. Si `get_current_user` post-refactor llama `get_session_factory()()` para abrir sesión read-only, ese path SÍ está cubierto. Si llama por otra ruta, NO.

→ **Mitigación**: en `get_current_user` post-refactor, usar **exactamente** `get_session_factory()()` (no `engine.connect()` ni otras alternativas). Task 1.2 explicita el patrón.

## Migration Plan

No hay migración de datos. No hay migración de API externa. Es un refactor interno transparente al cliente HTTP. El "plan de migración" interno es la secuencia ordenada de los tasks (Steps 1-4) que mantiene la suite verde después de cada commit.

Rollback: cada step es un commit independiente. Si el step 2 (router) rompe algo, `git revert` solo ese commit. Step 1 (service + dependencies) puede convivir temporalmente con un router viejo si el cleanup del router se atrasa — el service nuevo acepta ser llamado con o sin `session` en el constructor (durante la transición no, porque el constructor cambia limpiamente; pero si fuera necesario, podríamos hacer transición gradual con un `Optional[Session]` deprecado). Para este change preferimos commit atómico por step sin transición gradual — la suite verde después de cada step es suficiente garantía.

## Open Questions

Ninguna. El explore cubrió todas las decisiones (D1-D8); los riesgos están mitigados; el contrato HTTP es estable; los consumidores internos son conocidos y limitados.
