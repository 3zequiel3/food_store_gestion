# Proposal: refactor-uow-to-context-manager

## Why

Hoy el lifecycle del `UnitOfWork` (apertura de sesión, `commit()`/`rollback()`, `close()`) vive en los routers via `Depends(get_uow)`. Esto **mezcla preocupaciones HTTP con la responsabilidad transaccional del caso de uso** y genera deuda técnica reconocida explícitamente en los `design.md` archivados de los 5 changes de feature (categories, ingredients, products, users, addresses) — todos ellos documentan que "el commit lo hace el router (D6)" como decisión pragmática a corregir.

El precio que se paga:

- **5 services con `__init__(uow)` acoplado al objeto transaccional** — el service no puede ejecutarse sin que alguien externo le inyecte la transacción, lo que rompe el principio de que un caso de uso es atómico y self-contained.
- **2 endpoints con "double-read pattern"** (`products/router.py:248-274` `set_categorias` y `users/router.py:77-80` `update_profile`) que llaman al service, hacen `uow.commit()`, y luego vuelven a llamar al service para releer la entidad post-mutación. El router orquesta dos transacciones lógicas porque el service no puede devolver el resultado completo.
- **28 ocurrencias de `Depends(get_uow)` y 20 de `uow.commit()`** repetidas a lo largo de los routers. Boilerplate que cada nuevo endpoint copia.
- **`get_uow` como Depends** opaca la frontera de la transacción: un developer que lee el router no ve dónde empieza ni dónde termina la unidad de trabajo.

El refactor traslada la responsabilidad transaccional **al service** (que es quien representa el caso de uso) usando `UnitOfWork` como context manager. El router queda libre de Depends transaccionales y de `commit()` manuales.

> **Desviación intencional de spec del integrador §7.1.** La spec canónica dice explícitamente "Router abre contexto: `with UnitOfWork() as uow:` — llama service.crear_pedido(uow, body, usuario_id)" (paso 2 del flujo "Crear Pedido"). Este change se desvía de esa indicación con justificación arquitectónica: en clean architecture pura, la transacción es parte del caso de uso (capa service), no del adapter HTTP (capa router). El integrador define un patrón válido pero no óptimo; el proyecto adopta el patrón puro y documenta la desviación aquí.

## What Changes

### Estructura del UnitOfWork

- **MODIFIED**: `UnitOfWork.__init__()` acepta `session_factory: Optional[Callable] = None`. Si es `None`, llama internamente a `get_session_factory()` y crea su propia sesión. Ya no recibe `Session` externa.
- **ADDED**: `UnitOfWork.__enter__(self) -> UnitOfWork` — retorna `self` para uso con `with`.
- **ADDED**: `UnitOfWork.__exit__(self, exc_type, exc_val, exc_tb)` — `commit()` si no hubo excepción, `rollback()` si la hubo, `close()` siempre en `finally`. Retorna `False` (no suprime excepciones).
- `commit()` / `rollback()` / `close()` / `register_repository()` / `__getattr__()` se mantienen sin cambios.

### Eliminación del Depends transaccional

- **REMOVED**: `get_uow()` desaparece de `backend/dependencies.py` por completo. Los routers ya no reciben `UnitOfWork` por inyección de FastAPI.

### Patrón nuevo en los 5 services del scope

Cada service:
- `__init__(self)` — sin argumentos.
- Cada método público abre `with UnitOfWork() as uow:`, registra sus repositories dentro del `with`, ejecuta la lógica, y devuelve el resultado. El `__exit__` se encarga del commit.

### Patrón nuevo en los 5 routers del scope

Cada endpoint:
- Elimina `uow: UnitOfWork = Depends(get_uow)`.
- Elimina `uow.commit()` manual.
- Cambia `Service(uow)` por `Service()`.

### Resolución del double-read pattern

- **`products.set_categorias`**: el service envuelve el reemplazo de pivote + el `get_detail` en un único `with` y devuelve el `ProductoDetail` final. El router NO vuelve a llamar al service.
- **`users.update_profile`**: el service ejecuta el update y devuelve el perfil ya hidratado dentro del mismo `with`. El router NO hace re-read.

### Test infrastructure

- **REMOVED**: el override `app.dependency_overrides[get_uow]` del conftest desaparece (ya no existe `get_uow`).
- **ADDED**: fixture `autouse=True` en `backend/tests/conftest.py` que aplica `monkeypatch` sobre `backend.shared.unit_of_work.get_session_factory` para que `UnitOfWork()` (cuando el service lo invoca internamente) reciba la `test_db_session` SQLite en lugar de abrir conexión a Postgres.
- **MODIFIED**: `backend/tests/integration/test_conftest_overrides.py` se reescribe para verificar el nuevo monkeypatch (que `get_session_factory` apunta a la fixture de test).

