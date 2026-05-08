## Context

El conftest de pytest (`backend/tests/conftest.py`) configura un harness de tests con dos primitivas:

1. Un engine SQLite in-memory con `StaticPool` y `check_same_thread=False` (`test_db_engine` fixture, scope function).
2. Una sesión envuelta en `connection.begin()` + `sessionmaker(bind=connection)` (`test_db_session` fixture). El patrón usa rollback explícito de la transaction al final → cada test queda aislado y la base no persiste cambios entre tests.

El fixture `client` (función) hace dependency override:

```python
def override_get_db():
    yield test_db_session

app.dependency_overrides[get_db] = override_get_db
```

Esto funciona perfecto para routers que declaran `db: Session = Depends(get_db)`. Pero los routers de `categories` (y todos los futuros que usen UoW) declaran `uow: UnitOfWork = Depends(get_uow)`. La función `get_uow` en `backend/dependencies.py` es:

```python
def get_uow() -> Generator[UnitOfWork, None, None]:
    session = get_session_factory()()   # <-- crea su PROPIA sesión
    uow = UnitOfWork(session)
    try:
        yield uow
    except Exception:
        uow.rollback()
        raise
    finally:
        uow.close()
```

`get_session_factory()` (en `backend/shared/database.py`) construye un `sessionmaker` ligado a `get_engine()`, que a su vez lee `DATABASE_URL` del entorno (con fallback a `backend.config.settings.DATABASE_URL`). En pytest, sin `.env` cargado y sin `DATABASE_URL` exportado, eso resuelve al default `postgresql://...@localhost:5432/...` y la primera query lanza `OperationalError: Connection refused`.

**Trace del bug (request real):**
```
TestClient.get("/api/v1/categorias")
  → FastAPI resuelve dependencias del endpoint
  → Depends(get_uow) → get_uow() corre normal (NO está overriden)
  → get_session_factory()()         # construye sesión nueva
  → bind=get_engine()                # engine apuntando a Postgres real
  → session.query(...) en el service
  → psycopg2.OperationalError: connection refused 127.0.0.1:5432
```

El override de `get_db` está intacto, pero ningún endpoint de `categories` lo usa.

## Goals / Non-Goals

**Goals:**

- Que el TestClient pueda invocar cualquier endpoint que use `Depends(get_uow)` y la sesión real sea la SQLite del fixture `test_db_session`.
- Que el suite `pytest backend/tests/integration/test_categories.py -v` pase de 2/31 a 31/31 (siempre que no haya OTROS bugs no relacionados — ver "Si el suite no pasa después del fix").
- Tener un test de regresión que falle si alguien rompe el override en el futuro.
- Mantener el aislamiento transaccional entre tests (cada test ve la base limpia).

**Non-Goals:**

- Reescribir `get_uow` para que sea overriden-friendly desde el código de la app. La app está bien; solo necesita un override en tests, igual que `get_db`.
- Tocar `backend/shared/database.py` o `backend/shared/unit_of_work.py`. La infra de la app es correcta.
- Agregar fixtures nuevas (sample_user, sample_roles, etc. ya existen).
- Resolver bugs latentes en el código de `categories` que NO sean este connection-refused. Si aparecen al correr el suite post-fix, se reportan en el apply summary, no se arreglan acá.
- Cargar `.env` en pytest (workaround más frágil que el override; además ocultaría el bug en lugar de arreglarlo).

## Decisions

### Decisión 1 — Construir el UoW con `test_db_session` directamente

**Elegida:**

```python
from backend.dependencies import get_uow
from backend.shared.unit_of_work import UnitOfWork

def override_get_uow():
    uow = UnitOfWork(test_db_session)
    try:
        yield uow
    except Exception:
        uow.rollback()
        raise
    # NO uow.close() — el cierre lo hace el fixture test_db_session

app.dependency_overrides[get_uow] = override_get_uow
```

**Por qué:** comparte la misma sesión que el resto de fixtures (`sample_user`, `sample_roles`, `auth_headers`). Lo que el test inserta vía `test_db_session.add(...)` queda visible para los endpoints, y viceversa. Es la única manera de mantener visibilidad transaccional entre el side del test y el side del request.

**Alternativa descartada — crear sesión nueva por request:** romperia la coordinación transaccional. El test setup haría `commit()` en `test_db_session`, pero el endpoint vería su propia sesión sin esos datos (o vería la base SQLite distinta si abrimos otra conexión). Igual que `override_get_db`, queremos que ambos lados compartan sesión.

**Alternativa descartada — patchear `get_session_factory` con `monkeypatch`:** funciona pero es indirecto y frágil ante refactors de `database.py`. El patrón estándar de FastAPI para este caso es `dependency_overrides`, igual que ya usamos para `get_db`.

### Decisión 2 — NO llamar `uow.close()` en el override

**Elegida:** omitir `finally: uow.close()`.

**Por qué:** el fixture `test_db_session` ya hace `session.close()` + `transaction.rollback()` + `connection.close()` en su teardown. Si `override_get_uow` también cerrara la sesión, la siguiente fixture o assertion del test que use `test_db_session` directamente (por ejemplo `test_db_session.refresh(user)` después del request) fallaría con `Session is closed`.

**Alternativa descartada — close defensivo:** rompería tests que mezclan llamadas via TestClient con queries directas a `test_db_session`. Patrón común: `client.post(...)` + `test_db_session.query(Categoria).first()` para verificar persistencia.

### Decisión 3 — Commit/rollback semantics dentro del request

El handler real de `categories` hace `uow.commit()` (que es `session.commit()`). Bajo el patrón `connection.begin()` + `sessionmaker(bind=connection)` de `test_db_session`, ese commit **NO escribe al disco** porque la transacción raíz es `connection.begin()` y el sessionmaker no la posee — el commit del session marca el work como persistido a nivel sesión, pero el `transaction.rollback()` del teardown de `test_db_session` deshace todo igual.

