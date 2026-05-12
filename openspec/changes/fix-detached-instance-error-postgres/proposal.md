## Why

TestSprite, corriendo contra Postgres real, detectó `DetachedInstanceError` 500s en `PATCH /usuarios/me` (TC006) y `POST /direcciones/` (TC009). El bug es sistémico: el `sessionmaker` de producción en `backend/shared/database.py` no fija `expire_on_commit=False`, por lo que SQLAlchemy usa el default `True`. Tras `UoW.__exit__()` (`commit()` + `close()`), todos los objetos ORM retornados por los services quedan **detached + expired**, y cuando el router llama `model_validate(obj)` Pydantic dispara un lazy-load contra una sesión cerrada → 500.

La suite local con SQLite **no detecta el bug** porque `backend/tests/conftest.py:119` ya define `expire_on_commit=False` explícitamente en el `_UoWSessionFactory`. Es decir, el conftest tenía el comportamiento correcto desde el día uno; producción quedó en deuda. Este change cierra esa brecha silenciosa.

## What Changes

- **Producción**: agregar `expire_on_commit=False` al `sessionmaker` en `backend/shared/database.py` (1 línea).
- **Tests (conftest)**: agregar comentario en `backend/tests/conftest.py:119` aclarando que el `expire_on_commit=False` allí **espeja la config de producción** y NO es un workaround para tests.
- **Tests de regresión nuevos** (`pg_only`, 3 casos): validan contra Postgres real que `PATCH /usuarios/me`, `POST /direcciones/` y `POST /pedidos/` retornan 2xx con response body bien serializado — bloquean la regresión a nivel CI cuando se corra el subset `pg_only`.
- **Convención nueva a documentar**: todo response schema que exponga una relación M2N debe eager-loadearla en el repo (no apoyarse en lazy + `expire_on_commit=False`, que no la cubre).
- **NO se modifica**: ningún router, ningún service, ningún schema Pydantic, ningún repo. La arquitectura Router → Service → UoW → Repo → Model del refactor anterior queda **100% intacta**; este fix solo corrige config interna del sessionmaker.

## Capabilities

### New Capabilities

<!-- Ninguna. Este es un fix de infraestructura que no introduce comportamiento nuevo. -->

### Modified Capabilities

- `base-entities`: documenta un contrato implícito heredado del refactor `refactor-uow-to-context-manager`: **los objetos ORM retornados por un service tras `UoW.__exit__()` deben permanecer utilizables para serialización en el router** (Pydantic `model_validate(obj)` no debe disparar lazy-load ni `DetachedInstanceError`). Hasta hoy ese contrato existía solo en la cabeza del autor del refactor; la spec de cada feature (`user-profile`, `delivery-addresses`, `order-creation`, etc.) lo asume tácitamente al definir endpoints que devuelven `<Entity>Read`. Se consolida acá, en `base-entities`, porque es transversal a toda entidad ORM del sistema y no pertenece a ninguna feature individual.

> **Decisión de spec delta**: se eligió la **Opción A** (modificar `base-entities`) sobre la Opción B (skip delta, tratar el change como fix puro de infra) porque el bug demostró que el contrato implícito era frágil. Codificarlo en spec previene que un refactor futuro vuelva a romperlo silenciosamente. El costo es 1 Requirement MODIFIED en una sola capability transversal — más barato que reabrir 8 specs feature-por-feature.

## Impact

**Código afectado** (surface mínima):
- `backend/shared/database.py` — 1 línea agregada al `sessionmaker`.
- `backend/tests/conftest.py` — 1 comentario explicativo (no cambia comportamiento; el `expire_on_commit=False` ya estaba allí).
- 3 tests nuevos `pg_only` (sin red de seguridad existente para este caso).

**Código NO afectado** (verificado contra el explore):
- `auth/dependencies.py::get_current_user` — usa `get_session_factory()()` directo, lectura pura, no commitea → seguro bajo `expire_on_commit=False`.
- `orders/service.py::avanzar_estado` — abre sesión de lectura directa, idem.
- `orders/service.py::crear_pedido` / `transicionar_estado` — los `session.refresh(pedido, attribute_names=[...])` pre-commit existentes quedan como reads defensivos de server-defaults (`creado_en`, `estado_codigo`). NO se remueven; cambia su **significado** (ya no son anti-DetachedInstanceError, son anti-server-default-not-loaded).
- Todos los routers que hacen `<Entity>Read.model_validate(...)` post-UoW.
- 372/378 tests verdes locales (no asumen `expire_on_commit=True`; verificado en el explore).

**APIs/contratos**: cero cambios. Misma firma de endpoints, mismos response bodies, mismos status codes — pero ahora los endpoints **funcionan en Postgres** sin tirar 500.

**Dependencias / sistemas externos**: ninguno.

**Riesgo de stale read** (motivo por el que SQLAlchemy default `expire_on_commit=True`): teórico cero en este proyecto. El patrón UoW es de **sesión ultracorta**: 1 request = 1 commit + close inmediato. No hay código que lea atributos de una entidad después de un commit y antes del close; tampoco hay sesiones largas tipo daemon que necesiten refrescar estado tras commit.

**Estimación**: 1.5–2h end-to-end (3 tests rojos → fix de 1 línea → tests verdes → re-run manual de TestSprite externo).

**Validación final**: TC006 y TC009 de TestSprite deben pasar contra el backend con el fix aplicado (requiere correr TestSprite manualmente — no automatizable en este change).
