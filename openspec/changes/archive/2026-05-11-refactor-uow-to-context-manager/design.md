# Design: refactor-uow-to-context-manager

## Context

### Estado actual del UoW

`backend/shared/unit_of_work.py` (líneas 17–115) implementa hoy:

```python
class UnitOfWork:
    def __init__(self, session: Session) -> None:
        self.session = session
        self._repositories: dict[str, Any] = {}

    def register_repository(self, name: str, repository: Any) -> None: ...
    def __getattr__(self, name: str) -> Any: ...        # acceso dinámico
    def commit(self) -> None: ...                       # session.commit()
    def rollback(self) -> None: ...
    def close(self) -> None: ...
```

**Lo que falta**: `__enter__`, `__exit__` y la capacidad de auto-crear su propia sesión.

### Cómo se usa hoy en `dependencies.py`

```python
def get_uow():
    SessionLocal = get_session_factory()
    session = SessionLocal()
    uow = UnitOfWork(session)
    try:
        yield uow
    except Exception:
        uow.rollback()
        raise
    finally:
        uow.close()
```

`get_uow` es un generator dependency de FastAPI que gestiona el ciclo de vida desde la capa HTTP. Esto es lo que el refactor elimina.

### Cómo se usa hoy en routers

```python
@router.post("/")
async def crear(payload: CategoryCreate,
                uow: UnitOfWork = Depends(get_uow),
                _user=Depends(require_role("ADMIN", "STOCK"))):
    service = CategoryService(uow)
    cat = service.create(payload)
    uow.commit()
    return CategoryRead.model_validate(cat)
```

### Cómo se usa hoy en services

```python
class CategoryService:
    def __init__(self, uow: UnitOfWork) -> None:
        uow.register_repository("categorias", CategoryRepository(uow.session))
        self.repo: CategoryRepository = uow.categorias  # vía __getattr__
        self.uow = uow

    def create(self, payload: CategoryCreate) -> Categoria:
        # ... lógica ...
        return self.repo.create(...)
        # NUNCA llama self.uow.commit() — eso es responsabilidad del router (D6)
```

### Test infrastructure actual (`backend/tests/conftest.py:106-114`)

```python
def override_get_uow():
    uow = UnitOfWork(test_db_session)
    try:
        yield uow
    except Exception:
        uow.rollback()
        raise

app.dependency_overrides[get_uow] = override_get_uow
```

El conftest sobre-escribe `get_uow` para inyectar la `test_db_session` SQLite. Como el refactor elimina `get_uow`, el override deja de tener efecto y necesitamos otro punto de inyección.

### Constraints

- **Atomicidad por caso de uso**: cada método público de service representa un caso de uso completo. Una sola transacción de DB por llamada.
- **Tests verdes después de cada step**: la migración debe ser incremental sin romper la suite (256 tests).
- **Sin dependencias nuevas**: usar la pila existente (Python stdlib `contextlib`, SQLAlchemy / SQLModel ya presentes).
- **Spec del integrador §7.1 dice "Router abre with"**: este change se desvía intencionalmente. Documentar la justificación clean-architecture.

## Goals / Non-Goals

### Goals

1. Trasladar la responsabilidad transaccional del router al service.
2. Convertir `UnitOfWork` en context manager (`__enter__` / `__exit__`).
3. Hacer que `UnitOfWork()` sea self-contained: crea su propia sesión, no depende de inyección externa salvo en tests.
4. Eliminar `get_uow` de `backend/dependencies.py` por completo.
5. Colapsar los 2 cases de double-read pattern (`products.set_categorias`, `users.update_profile`) en una sola llamada al service.
6. Preservar el comportamiento observable: el contrato HTTP de los endpoints queda idéntico.
7. Mantener la suite de 256 tests verde después del refactor.

### Non-Goals

- **NO** migrar `auth/service.py` ni `auth/router.py`. Usan `Session` directa con `Depends(get_db)`, patrón distinto. Es deuda técnica reconocida que se difiere a un change separado.
- **NO** tocar `backend/shared/database.py` (`get_db`, `get_session_factory`, `engine`).
- **NO** tocar `BaseRepository` ni los repositorios concretos.
- **NO** introducir async (`AsyncSession`, `async with`) — todo se mantiene sync.
- **NO** agregar tests nuevos. La cobertura actual de 256 tests valida el refactor.
- **NO** cambiar el contrato HTTP de ningún endpoint (paths, request schemas, response schemas, status codes).
- **NO** agregar dependencies en `requirements.txt`.

