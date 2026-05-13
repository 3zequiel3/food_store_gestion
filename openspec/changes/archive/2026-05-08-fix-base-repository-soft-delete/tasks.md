## 1. Code change en `backend/shared/repository.py`

- [x] 1.1 Renombrar atributo: línea 40 `self._has_deleted_at = hasattr(model, "deleted_at")` → `self._has_eliminado_en = hasattr(model, "eliminado_en")`
- [x] 1.2 Renombrar uso del atributo en `_get_base_query` (línea 49) y query (línea 50): `_has_deleted_at` → `_has_eliminado_en`, `self.model.deleted_at` → `self.model.eliminado_en`
- [x] 1.3 Renombrar uso del atributo en `delete()` (línea 121) y asignación de campo (línea 124): `_has_deleted_at` → `_has_eliminado_en`, `instance.deleted_at` → `instance.eliminado_en`
- [x] 1.4 Renombrar uso del atributo en `count()` (línea 182) y query (línea 183): `_has_deleted_at` → `_has_eliminado_en`, `self.model.deleted_at` → `self.model.eliminado_en`
- [x] 1.5 Actualizar docstrings: módulo (línea 5 menciona `deleted_at`), clase `BaseRepository` (línea 27), método `delete` (línea 109) — todos a `eliminado_en`
- [x] 1.6 Verificar que no quedan referencias residuales: `rg "deleted_at" backend/shared/repository.py` debe retornar 0 matches

## 2. Sincronizar docs

- [x] 2.1 Actualizar `backend/README.md` línea 70 (`deleted_at (DateTime, nullable, for soft delete)` → `eliminado_en (DateTime, nullable, for soft delete)`)
- [x] 2.2 Actualizar `backend/README.md` línea 77 (`Soft delete (sets deleted_at)` → `Soft delete (sets eliminado_en)`)
- [x] 2.3 Actualizar `backend/README.md` línea 107 (`Models with deleted_at field use soft delete` → `Models with eliminado_en field use soft delete`)
- [x] 2.4 Actualizar `backend/README.md` líneas 227 y 242 (ejemplos de modelo: `deleted_at: Optional[DateTime]` → `eliminado_en: Optional[datetime]`)
- [x] 2.5 Verificar: `rg "deleted_at" backend/README.md` debe retornar 0 matches

## 3. Tests de regresión (archivo nuevo)

- [x] 3.1 Crear `backend/tests/integration/test_base_repository.py` con header de docstring del archivo y los imports (`pytest`, `BaseRepository`, modelos `Usuario` y `Rol`, `select` de SQLAlchemy)
- [x] 3.2 ANTES del fix: correr `pytest backend/tests/integration/test_base_repository.py -v` y CONFIRMAR que los 6 tests del path soft-delete fallan (test 5 puede pasar trivialmente). Documentar la salida en el commit message del code change.
- [x] 3.3 Test 1 — `test_delete_sets_eliminado_en_on_basemodel_instance`: instanciar `BaseRepository(session, Usuario)`, `repo.delete(sample_user.id)` retorna True, `eliminado_en` del row queda no-nulo (consultar con `select(Usuario)` directo, sin filtro), el row sigue presente físicamente
- [x] 3.4 Test 2 — `test_read_returns_none_for_soft_deleted_record`: tras `repo.delete(id)`, `repo.read(id)` retorna `None`
- [x] 3.5 Test 3 — `test_list_excludes_soft_deleted_records`: crear 3 usuarios distintos, soft-delete del primero, `repo.list()` retorna 2 elementos sin el borrado
- [x] 3.6 Test 4 — `test_count_excludes_soft_deleted_records`: 3 usuarios, soft-delete uno, `repo.count()` retorna 2
- [x] 3.7 Test 5 — `test_delete_falls_back_to_hard_delete_when_model_lacks_eliminado_en`: instanciar `BaseRepository(session, Rol)`, `repo.delete(role.id)` retorna True, query directa confirma que el row YA NO existe (hard delete físico)
- [x] 3.8 Test 6 — `test_hard_delete_always_removes_record_physically`: `BaseRepository(session, Usuario).hard_delete(sample_user.id)` retorna True, query directa con `select(Usuario)` confirma ausencia (regression test del path existente)
- [x] 3.9 DESPUÉS del fix: correr `pytest backend/tests/integration/test_base_repository.py -v` — los 6 tests deben pasar
- [x] 3.10 Correr suite de tests completa relacionada para asegurar que no se rompió nada heredado: `pytest backend/tests/ -v` (no buildear, solo pytest)

## 4. Spec sync

- [x] 4.1 Verificar que `openspec/changes/fix-base-repository-soft-delete/specs/base-entities/spec.md` existe y declara el Requirement nuevo bajo `## ADDED Requirements` con sus 4 scenarios
- [x] 4.2 Correr `openspec validate fix-base-repository-soft-delete` y resolver cualquier warning antes de pedir review humana
