## Why

Durante el audit de `categories-backend` (8 may 2026) descubrimos un bug del setup de tests: 29 de los 31 tests del módulo fallan con `OperationalError: connection to server at "localhost", port 5432 failed: Connection refused` aun cuando `backend/tests/conftest.py` configura SQLite in-memory. El conftest hace `app.dependency_overrides[get_db] = override_get_db`, pero los routers de `categories` usan `Depends(get_uow)` — y `get_uow` (en `backend/dependencies.py:39`) instancia su propia sesión vía `get_session_factory()()`, esquivando por completo el override del DI. Esa session factory lee `DATABASE_URL` del entorno y, sin `.env` cargado en pytest, intenta conectar al Postgres real. Resultado: el suite cae apenas pega un endpoint que toca DB. **Los 2 tests que pasan son los que retornan 401/403 antes de tocar la sesión** (no es coincidencia; son los únicos que no entran al `get_uow`).

Hay que fixearlo ahora porque (a) bloquea la validación CI de `categories-backend` antes de archivar, y (b) cualquier futuro módulo que use UoW (todos los del Sprint 2 en adelante: products, orders, inventory) heredaría el mismo problema silencioso.

## What Changes

- Agregar override de `get_uow` en `backend/tests/conftest.py` dentro del fixture `client`. El `UnitOfWork` se construye con la **misma `test_db_session`** ya en uso (sesión SQLite con transaction wrapper para aislamiento), garantizando que todos los endpoints usen la base de tests sin importar qué dependency declaren (`get_db` o `get_uow`).
- Importar `get_uow` desde `backend.dependencies` en el conftest.
- **NO se cierra** la sesión dentro del `override_get_uow` — el ciclo de vida lo maneja el fixture `test_db_session` (cierre + rollback de transaction al final del test). Cerrarla dos veces rompería el patrón `connection.begin()` + sessionmaker.
- Test de regresión nuevo en `backend/tests/integration/test_conftest_overrides.py` que verifica el override: pega `GET /api/v1/categorias` (endpoint público que usa `get_uow`) y confirma que la app NO intenta conectar a Postgres real.
- **Sin cambios** en `backend/dependencies.py`, `backend/shared/database.py`, ni `backend/shared/unit_of_work.py`. El bug es de la infraestructura de tests, no de la app.

## Capabilities

### New Capabilities

Ninguna. Este change toca exclusivamente configuración de tests (`backend/tests/conftest.py` + un test nuevo de regresión). No introduce ni modifica comportamiento del producto, no expone nuevos endpoints, no cambia contratos de API ni reglas de negocio.

### Modified Capabilities

- `backend-setup`: el requirement `pytest integration` ya cubre "el sistema SHALL configurarse para tests con pytest y fixtures de base de datos". Este change **agrega scenarios** sobre el contrato del harness para `get_uow`:
  - El override de `get_uow` debe redirigir al `test_db_session` (al igual que `get_db`).
  - TestClient y queries directas a `test_db_session` comparten visibilidad transaccional.
  - El aislamiento entre tests se mantiene aun cuando el endpoint hace `uow.commit()`.

  No hay change de comportamiento del requirement principal — es una **clarificación** del contrato existente del harness para evitar el agujero que el bug expuso. Por eso es `MODIFIED Requirements` (extender scenarios), no `ADDED`.

## Impact

**Código afectado:**
- Modificación: `backend/tests/conftest.py` (~5 líneas: import + override_get_uow + registro).
- Nuevo: `backend/tests/integration/test_conftest_overrides.py` (1 test).
- **No se toca:** `backend/dependencies.py`, `backend/shared/database.py`, `backend/shared/unit_of_work.py`, `backend/main.py`, ningún router, ningún service, ningún model.

**Riesgo:** muy bajo. Cambio local al harness de tests. La única forma de romper algo es si algún test existente dependía implícitamente del comportamiento bugueado (improbable, pero el suite de auth — que sí pasa hoy — lo confirmará al re-correr).

**Dependencias:** ninguna.

**Bloqueado por este change:**
- Validación final del suite de `categories-backend` antes de archivar (objetivo: 31/31 tests pasando).
- Cualquier change futuro que use `get_uow` en routers (products, orders, inventory, payments).

**Roadmap:** este change NO está en `docs/CHANGES.md` porque es un fix de infraestructura de tests descubierto por un audit, no un feature de producto. Se ejecuta como mini-change correctivo entre `categories-backend` (en revisión) y el próximo feature del Sprint 2.

**Estimación:** 40 min totales — 10 min code change, 20 min test nuevo, 10 min validación contra `test_categories.py`.