## Decisions

### D1 — Lifecycle del UoW: el service abre el `with`, no el router

**Elección**: el service abre `with UnitOfWork() as uow:` dentro de cada método público.

**Por qué**: Clean architecture pura. El caso de uso (capa service) representa una operación atómica del dominio; la transacción es parte del caso de uso. El router es solamente un adapter HTTP — su responsabilidad es validar request/response y delegar.

**Alternativa rechazada**: que el router abra el `with` (tal como dice `Integrador.txt §7.1`). Mantiene la spec del integrador pero perpetúa el acoplamiento HTTP↔transacción y no resuelve el problema del double-read.

**Desviación documentada**: la spec del integrador §7.1 paso 2 dice literalmente "Router — Abre contexto: `with UnitOfWork() as uow:` — llama service.crear_pedido(uow, body, usuario_id)". Este change se desvía con justificación clean architecture. La justificación queda registrada en `proposal.md` § "Why" y aquí.

### D2 — UnitOfWork como context manager

**Elección**: implementar `__enter__` / `__exit__`. `__exit__` hace `commit()` en éxito, `rollback()` en exception, `close()` siempre en `finally`.

**Snippet exacto a aplicar** (sustituye el `__init__` actual y agrega los dos dunder methods):

```python
# backend/shared/unit_of_work.py
from typing import Any, Callable, Optional

from backend.shared.database import get_session_factory


class UnitOfWork:
    """Context manager that owns a SQLAlchemy session for one use case.

    Opened by the service (NOT the router). On clean exit commits; on
    exception rolls back; in either case closes the session.
    """

    def __init__(self, session_factory: Optional[Callable] = None) -> None:
        factory = session_factory or get_session_factory()
        self.session = factory()
        self._repositories: dict[str, Any] = {}

    def __enter__(self) -> "UnitOfWork":
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        try:
            if exc_type is None:
                self.session.commit()
            else:
                self.session.rollback()
        finally:
            self.session.close()
        return False  # do not suppress exceptions

    # register_repository / __getattr__ / commit / rollback / close
    # remain unchanged from current implementation.
```

**Por qué `return False` en `__exit__`**: para no suprimir excepciones — el caller (service) puede dejar que la excepción se propague al router, que la transformará en HTTPException via los handlers globales.

**Por qué seguir exponiendo `commit()` / `rollback()` públicos**: los services pueden necesitar `flush()` intermedio (ya lo hace `users.change_password`) y, en raras situaciones, un commit intermedio dentro del mismo `with`. No se rompe API.

### D3 — `UnitOfWork()` sin argumentos crea su propia sesión

**Elección**: `__init__(self, session_factory: Optional[Callable] = None)`. Si es `None`, usa `get_session_factory()` como fallback.

**Por qué**: el service no debe conocer cómo se construye una sesión — esa es la responsabilidad de `database.py`. En tests, el `session_factory` también se inyecta NO por argumento del service sino vía monkeypatch del símbolo `get_session_factory` en el módulo `unit_of_work` (ver D8).

**Alternativa rechazada**: que el service reciba `session_factory` por DI y lo pase al `UnitOfWork`. Propaga la factory por toda la cadena, viola el principio de menor conocimiento (los servicios no necesitan saber qué es una factory).

### D4 — `get_uow` en `dependencies.py`: ELIMINADO

**Elección**: borrar el símbolo por completo. Routers ya no reciben `UnitOfWork` como Depends.

**Por qué**: si nadie lo usa, mantenerlo "deprecated" solo invita a copy-paste de patrones viejos. Borrar fuerza al developer a usar el patrón nuevo.

**Implicancia en imports**: `backend/dependencies.py` deja de importar `UnitOfWork` y `get_session_factory` (a menos que `get_db` también esté ahí — verificar al apply).

### D5 — Service signature: `__init__(self)` sin argumentos

**Elección**: `class CategoryService: def __init__(self) -> None: pass`. Cada método público abre su propio `with UnitOfWork() as uow:` y registra los repositorios dentro del `with`.

**Por qué**: el service es stateless. No tiene sentido cargarlo con un `uow` que dura para una sola operación. La instancia del service se puede crear cada vez (`CategoryService()`) o cachear como singleton — no afecta correctness porque no tiene estado interno transaccional.

