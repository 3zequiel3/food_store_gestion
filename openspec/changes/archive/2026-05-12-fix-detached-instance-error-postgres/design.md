## Context

El refactor `refactor-uow-to-context-manager` movió la frontera transaccional al patrón `with UnitOfWork() as uow:` dentro de cada service. El router quedó como pasarela fina: instancia el service, llama al método, recibe una entidad ORM y la pasa por `<Entity>Read.model_validate(...)` para construir la respuesta. La firma quedó limpia, pero **se asumió tácitamente que las entidades ORM retornadas sobrevivirían a la salida del `with`** (commit + close) lo suficiente para que Pydantic pueda leer sus atributos.

Esa asunción es VERDADERA cuando el `sessionmaker` se configura con `expire_on_commit=False`. Con el default `True` de SQLAlchemy, `session.commit()` expira todos los atributos cargados, y el subsiguiente `session.close()` deja los objetos detached. Pydantic, al acceder a un atributo, dispara un lazy SELECT contra una sesión cerrada → `DetachedInstanceError` → 500.

El `_UoWSessionFactory` del conftest (`backend/tests/conftest.py:119`) ya tiene `expire_on_commit=False` explícito desde el día uno del refactor, por lo que la suite local **nunca detectó el bug**. Producción quedó con el default. La discrepancia fue silenciada hasta que TestSprite, corriendo contra Postgres real, golpeó TC006 (`PATCH /usuarios/me`) y TC009 (`POST /direcciones/`).

**El refactor anterior no está roto** — está incompleto en su config interna del sessionmaker. Este change cierra ese gap sin tocar arquitectura.

## Goals / Non-Goals

