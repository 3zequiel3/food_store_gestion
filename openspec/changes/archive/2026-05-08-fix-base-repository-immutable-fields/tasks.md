## 1. Verificación previa (regression contract)

- [x] 1.1 Confirmar que `backend/tests/integration/test_base_repository.py` existe (creado por `fix-base-repository-soft-delete`). Si no existe, bloquear el change.
- [x] 1.2 Confirmar que `backend/shared/repository.py` línea 100 sigue diciendo `key not in ("id", "created_at")`. Si ya fue modificado, bloquear el change.

## 2. Tests de regresión (agregar al archivo existente)

- [x] 2.1 Editar `backend/tests/integration/test_base_repository.py` y agregar el test `test_update_does_not_overwrite_creado_en` al final del archivo. El test:
  - Usa fixture `sample_user`.
  - Captura `creado_en_original = sample_user.creado_en`.
  - Llama `repo.update(sample_user.id, creado_en=datetime.now(timezone.utc) + timedelta(days=999))` donde `repo = BaseRepository(test_db_session, Usuario)`.
  - Re-lee el row con `select(Usuario).where(Usuario.id == sample_user.id)` (sin filtro) y verifica que `row.creado_en == creado_en_original`.
- [x] 2.2 Agregar también `test_update_does_not_overwrite_id`:
  - Usa fixture `sample_user`.
  - Captura `id_original = sample_user.id`.
  - Llama `repo.update(sample_user.id, id=999999)`.
  - Re-lee con `repo.read(id_original)` y verifica que `row.id == id_original`.
  - (Adicionalmente verifica que NO existe ningún row con `id=999999`.)
- [x] 2.3 Imports nuevos requeridos en el archivo: `from datetime import datetime, timezone, timedelta`. (Los demás imports ya están: `select`, `BaseRepository`, `Usuario`.)
- [x] 2.4 ANTES del fix: correr `pytest backend/tests/integration/test_base_repository.py::test_update_does_not_overwrite_creado_en -v`. CONFIRMADO: FAILED con `AssertionError: creado_en was mutated by update(): expected 2026-05-08 ..., got 2029-01-31 ...`. Regression contract validado.
- [x] 2.5 ANTES del fix: correr `pytest backend/tests/integration/test_base_repository.py::test_update_does_not_overwrite_id -v`. CONFIRMADO: PASSED (la firma posicional de `update()` protege `id` por colisión de argumentos — descubrimiento documentado en design decisión 6).

## 3. Code change en `backend/shared/repository.py`

- [x] 3.1 Editar línea 100: `if hasattr(instance, key) and key not in ("id", "created_at"):` → `if hasattr(instance, key) and key not in ("id", "creado_en"):`.
- [x] 3.2 Verificar que no quedan referencias residuales a `"created_at"` en el archivo: `rg "created_at" backend/shared/repository.py` retornó 0 matches.

## 4. Verificación post-fix

- [x] 4.1 Correr `pytest backend/tests/integration/test_base_repository.py -v` — RESULTADO: **8/8 PASSED** (6 tests heredados de `fix-base-repository-soft-delete` + 2 tests nuevos del actual change).
- [x] 4.2 Correr `pytest backend/tests/` para asegurar que ningún test heredado se rompió. RESULTADO: 26 passed, 26 errors. Los 26 errores son **preexistentes**, no causados por este change: provienen de tests (`test_main.py`, `test_error_handling.py`, `test_auth.py`) que requieren PostgreSQL real corriendo en localhost:5432 (`psycopg2.OperationalError: connection to server at "localhost" (127.0.0.1), port 5432 failed`). En este entorno no hay Postgres levantado. Todos los tests que usan la infra in-memory (incluidos los 8 nuestros) pasan. CONFIRMADO: el fix no rompió nada.

## 5. Spec sync

- [x] 5.1 Verificar que `openspec/changes/fix-base-repository-immutable-fields/specs/base-entities/spec.md` declara el Requirement "BaseRepository protects immutable audit fields" bajo `## ADDED Requirements` con 2 scenarios (creado_en + id).
- [x] 5.2 Correr `openspec validate fix-base-repository-immutable-fields` — RESULTADO: "Change is valid". `openspec status --json` reporta `isComplete: true` con los 4 artifacts en `done`.