**Patrón canónico nuevo del service** (ejemplo categories):

```python
# ANTES (patrón viejo)
class CategoryService:
    def __init__(self, uow: UnitOfWork) -> None:
        uow.register_repository("categorias", CategoryRepository(uow.session))
        self.repo: CategoryRepository = uow.categorias
        self.uow = uow

    def create(self, payload: CategoryCreate) -> Categoria:
        # ... ops sobre self.repo ...
        return result
        # NO commit acá

# DESPUÉS (patrón nuevo)
class CategoryService:
    def __init__(self) -> None:
        pass  # stateless

    def create(self, payload: CategoryCreate) -> Categoria:
        with UnitOfWork() as uow:
            uow.register_repository("categorias", CategoryRepository(uow.session))
            repo: CategoryRepository = uow.categorias
            # ... ops sobre repo ...
            return result
        # __exit__ hace commit
```

**Patrón canónico nuevo del router**:

```python
# ANTES
@router.post("/")
async def crear(payload: CategoryCreate,
                uow: UnitOfWork = Depends(get_uow),
                _user=Depends(require_role("ADMIN", "STOCK"))):
    service = CategoryService(uow)
    cat = service.create(payload)
    uow.commit()
    return CategoryRead.model_validate(cat)

# DESPUÉS
@router.post("/")
async def crear(payload: CategoryCreate,
                _user=Depends(require_role("ADMIN", "STOCK"))):
    service = CategoryService()
    cat = service.create(payload)
    return CategoryRead.model_validate(cat)
```

### D6 — Auth FUERA de scope

**Elección**: `auth/service.py` y `auth/router.py` **no se tocan** en este change.

**Por qué**: usan `Depends(get_db)` con `Session` directa, NO `Depends(get_uow)` con `UnitOfWork`. Migrar auth implicaría:
1. Crear `RefreshTokenRepository` o equivalente con el patrón de UoW.
2. Reescribir 4 endpoints (register, login, refresh, logout) y el service entero.
3. Tocar 15 tests de `test_auth.py`.

Eso duplica el scope del change. Es deuda técnica reconocida que se difiere a un change posterior (ej. `refactor-auth-to-uow`). Se documenta acá para que el lector futuro entienda por qué auth quedó fuera.

**Confirmación de spec**: `openspec/specs/auth/spec.md` no menciona `Depends(get_uow)` en ningún requirement, así que no hay delta de spec necesaria para auth.

### D7 — Resolución del double-read pattern

Hay 2 endpoints que hoy llaman al service, hacen `commit()`, y vuelven a llamar al service para releer la entidad mutada:

#### `products/router.py:248-274` — `set_categorias`

```python
# HOY
@router.put("/{producto_id}/categorias", response_model=ProductoDetail)
async def set_categorias(producto_id: int, payload: SetCategoriasRequest,
                         uow: UnitOfWork = Depends(get_uow),
                         _user=Depends(require_role("ADMIN", "STOCK"))):
    service = ProductService(uow)
    service.set_categorias(producto_id, payload.categoria_ids)
    uow.commit()
    detail = service.get_detail(producto_id)
    return ProductoDetail.model_validate(detail)
```

```python
# DESPUÉS
@router.put("/{producto_id}/categorias", response_model=ProductoDetail)
async def set_categorias(producto_id: int, payload: SetCategoriasRequest,
                         _user=Depends(require_role("ADMIN", "STOCK"))):
    service = ProductService()
    detail = service.set_categorias(producto_id, payload.categoria_ids)
    return ProductoDetail.model_validate(detail)
```

El método `ProductService.set_categorias` queda así:

```python
def set_categorias(self, producto_id: int, categoria_ids: list[int]) -> Producto:
    with UnitOfWork() as uow:
        uow.register_repository("productos", ProductRepository(uow.session))
        uow.register_repository("categorias", CategoryRepository(uow.session))
        prod_repo: ProductRepository = uow.productos
        cat_repo: CategoryRepository = uow.categorias
        # ... reemplazar pivote ...
        # ... obtener detail con relationships hidratadas ...
        detail = prod_repo.get_detail(producto_id)
        return detail
    # __exit__ commitea ambas operaciones atómicamente
```

#### `users/router.py:77-80` — `update_profile`