**Validación esperada:** los tests pueden hacer `client.post("/api/v1/categorias", ...)` y luego `test_db_session.query(Categoria).filter(...).first()` y la fila aparece (porque está en la transacción activa). Después del test, esa fila desaparece (porque la transaction raíz se rollbackea).

**Fallback si SAVEPOINT/sessionmaker no se comporta como esperamos:** en SQLAlchemy 2.0 hay sutilezas con sessionmaker bindeado directo a connection vs `Session(bind=connection)`. Si al correr `test_categories.py` aparecen errores tipo `Transaction already deassociated` o "data not visible across session.commit()", el path alternativo es:

```python
# En test_db_session fixture, cambiar a join_transaction_mode="create_savepoint"
session = sessionmaker(
    autocommit=False,
    autoflush=False,
    bind=connection,
    join_transaction_mode="create_savepoint",   # SQLAlchemy 2.x
)()
```

O usar el patrón `nested=True` con `connection.begin_nested()` + listener `after_transaction_end`. **El agente del apply elige el path tras correr los tests reales.** Documentar acá ambos caminos para que el apply no improvise.

### Decisión 4 — Test de regresión en archivo nuevo

**Elegida:** crear `backend/tests/integration/test_conftest_overrides.py` con un test focused.

**Por qué:** el bug existe porque NO había test que validara la infra. Aislar el test en un archivo dedicado lo hace fácil de encontrar (alguien que toque `conftest.py` lo va a ejecutar primero). Mezclarlo con `test_categories.py` dispersa la responsabilidad: el test no es sobre el comportamiento de categorías, es sobre el override del DI.

**Test propuesto:** `test_get_uow_uses_test_db_session_not_real_postgres`:

```python
def test_get_uow_uses_test_db_session_not_real_postgres(client, test_db_session):
    """Regression: get_uow MUST be overridden so requests use the SQLite
    test session, not a real Postgres connection.

    Before fix: this test would fail with OperationalError (connection refused
    to localhost:5432) because get_uow bypasses dependency_overrides[get_db].

    After fix: this returns 200 with an empty list — confirming the request
    reached the service layer using the in-memory SQLite session.
    """
    response = client.get("/api/v1/categorias")

    # If override is missing, this fails with 500 + connection refused
    # in the response body, or pytest catches the exception during teardown.
    assert response.status_code == 200, (
        f"Expected 200, got {response.status_code}. "
        f"Body: {response.text[:500]}. "
        f"If you see 'connection refused' or 'localhost:5432', "
        f"the get_uow override is missing or broken."
    )
    assert response.json() == []   # base SQLite is empty on each test
```

**Por qué este endpoint:** `GET /api/v1/categorias` es público (sin auth), usa `get_uow`, y retorna lista vacía cuando no hay datos. Es el camino más corto para validar el override sin acoplar el test a fixtures de auth o roles.

### Decisión 5 — Validación de éxito secundaria (no del propose)

Después del fix, correr `pytest backend/tests/integration/test_categories.py -v` y reportar el delta:

- **31/31:** todo bien, el bug era ÚNICAMENTE el override del UoW.
- **<31 con errores tipo connection refused:** el fix está incompleto, revisar.
- **<31 con OTROS errores (validación, lógica de negocio, RBAC, etc.):** el fix funciona pero hay bugs residuales en `categories-backend` que se reportan en el apply summary y se manejan en un change separado (no en éste). Ejemplo: si un test falla porque el service no valida unicidad por nivel, eso es un bug de `categories`, no del conftest.

**Cómo distinguir bug residual nuestro vs bug de categories:**
- Si el error menciona "connection", "OperationalError", "psycopg2", "localhost", "5432" → es nuestro fix incompleto.
- Si el error es `AssertionError`, `400`, `403`, `409`, `ValidationError`, `IntegrityError sin connection` → es bug del código de categories.

## Risks / Trade-offs

- **Riesgo:** el override comparte la `test_db_session` entre el test y los requests del TestClient. Si el código del endpoint cierra la sesión o rebindea el engine, el fixture posterior rompe. → **Mitigación:** ningún router actual cierra la sesión (es el patrón estándar de FastAPI; el cierre lo gestiona la dependency). Si en el futuro alguien lo hace, el test de regresión lo captura.

- **Riesgo:** SAVEPOINT semantics con SQLAlchemy 2.0 + sessionmaker bindeado a connection puede tener edge cases (ver Decisión 3). → **Mitigación:** documentar el fallback `join_transaction_mode="create_savepoint"` para que el apply lo use sin improvisar.

- **Riesgo:** futuros routers que crean su propio UoW manualmente (sin `Depends(get_uow)`) escapan el override. → **Mitigación:** convención del proyecto es siempre `Depends(get_uow)` en routers. Si alguien viola la convención, es un code review issue, no de tests.

- **Trade-off:** no se solicita centralizar la infraestructura de tests en un capability `testing-infrastructure` ahora. Lo posponemos hasta que el equipo lo necesite. Costo: si reaparece otro bug similar en el futuro, vamos a hacer otro fix puntual sin spec. Beneficio: evitamos over-engineering en un fix de 40 min.

## Migration Plan

No aplica — change interno de tests, no afecta producción ni datos.

**Rollback:** `git revert` del commit. El fix es totalmente aditivo (un import, un override, un archivo nuevo de test). No remueve ni reemplaza código existente.

## Open Questions

Ninguna. Las decisiones están cerradas. La única variable es cuál de los dos paths de SAVEPOINT usar (Decisión 3), y eso se resuelve empíricamente en el apply al correr los tests.