**Goals:**
- Cerrar `DetachedInstanceError` en TODOS los endpoints actuales contra Postgres real.
- Alinear el `sessionmaker` de producción con la config que el conftest ya usa (cierre de brecha tests↔prod).
- Agregar red de seguridad `pg_only` (3 tests) que **falle hoy** y pase con el fix, para bloquear regresión futura a nivel CI cuando se corra el subset Postgres.
- Codificar en spec (`base-entities`) el contrato implícito que el refactor anterior dejó tácito.
- Documentar la convención necesaria para que features futuros (#17 `order-visualization` con relaciones expuestas) no reabran el agujero.

**Non-Goals:**
- Cambiar la arquitectura Router → Service → UoW → Repo → Model (queda 100% intacta).
- Refactorizar services para retornar Pydantic schemas en lugar de ORM (Opción C, rechazada).
- Quitar los `session.refresh(pedido, attribute_names=[...])` defensivos pre-commit en `orders/service.py`.
- Cambiar la red de tests existente: 372/378 verdes locales siguen verdes; el delta son 3 nuevos `pg_only`.
- Re-correr TestSprite externo en CI: el re-run de TC006 y TC009 queda como validación manual al cerrar el change.

## Decisions

### D1 — `expire_on_commit=False` en el `sessionmaker` de producción (Opción A)

**Decisión**: agregar `expire_on_commit=False` al `sessionmaker` en `backend/shared/database.py` (1 línea). Listo.

**Por qué**, contra las alternativas evaluadas en el explore:

| Opción | Archivos tocados | Esfuerzo | Cobertura del bug actual | Riesgo de futuro |
|--------|------------------|----------|--------------------------|-------------------|
| **A — `expire_on_commit=False`** (elegida) | 1 | 30 min | **100%** | Bajo: solo no cubre relaciones lazy nunca cargadas (D4 lo documenta) |
| B — `populate_existing=True` en repos | 5–8 | 2–3 h | Parcial: cubre re-reads, no el CREATE de `DireccionEntrega` ni server-defaults | Alto: olvidar uno en el próximo feature reabre el bug |
| C — Serializar Pydantic dentro del `with` | ~18 (8 services + 10 routers) | 4–6 h | 100% | Rompe principio "service NO conoce schemas Pydantic" |
| D — `session.expunge(instance)` antes de return | 8 (services) | 2 h | Igual cobertura que A | Peor DX: pasos extra en cada service, ruido visual |
| E — Híbrida A + verificar eager-loads | 1 + auditoría | 1 h | 100% | Idéntico a A; la auditoría ya está implícita en D4 |

**Por qué A es seguro pese al default SQLAlchemy `True`**: el default existe para prevenir **stale reads** post-commit en sesiones largas. El patrón UoW de este proyecto tiene sesión **ultracorta**: 1 request = 1 commit + close inmediato. No hay código que lea atributos de una entidad después de un commit Y antes del close (`__exit__` los encadena). No hay sesiones daemon de larga duración. Stale-read risk: cero práctico.

**Cobertura confirmada del 100% para el codebase actual** (verificado en el explore):
- `Usuario.roles` (M2N expuesto en `ProfileResponse`): ya se eager-loadea con `selectinload` en `find_by_id_with_roles`. Con `expire_on_commit=False`, sobrevive al commit.
- `DireccionEntrega`: solo scalars en `DireccionRead`. Cubierto.
- `Pedido`: `PedidoRead` solo accede a scalars + server-defaults. Cubierto.
- `Producto`: `ProductoRead` solo scalars. Cubierto.
- `Categoria`, `Ingrediente`: solo scalars. Cubierto.

### D2 — NO tocar `auth/dependencies.py::get_current_user` ni `orders/service.py::avanzar_estado`

Ambos abren sesión directa (sin UoW) vía `get_session_factory()()` o `_uow_mod.get_session_factory()()`. Son paths **read-only**: nunca commitean. Bajo el nuevo default `expire_on_commit=False` heredan la config sin riesgo (irrelevante para reads puros). Cero esfuerzo, cero riesgo.

### D3 — Mantener los `session.refresh(..., attribute_names=[...])` defensivos en `orders/service.py`

`crear_pedido` hace `session.refresh(pedido, attribute_names=["creado_en"])` pre-commit. `transicionar_estado` hace `session.refresh(pedido, attribute_names=["estado_codigo", "creado_en"])` pre-commit. Estos refresh resuelven **server-defaults** (timestamps `TIMESTAMPTZ default now()`, `estado_codigo` con default `'PENDIENTE'`) que SQLAlchemy desconoce hasta que la fila exista en DB.

Con `expire_on_commit=True` actual eran **insuficientes** (el commit posterior re-expira todo igual). Con `expire_on_commit=False` quedan como **reads explícitos del valor server-default**: sin ellos, el atributo es `None` en la instancia ORM porque la fila se insertó con NULL y la base lo defaulteó. Cambia el **significado** del refresh: de "anti-DetachedInstanceError fallido" → "lectura explícita de server-default". Se documenta el cambio de significado en el commit y en código mediante comentario.

**No se remueven** porque su rol cambia, no desaparece.

### D4 — Convención nueva a documentar: eager-load de relaciones expuestas en response schemas

`expire_on_commit=False` mantiene en memoria los atributos que YA estaban cargados al momento del commit. **No carga relaciones que nunca se tocaron**. Si un response schema futuro expone una relación lazy y el repo no la eager-loadea, Pydantic intentará lazy-load post-commit y volverá a tirar `DetachedInstanceError` (esta vez por relación, no por escalar).

**Convención**: todo response schema que exponga una relación M2N o 1:N DEBE eager-loadearla en el repo (vía `selectinload`, `joinedload`, o equivalente) ANTES de que el `UoW.__exit__()` corra. Se codifica como Scenario en la spec delta (`Relationships exposed in a response schema are eager-loaded by the repo`).

Caso futuro identificado en el explore: **#17 `order-visualization`** va a exponer `Pedido.items`, `Pedido.pagos` o `Pedido.historial`. Ese change DEBE eager-loadear esas relaciones en su repo nuevo, no apoyarse en `expire_on_commit=False`.

### D5 — La verdad de la config vive en producción; el conftest es ESPEJO, no excepción

Hoy, leer `conftest.py:119` con `expire_on_commit=False` parece un workaround para que los tests pasen. Después de este change, **producción es la fuente de verdad** y el conftest la replica para asegurar paridad. Se agrega un comentario explicativo arriba del `_UoWSessionFactory` en el conftest para que un lector futuro entienda que **borrar esa línea rompería la paridad tests↔prod**, no que es una concesión a SQLite.

### D6 — Spec delta: Opción A (MODIFICAR `base-entities`) por sobre Opción B (skip)

**Decisión tomada en la `proposal.md`**: el contrato "los objetos retornados por un service deben sobrevivir al commit del UoW para serialización" estaba implícito en el refactor anterior. El bug demostró que un contrato implícito es frágil: el próximo refactor del sessionmaker (o el próximo feature que exponga una relación lazy) puede romperlo silenciosamente otra vez.

Se MODIFICA el Requirement existente "Double-read pattern SHALL be collapsed into a single service call" en `base-entities` agregando:
- Texto normativo nuevo que define el contrato post-commit.
- 3 Scenarios nuevos `pg_only`-style que mapean 1:1 a los 3 tests de regresión.
- 1 Scenario que codifica D1 (la config del sessionmaker).
- 1 Scenario que codifica D4 (la convención de eager-load).

Costo: 1 capability (transversal) en lugar de 8 (feature-por-feature). Beneficio: cualquier review futuro contra spec va a fallar si alguien revierte `expire_on_commit` o expone una relación lazy sin eager-load.

## Risks / Trade-offs

### R1 — `get_current_user` hereda `expire_on_commit=False`

→ **Mitigación**: read-only path, nunca commitea. La nueva config es irrelevante para reads puros. Cero acción requerida.

### R2 — `avanzar_estado` ídem

→ **Mitigación**: mismo análisis que R1. Sesión de lectura directa, no UoW. Sin riesgo.

### R3 — Tests existentes que asuman `expire_on_commit=True`

→ **Mitigación**: el explore verificó que 0 tests del proyecto dependen del default `True`. El conftest YA usa `False`, por lo que los 372/378 tests verdes corren ya con esa config. Confidence alto.

### R4 — Relaciones lazy expuestas en response schemas futuros

→ **Mitigación**: documentado como D4 + codificado como Scenario en spec delta. Trade-off explícito: `expire_on_commit=False` no es un comodín universal; cubre escalares y relaciones cargadas, no relaciones nunca tocadas. Cualquier feature futuro que viole la convención fallará en code review contra spec.

### R5 — Sigue overhead defensivo en `orders/service.py`

→ **Mitigación**: `session.refresh(..., attribute_names=[...])` pre-commit queda como lectura explícita de server-default (cambia su significado, no su comportamiento). Costo: 1 SELECT extra por orden creada / transicionada (idéntico al pre-fix, costo neto cero). Beneficio: el campo `creado_en` / `estado_codigo` queda poblado en la instancia ORM sin depender del comportamiento de `default=None` en cliente. Comentario en código aclara el rol nuevo.

### R6 (nuevo) — TestSprite externo no automatizable en este change

→ **Mitigación**: el TC006 / TC009 re-run requiere backend corriendo + cuenta TestSprite + tiempo de polling. Queda como Step 5 manual de `tasks.md`. Los 3 tests `pg_only` nuevos cubren el mismo caso a nivel pytest + Postgres local, dando red de seguridad ANTES de re-correr TestSprite. Si los 3 `pg_only` pasan y el explore es correcto, TestSprite va a pasar también — pero la validación final queda registrada como manual.

### R7 (trade-off explícito) — Bypass del default SQLAlchemy

→ **Aceptado**: el default `expire_on_commit=True` existe para casos donde la sesión sobrevive al commit (uso de objetos post-commit en código de aplicación largo). Este proyecto no tiene ese patrón. Si en el futuro se introduce (ej. un worker que reusa sesiones), habrá que revisar esta decisión. Documentado como nota en el comentario del `database.py`.

## Migration Plan

Cambio backwards-compatible a nivel API: no afecta clients ni schema DB ni migraciones Alembic. No hay rollback de datos.

**Deploy**:
1. Merge del PR del change.
2. Backend levanta con `expire_on_commit=False` desde el siguiente request.
3. No requiere reinicio en orden particular, ni feature flag, ni warmup.

**Rollback**: revertir el commit. Los endpoints vuelven al estado pre-fix (DetachedInstanceError contra Postgres). El rollback no rompe nada nuevo; solo reintroduce el bug original. Bajo riesgo.

## Open Questions

Ninguna. El explore cerró todas las decisiones técnicas; el único punto abierto (spec delta A vs B) se resolvió como **A** con justificación en `proposal.md` y D6.