Mismo patrón. El service `update_profile` ya hace el update y devuelve el `Usuario` con relationships cargadas dentro del mismo `with`. El router no vuelve a llamar.

**Por qué es mejor**: una sola transacción atómica, una sola llamada al service desde el router, sin posibilidad de race condition entre commit y reread.

**Riesgo**: si el `Usuario` o `Producto` retornado depende de eager loading que solo se materializa post-commit, podrían surgir issues. Mitigación: los repositorios ya retornan objetos con `selectinload` apropiado (verificable en los repositorios — no se modifican en este change).

### D8 — Test infrastructure: monkeypatch de `get_session_factory` en el módulo `unit_of_work`

**Elección**: en `backend/tests/conftest.py` agregar fixture `autouse=True` que sustituye `backend.shared.unit_of_work.get_session_factory` por una factory que retorna la `test_db_session` SQLite. El override se restaura por test (vía pytest `monkeypatch`).

**Snippet a aplicar**:

```python
# backend/tests/conftest.py
import pytest

@pytest.fixture(autouse=True)
def _patch_uow_session_factory(monkeypatch, test_db_session):
    """Make UnitOfWork() use the test SQLite session.

    Patches get_session_factory in the unit_of_work module so that
    UnitOfWork() (called by services internally) returns the SQLite
    session from the test fixture instead of opening a Postgres
    connection.
    """
    import backend.shared.unit_of_work as _uow_mod

    def _factory():
        return lambda: test_db_session

    monkeypatch.setattr(_uow_mod, "get_session_factory", _factory)
```

**Cómo funciona**:

1. El UoW importa `from backend.shared.database import get_session_factory` a nivel de módulo.
2. `monkeypatch.setattr(_uow_mod, "get_session_factory", _factory)` reemplaza el símbolo `get_session_factory` **en el namespace de `unit_of_work`**, no en `database`.
3. Cuando el service hace `UnitOfWork()`, el `__init__` llama `get_session_factory()` → resuelve el símbolo del namespace local del módulo `unit_of_work` → devuelve `_factory()` → que devuelve `lambda: test_db_session` → el UoW lo invoca para obtener `test_db_session`.
4. `monkeypatch` restaura el símbolo al final de cada test.

**SAVEPOINT vs commit semantics — explicación**:

La fixture `test_db_session` del conftest abre una conexión SQLite, hace `connection.begin()` (transacción externa), crea una `Session` bound a esa conexión y al final hace `connection.rollback()`. Cuando el service interno hace `with UnitOfWork() as uow:` y `__exit__` llama `session.commit()`, ese `commit()` es un **SAVEPOINT** dentro de la transacción externa, NO un commit real al disco. El `connection.rollback()` final del fixture revierte todo, dejando la DB limpia para el siguiente test. Esto preserva el aislamiento sin que cada test deba truncar tablas.

**Alternativa rechazada (Opción B)**: pasar `session_factory` como argumento del service. Propaga la factory por toda la cadena, requiere cambiar la firma de los 5 services + sus invocaciones en routers. Más invasivo.

**Alternativa rechazada (Opción C)**: `UnitOfWork._session_factory` como class attribute con override. Funciona, pero el monkeypatch de módulo es más idiomático en pytest y se restaura automáticamente.

### D9 — Reescribir `test_conftest_overrides.py`

**Elección**: el test actual verifica `app.dependency_overrides[get_uow]`. Como `get_uow` desaparece, el test queda obsoleto. Reemplazar por un test que verifique:

1. Que `backend.shared.unit_of_work.get_session_factory` está monkeypatched (no es la función original).
2. Que llamar `UnitOfWork()` devuelve un UoW con `session is test_db_session` (o equivalente — la session inyectada por la fixture).

**Por qué reescribir y no borrar**: el test es una guardia de sanidad sobre el conftest. Si alguien remueve la fixture `_patch_uow_session_factory` por error, este test debe fallar primero antes que toda la suite explote.

### D10 — Estrategia: un solo change con tasks secuenciales (estrategia híbrida)

**Elección**: un único change OpenSpec con tasks dividas en STEPs:

- **Step 1** (bloqueante): refactor del core (`unit_of_work.py`, `dependencies.py`, `conftest.py`, `test_conftest_overrides.py`). Después de Step 1, los 256 tests deben seguir verdes — los services todavía usan el patrón viejo (router pasa uow al service), pero el conftest soporta ambos casos (los services todavía no llaman `UnitOfWork()` internamente, así que el monkeypatch no se ejerce; los routers todavía usan… a ver).

  > **Aclaración crítica**: en Step 1 NO podemos eliminar `get_uow` mientras los routers todavía lo usan. La secuencia correcta es:
  >
  > **Step 1 alternativo**: agregar `__enter__`/`__exit__` y `session_factory` opcional al UoW (manteniendo backward compat con `__init__(session)`), pero **NO** eliminar `get_uow` todavía. Conftest se mantiene como está.
  >
  > **Step 2** (módulo por módulo): migrar cada feature. Cuando los 5 features están migrados, Step 3 elimina `get_uow` y reescribe el conftest.
  >
  > Esto se decide finalmente como **estrategia ajustada**: ver `tasks.md` para el orden definitivo. La estrategia "Step 1 = core completo + dependencies eliminado" del explore asume que se tolera tener routers rotos durante 5 commits, lo cual no es deseable. La versión secuencial preserva tests verdes después de cada commit individual.

  **DECISIÓN FINAL**: la estrategia híbrida del explore SE ADOPTA con un ajuste: el `__init__` del UoW debe ser **compatible con ambas formas de invocación** durante la transición:

  ```python
  def __init__(self, session_or_factory=None) -> None:
      if session_or_factory is None:
          factory = get_session_factory()
          self.session = factory()
      elif callable(session_or_factory) and not isinstance(session_or_factory, Session):
          self.session = session_or_factory()
      else:
          # Backward compat: recibe Session directa (uso viejo desde get_uow)
          self.session = session_or_factory
      self._repositories = {}
  ```

  Esto permite que durante los 5 mini-commits (uno por módulo) el `get_uow` siga llamando `UnitOfWork(session)` y el código nuevo llame `UnitOfWork()` sin argumentos. **Al final** del Step 2 (todos los módulos migrados), el Step 3 simplifica el `__init__` a la forma final (`session_factory: Optional[Callable] = None`) y elimina la rama de backward compat.

- **Step 2** (5 sub-steps secuenciales): migrar categories → ingredients → products → users → addresses. Tests verdes después de cada sub-step.

- **Step 3** (cierre): eliminar `get_uow` de `dependencies.py`, eliminar la rama backward-compat del UoW `__init__`, reescribir `test_conftest_overrides.py`, simplificar el conftest (eliminar el `app.dependency_overrides[get_uow] = override_get_uow` y dejar solo el monkeypatch fixture). Tests verdes.

**Rollback**: si un sub-step de Step 2 falla, `git revert` del commit aislado de ese módulo. Los demás módulos siguen funcionando con el patrón viejo o nuevo según hayan sido migrados.

## Atomicidad preservada

### `addresses.set_principal` — 2 ops en la misma sesión

El método actual hace dos updates dentro del mismo UoW: marca todas las direcciones del user con `es_principal=False`, luego marca la elegida con `es_principal=True`. Hoy ambas se commitean juntas porque el router hace un solo `uow.commit()`.

**Post-refactor**: el service envuelve ambas ops en un solo `with UnitOfWork() as uow:`. La atomicidad se preserva porque `__exit__` hace un único `commit()` al final. Si la segunda op lanza, `__exit__` hace `rollback()` y la primera se descarta. Equivalente al comportamiento actual.

### `users.change_password` — flush intermedio

El método actual llama `self.uow.session.flush()` después del `UPDATE` de password y antes de la revocación masiva de refresh tokens. El flush garantiza que el SQL del UPDATE se envíe a la DB antes del `DELETE FROM refresh_tokens` (importante por orden de constraints / triggers).

**Post-refactor**: dentro de `with UnitOfWork() as uow: ... uow.session.flush() ...`. El `flush()` sigue siendo válido — fuerza envío sin commitear. El `commit()` final lo hace `__exit__`. Comportamiento idéntico.

### `register_repository` — sigue siendo método del UoW

El service llama `uow.register_repository("categorias", CategoryRepository(uow.session))` dentro del `with`. No cambia. Sigue siendo el punto de inyección de los repos. La diferencia es que ahora se llama dentro del scope del context manager en lugar de en el `__init__` del service.

## Auth fuera de scope — explicación expandida

`auth/router.py` (líneas 1–158) tiene 5 endpoints, ninguno de los cuales usa `Depends(get_uow)`. Todos usan `Depends(get_db)` que retorna una `Session` SQLModel directa.

