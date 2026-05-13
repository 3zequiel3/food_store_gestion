## Context

`BaseRepository` (`backend/shared/repository.py`) implementa un patrón de soft delete genérico: detecta si el modelo tiene una columna de "marca de borrado" y, si la tiene, filtra registros eliminados en lecturas y setea el timestamp en `delete()`. Si no la tiene, cae a hard delete.

La detección se hace por `hasattr(model, "deleted_at")` (línea 40), pero la convención del proyecto — establecida en `docs/Integrador.txt` §3, `docs/Descripcion.txt`, RN-CA09 y el spec OpenSpec `base-entities` — es `eliminado_en` (campos en español, alineados con los nombres del ERD v5). `BaseModel` y `PivotBaseModel` (`backend/shared/models.py`) declaran `eliminado_en` correctamente.

**Estado actual del bug**: `_has_deleted_at` evalúa `False` para TODOS los modelos del proyecto. Resultado:

- `_get_base_query` no aplica filtro → `read`, `list`, `count` ven registros borrados.
- `delete()` cae al else-branch (líneas 128-130) y borra físicamente.
- `count()` no descuenta borrados.

**Por qué pasó silencioso**:
1. Auth (único módulo aplicado) no expone `DELETE` HTTP en sus endpoints, así que el path defectuoso nunca se ejecutó en producción.
2. `backend/tests/integration/test_auth.py` y `test_security.py` no llaman `repo.delete()` sobre `Usuario` ni validan que `eliminado_en` se setee.
3. El comportamiento "fall-through a hard delete" pareció tolerable en revisión.

**Por qué fixear ahora**: el change `categories-backend` (en propose) inicialmente incluía una mitigación local (`CategoryRepository` sobrescribía `_get_base_query` y `delete`). Si arreglamos la raíz, esa mitigación desaparece y todos los módulos siguientes heredan el comportamiento correcto sin código defensivo redundante.

## Goals / Non-Goals

**Goals:**
- Hacer que `BaseRepository` cumpla la spec ya aprobada de `base-entities` ("repositories MUST filter WHERE eliminado_en IS NULL by default").
- Detectar regresiones futuras vía tests de integración con cobertura completa de los 4 paths del repo (`read`, `list`, `count`, `delete`).
- Documentar el comportamiento esperado en un Requirement OpenSpec explícito sobre `BaseRepository` (no solo en el modelo).
- Eliminar la deuda silenciosa antes de que más módulos hereden la rama defectuosa.

**Non-Goals:**
- NO refactorizar la API pública del repositorio (`create`, `read`, `update`, `delete`, `hard_delete`, `list`, `count` se mantienen igual).
- NO agregar `query_with_deleted()` (mencionado en docstring de `BaseModel` pero fuera de alcance — se trata en un change futuro si algún caso de uso lo requiere).
- NO cambiar nombres de columnas en modelos (ya son correctos en `BaseModel`).
- NO agregar dependencias nuevas; los tests usan `pytest`/`SQLite` ya configurados en `backend/tests/conftest.py`.

## Decisions

### Decisión 1: Fix raíz vs mitigación local
**Elegido**: fix raíz en `BaseRepository`.
**Alternativa descartada**: dejar la mitigación local en `CategoryRepository` y replicarla en cada módulo nuevo.
**Razón**: la mitigación local viola DRY, perpetúa el bug en `BaseRepository`, y obliga a cada feature futura a recordar el workaround. Costo del fix raíz: 15 min de rename + tests. Costo del workaround: 4-5 mitigaciones locales acumulándose en los próximos 6 meses.

### Decisión 2: Renombrar el atributo privado `_has_deleted_at` → `_has_eliminado_en`
**Elegido**: renombrar.
**Alternativa descartada**: dejar `_has_deleted_at` como nombre interno y solo cambiar el string literal `"eliminado_en"`.
**Razón**: el atributo es privado (prefijo `_`, no exportado), y la consistencia ayuda a futuras búsquedas (`rg "_has_eliminado_en"` debe encontrar el patrón). Riesgo nulo — verificado con `rg "_has_deleted_at" backend/` que solo aparece dentro de `repository.py`.

### Decisión 3: Documentar el invariante en docstring del módulo
**Elegido**: el docstring del módulo (`backend/shared/repository.py` líneas 1-6) y de la clase deben mencionar **`eliminado_en`** explícitamente.
**Razón**: es la primera línea de defensa contra regresión. Un futuro lector que vea "soft delete via deleted_at" en el docstring va a tipear `deleted_at` en su código. El docstring debe reflejar la convención del proyecto.

### Decisión 4: Agregar Requirement OpenSpec explícito sobre `BaseRepository`
**Elegido**: agregar un Requirement nuevo bajo `## ADDED Requirements` en el delta de `base-entities`, con scenarios para cada path (filter en `_get_base_query`, soft delete en `delete()`, fallback a hard delete sin `eliminado_en`).
**Alternativa descartada**: solo arreglar el código y confiar en que el Requirement existente de `eliminado_en` ("is included in default repository filters") sea suficiente.
**Razón**: el scenario actual está embebido como sub-bullet dentro del Requirement de `BaseModel`, no es testeable a nivel del repositorio, y permitió que el bug existiera sin violar la letra del spec. Un Requirement separado con scenarios atómicos hace que la próxima auditoría detecte cualquier regresión.