### Out-of-scope (deuda técnica diferida)

- `auth/service.py` y `auth/router.py` — usan `Session` directa via `Depends(get_db)`, patrón distinto al UoW. Se difiere a un change separado para no inflar este scope. Documentado en `design.md` § "Auth fuera de scope".
- Frontend, otros servicios externos, otros módulos.

## Capabilities

### New Capabilities

(Ninguna nueva — refactor estructural)

### Modified Capabilities

- `base-entities`: agregar requirements explícitos sobre el ciclo de vida del UnitOfWork como context manager y la regla de que "el service es responsable de la transacción, no el router". Hoy el spec habla de modelos y BaseRepository pero no menciona el patrón transaccional — esta delta lo hace explícito y consistente con el código.

## Impact

### Código de producción afectado (12 archivos)

| Archivo | Cambio |
|---|---|
| `backend/shared/unit_of_work.py` | `__enter__` / `__exit__`, self-creating session, `session_factory` opcional |
| `backend/dependencies.py` | Eliminar `get_uow` |
| `backend/features/categories/service.py` | 4 métodos envueltos en `with` |
| `backend/features/categories/router.py` | 4 endpoints sin `Depends(get_uow)` ni `uow.commit()` |
| `backend/features/ingredients/service.py` | 5 métodos envueltos en `with` |
| `backend/features/ingredients/router.py` | 5 endpoints sin `Depends(get_uow)` ni `uow.commit()` |
| `backend/features/products/service.py` | 12 métodos envueltos en `with` + colapso double-read en `set_categorias` |
| `backend/features/products/router.py` | 11 endpoints sin `Depends(get_uow)` ni `uow.commit()` |
| `backend/features/users/service.py` | 3 métodos envueltos en `with` + colapso double-read en `update_profile` |
| `backend/features/users/router.py` | 3 endpoints sin `Depends(get_uow)` ni `uow.commit()` |
| `backend/features/addresses/service.py` | 5 métodos envueltos en `with` |
| `backend/features/addresses/router.py` | 5 endpoints sin `Depends(get_uow)` ni `uow.commit()` |

### Test infrastructure afectado (2 archivos)

| Archivo | Cambio |
|---|---|
| `backend/tests/conftest.py` | Eliminar override `get_uow`, agregar fixture `autouse` con monkeypatch de `get_session_factory` |
| `backend/tests/integration/test_conftest_overrides.py` | Reescribir para verificar monkeypatch (no override) |

### Conteo mecánico

- ~28 ocurrencias de `Depends(get_uow)` eliminadas en routers.
- ~20 ocurrencias de `uow.commit()` eliminadas en routers.
- 5 services con `__init__` simplificado a `__init__(self)`.
- 2 cases de double-read colapsados a 1 sola llamada al service.

### Tests

256 tests ya existentes. **No se agregan tests nuevos** — el refactor es comportamentalmente neutro. Se valida con la suite existente:
- `test_categories.py` (31), `test_ingredients.py` (39), `test_products.py` (89), `test_user_profile.py` (34), `test_delivery_addresses.py` (36) — los 229 tests de feature deben seguir verdes.
- `test_auth.py` (15), `test_base_repository.py` (8) — no deben verse afectados (auth fuera de scope, base_repository no usa UoW).
- `test_conftest_overrides.py` (1) — se reescribe.

### APIs externas

**Ninguna.** El contrato HTTP de cada endpoint (paths, request schemas, response schemas, status codes) queda **idéntico**. El cliente del API (frontend) no detecta el cambio.

### Estimación

**5.5 horas** = 1.5 h Step 1 (core + conftest) + 3 h Step 2 (5 modules secuenciales) + 1 h buffer / debugging.

### Riesgos principales

- **Conftest monkeypatch mal aplicado** — si la fixture `autouse` no engancha correctamente, los services intentarían abrir conexión a Postgres y los 229 tests de feature fallarían. Mitigación: validar el conftest en Step 1 antes de tocar ningún service (Step 1 corre los 256 tests sin que ningún service haya migrado todavía).
- **Double-read pattern roto** — al colapsar `set_categorias` y `update_profile`, los responses pueden cambiar sutilmente (objeto hidratado dentro del mismo `with` vs. reread post-commit). Mitigación: tests existentes cubren ambos escenarios; si pasan, el contrato se respeta.
- **Auth fuera de scope** — si alguien intenta migrar auth en el mismo change, se duplica el alcance. Mitigación: explicitar el scope en `design.md` y `tasks.md`.