`auth/service.py` (líneas 1–250) tiene `__init__(self, session: Session)`. Usa `session.add()`, `session.flush()`, `session.refresh()` directamente y NO usa `register_repository`. Tiene un solo repository custom (`RefreshTokenRepository`) que recibe `session` por argumento.

**Migrar auth implicaría**:
1. Refactorizar `RefreshTokenRepository` para registrarse vía UoW.
2. Reescribir 4 métodos de service (`register`, `login`, `refresh`, `logout`) para abrir `with UnitOfWork()`.
3. Tocar 5 endpoints del router para eliminar `Depends(get_db)` y `AuthService(db)`.
4. Validar 15 tests de `test_auth.py`, especialmente los que verifican el comportamiento de revocación de refresh tokens (operación multi-tabla).
5. Decidir qué hacer con `get_db` (si solo lo usa auth, eliminarlo también).

Eso es un change separado de scope similar al actual. Se difiere para mantener este change focalizado en los 5 features del UoW pattern.

**Plan futuro**: cuando este change esté archivado y los 5 features migrados, abrir `refactor-auth-to-uow` que aplique el mismo patrón a auth.

## Risks / Trade-offs

### Risk 1 — Conftest monkeypatch mal aplicado

[Risk] Si la fixture `_patch_uow_session_factory` no se aplica correctamente (por ejemplo, scope incorrecto, o el import del módulo `unit_of_work` ocurre antes de que el monkeypatch tenga efecto), los tests de feature intentarían abrir conexión a Postgres y los 229 tests fallarían en bulk.

→ **Mitigación**: el Step 1 termina con la fixture en el conftest pero los services todavía usan el patrón viejo. Los tests pasan porque el patrón viejo no invoca `UnitOfWork()` (lo invoca `get_uow` que sigue usando la session externa via `dependency_overrides[get_uow]`). El primer ejercicio real del monkeypatch es en Step 2.1 (categories migrado). Si falla ahí, es localizado a 31 tests, no 229. `git revert` y debug.

### Risk 2 — Auth fuera de scope

[Risk] Un developer puede asumir que el refactor incluye auth y empezar a cambiarlo, inflando el alcance.

→ **Mitigación**: documentar explícitamente en `proposal.md`, `design.md`, `tasks.md` que auth queda fuera. El test de `test_auth.py` debe seguir verde sin cambios — esa es la guardia de sanidad.

### Risk 3 — Double-read pattern roto

[Risk] Al colapsar `set_categorias` y `update_profile`, el response puede cambiar sutilmente: el objeto retornado dentro del `with` puede tener relationships en estado "lazy load" que se materializan cuando el ORM detecta acceso, pero como la session se cierra al salir del `with`, un acceso posterior (en el router al hacer `model_validate`) podría disparar `DetachedInstanceError`.

→ **Mitigación**:
- Verificar que los repositorios usan `selectinload` o equivalente para hidratar relationships dentro del `with`.
- Si Pydantic hace `model_validate` después del `with` y necesita acceder a relationships, el dict comprehension del response schema debe ejecutarse antes del `__exit__`, o el repositorio debe devolver una representación ya serializable (dict, dataclass, etc.).
- Tests existentes (`test_products.py::test_set_categorias_*`, `test_user_profile.py::test_update_profile_*`) cubren el path completo. Si pasan, el contrato se respeta.

### Risk 4 — `test_conftest_overrides.py` desincronizado

[Risk] El test actual verifica el override de `get_uow`. Si no se reescribe, falla en Step 1.

→ **Mitigación**: explicit task en `tasks.md` Step 1 para reescribir ese test. Va junto con la modificación del conftest, no después.

### Risk 5 — `session.flush()` en `users.change_password`

[Risk] El flush podría comportarse distinto cuando la sesión la crea el UoW internamente vs cuando viene inyectada.

→ **Mitigación**: el `flush()` es una operación de SQLAlchemy que no depende de cómo se creó la sesión, solo del estado de la unit-of-work interna del ORM. Comportamiento idéntico esperado. Tests `test_user_profile.py::test_change_password_*` validan.

### Trade-off 1 — Una instancia nueva del service por request

Antes: `Service(uow)` se creaba una vez por request, pero el uow venía pre-construido por `get_uow` (con su session ya creada).