### Decisión 5: Tests sobre `Usuario` (no fixture nueva)
**Elegido**: usar el modelo `Usuario` (que hereda `BaseModel` con `eliminado_en`) en los tests de soft delete, y el modelo `Rol` (que tampoco hereda `BaseModel`, no tiene `eliminado_en`) para el test de fallback a hard delete.
**Razón**: ambos modelos ya tienen fixtures en `backend/tests/conftest.py` (`sample_user`, `sample_roles`). Reutilizamos infra existente sin agregar fixtures.
**Verificado**: `Rol` (en `backend/features/catalog/models.py`) no hereda `BaseModel` y NO tiene columna `eliminado_en` — sirve para el test 5 sin fabricar un modelo de prueba ad hoc.

## Diff exacto del fix (10 ediciones en `backend/shared/repository.py`)

| Línea | Antes | Después |
|-------|-------|---------|
| 5 | `Includes soft delete support (queries exclude deleted_at IS NOT NULL by default).` | `Includes soft delete support (queries exclude eliminado_en IS NOT NULL by default).` |
| 27 | `Supports soft delete (deleted_at field).` | `Supports soft delete (eliminado_en field).` |
| 40 | `self._has_deleted_at = hasattr(model, "deleted_at")` | `self._has_eliminado_en = hasattr(model, "eliminado_en")` |
| 49 | `if self._has_deleted_at:` | `if self._has_eliminado_en:` |
| 50 | `query = query.where(self.model.deleted_at.is_(None))` | `query = query.where(self.model.eliminado_en.is_(None))` |
| 109 | `Soft delete an entity (sets deleted_at timestamp).` | `Soft delete an entity (sets eliminado_en timestamp).` |
| 121 | `if self._has_deleted_at:` | `if self._has_eliminado_en:` |
| 124 | `instance.deleted_at = datetime.now(timezone.utc)` | `instance.eliminado_en = datetime.now(timezone.utc)` |
| 182 | `if self._has_deleted_at:` | `if self._has_eliminado_en:` |
| 183 | `query = query.where(self.model.deleted_at.is_(None))` | `query = query.where(self.model.eliminado_en.is_(None))` |

Adicional fuera del archivo: 5 ocurrencias en `backend/README.md` (líneas 70, 77, 107, 227, 242) renombradas para mantener docs alineados.

## Estrategia de tests (6 tests, archivo nuevo `backend/tests/integration/test_base_repository.py`)

Todos los tests usan `test_db_session` (SQLite in-memory de `conftest.py`) e instancian directamente `BaseRepository(session, Usuario)` para aislar el comportamiento del repo de cualquier service layer.

| Test | Propósito | Fixture |
|------|-----------|---------|
| `test_delete_sets_eliminado_en_on_basemodel_instance` | `delete(id)` setea `eliminado_en` y NO borra físicamente. Query directa con `select(Usuario)` (sin filtro) confirma que el row sigue presente con `eliminado_en` no nulo. | `sample_user` |
| `test_read_returns_none_for_soft_deleted_record` | Tras `delete(id)`, `repo.read(id)` retorna `None` (filtrado por `_get_base_query`). | `sample_user` |
| `test_list_excludes_soft_deleted_records` | Crear 3 usuarios, soft-delete uno, `repo.list()` retorna 2. | `test_db_session` (creación inline) |
| `test_count_excludes_soft_deleted_records` | Crear 3 usuarios, soft-delete uno, `repo.count()` retorna 2. | `test_db_session` |
| `test_delete_falls_back_to_hard_delete_when_model_lacks_eliminado_en` | `BaseRepository(session, Rol).delete(id)` ejecuta hard delete (no setea timestamp porque `Rol` no tiene la columna) y el row desaparece de la DB. | `sample_roles` |
| `test_hard_delete_always_removes_record_physically` | `repo.hard_delete(id)` borra físicamente aunque el modelo tenga `eliminado_en`. Query directa confirma ausencia. | `sample_user` |

**Confirmación de regresión**: cada test debe FALLAR antes del fix (con AssertionError) y PASAR después. La task list incluye una verificación explícita pre-fix.

**Comando de ejecución local** (no buildear, regla del proyecto):
```
pytest backend/tests/integration/test_base_repository.py -v
```

## Risks / Trade-offs

- **Riesgo**: tests sobre SQLite in-memory pueden no detectar diferencias sutiles con PostgreSQL (ej. timezone handling). → **Mitigación**: el comportamiento bajo prueba es a nivel ORM (filtro WHERE, asignación de campo Python), no del dialecto SQL. SQLite alcanza para validar el path. Un test contra Postgres real puede correrse en el sprint de hardening.
- **Riesgo**: alguien copy-pastea el bug del docstring del módulo en otro lado del proyecto. → **Mitigación**: docstrings actualizados (decisión 3) + Requirement explícito en spec (decisión 4) + tests que fallan si vuelve a romperse.
- **Riesgo**: el archivo `backend/README.md` queda desactualizado en docs si no se actualiza junto. → **Mitigación**: incluido explícitamente en tasks (item 1.4).
- **Trade-off**: `_has_eliminado_en` mezcla snake_case con un nombre español embebido en código inglés. Es intencional — el nombre de columna ES español por la spec del proyecto, y el atributo refleja el nombre de columna detectado.

## Migration Plan

No aplica migración de schema ni datos. El cambio es interno al repositorio Python y no toca DB ni API HTTP.

**Rollback**: `git revert` del commit. Cero efectos persistentes.

**Despliegue**: el fix entra junto con cualquier deploy regular del backend; no requiere ventana ni coordinación.

## Open Questions

Ninguna abierta. La cobertura de tests, el alcance del rename y la actualización del spec están completamente especificados arriba.