Ahora: `Service()` se crea (cheap, sin estado), y dentro del método se abre `UnitOfWork()` que crea una sesión por método invocado.

**Costo**: una nueva session por método público invocado, en lugar de una por request. Si un endpoint llamara dos métodos del mismo service (no es el caso post-refactor del double-read), serían dos sessions. **No es un problema en este scope** porque:
- El double-read se colapsa: cada endpoint llama exactamente un método del service.
- Crear una session nueva en SQLAlchemy es barato (es un `Session()` sobre el engine, no abre conexión TCP — la conexión la toma del pool al primer uso).

### Trade-off 2 — Spec del integrador desviada

Spec dice "router abre with"; código adopta "service abre with". Esta es la decisión arquitectónica explícita del proyecto. Documentada en `proposal.md` y aquí.

**Costo**: si la cátedra o un revisor externo esperaba el patrón de la spec, hay que justificarles la desviación. Justificación: clean architecture pura, encapsulación del caso de uso, eliminación del double-read. La justificación está en este documento y queda como evidencia auditable.

## Migration Plan

### Step 1 — Core + Conftest (bloqueante, no migra services aún)

1. Editar `backend/shared/unit_of_work.py`: agregar `__enter__`/`__exit__`. Cambiar `__init__` a la versión backward-compat (acepta `Session`, `Callable` o `None`).
2. NO eliminar `get_uow` todavía.
3. Editar `backend/tests/conftest.py`: AGREGAR la fixture `_patch_uow_session_factory` (autouse). MANTENER el `app.dependency_overrides[get_uow] = override_get_uow` por ahora.
4. Reescribir `backend/tests/integration/test_conftest_overrides.py` para verificar AMBOS overrides (el legacy `get_uow` y el nuevo monkeypatch). Después del Step 3 se simplifica.
5. Correr suite completa — 256/256 deben seguir verdes.
6. Commit: `refactor(uow): add context manager protocol and self-creating session`

### Step 2 — Migrar features uno a uno

Para cada feature en orden (categories → ingredients → products → users → addresses):

1. Refactor `<feature>/service.py`: cambiar `__init__(self, uow)` a `__init__(self)`. Cada método público envuelve su lógica en `with UnitOfWork() as uow:` con `register_repository` dentro del with.
2. Refactor `<feature>/router.py`: eliminar `Depends(get_uow)` de cada endpoint. Cambiar `Service(uow)` por `Service()`. Eliminar `uow.commit()`.
3. Para `products` y `users`: colapsar el double-read pattern (el método del service devuelve la entidad ya hidratada).
4. Correr tests de la feature → todos verdes.
5. Correr suite completa → 256/256 verdes.
6. Commit: `refactor(<feature>): move uow lifecycle from router to service`

### Step 3 — Cierre

1. Eliminar `get_uow` de `backend/dependencies.py`.
2. Simplificar `__init__` del UoW (eliminar la rama backward-compat de aceptar `Session` directa). La firma final es `__init__(self, session_factory: Optional[Callable] = None)`.
3. Eliminar `app.dependency_overrides[get_uow] = override_get_uow` del conftest (ya no existe `get_uow`). Eliminar la función `override_get_uow`.
4. Simplificar `test_conftest_overrides.py` para verificar solo el monkeypatch.
5. Correr suite completa → 256/256.
6. Commit: `refactor(uow): remove get_uow dependency and legacy session injection`

### Rollback

Cada step / sub-step es un commit atómico. Si un sub-step de Step 2 rompe tests, `git revert` de ese commit deja el resto del progreso intacto. Step 3 solo se ejecuta cuando los 5 features están migrados — su revert deja a los services con el patrón nuevo y la rama backward-compat del UoW activa, sin pérdida de datos.

## Open Questions

- **¿Qué hacer si un test que NO está en `test_<feature>.py` toca un service del scope?** No se observa ningún test cross-feature en la suite actual. Si aparece, se trata como cualquier test del feature: debe pasar después del refactor sin modificación.
- **¿Cambia la performance?** Estimado: nula o positiva. La sesión de DB se abre y cierra por método invocado, igual que antes (antes la abría `get_uow`, ahora la abre `UnitOfWork()`). Crear `Session` es O(1). El pool de conexiones no se altera.
- **¿`get_db` sigue existiendo?** Sí — auth lo usa. Permanece en `backend/shared/database.py` sin cambios.
