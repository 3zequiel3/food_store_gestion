## Why

Durante el propose de `categories-backend` se descubrió que `backend/shared/repository.py` chequea `hasattr(model, "deleted_at")` (línea 40) pero los modelos heredan de `BaseModel` (`backend/shared/models.py`), que define el campo como **`eliminado_en`**. La spec canónica del proyecto (`docs/Integrador.txt` §3, `docs/Descripcion.txt`, RN-CA09) y el spec OpenSpec ya aprobado de `base-entities` establecen explícitamente que el campo se llama `eliminado_en`.

**Consecuencia**: `_has_deleted_at` siempre evalúa `False`, y toda la lógica de soft delete del `BaseRepository` es código muerto:

- `_get_base_query` no filtra registros eliminados — `read`, `list` y `count` los exponen.
- `delete()` cae al branch de hard delete (línea 128-130) en vez del soft delete (línea 121-126).
- `count()` cuenta también los eliminados.

El bug pasó silencioso porque los repos heredados (auth) no expusieron `delete()` todavía y no hay tests que ejerciten el soft delete. **Si lo arreglamos ahora**, todos los módulos siguientes (`categories-backend`, `products-backend`, `ingredients-backend`, `addresses-backend`, `orders-backend`) heredan el comportamiento correcto sin mitigaciones locales.

## What Changes

- **Renombrar** las 8 referencias internas a `deleted_at` por `eliminado_en` en `backend/shared/repository.py` (string literal del `hasattr`, accesos a columna en `_get_base_query`/`delete`/`count`, y docstrings de módulo, clase y método `delete`).
- **Renombrar** el atributo privado `_has_deleted_at` → `_has_eliminado_en` (privado por convención `_`, no afecta API pública del repo).
- **Actualizar** las 5 referencias a `deleted_at` en `backend/README.md` para reflejar el nombre real del campo.
- **Agregar** 6 tests de integración en `backend/tests/integration/` que ejercitan los caminos de soft delete y hard delete (regression tests). DEBEN fallar antes del fix y pasar después.
- **Spec delta**: agregar al capability `base-entities` un Requirement explícito sobre el comportamiento del `BaseRepository` (filtrado por `eliminado_en IS NULL`, soft delete vía `eliminado_en = NOW()`, fallback a hard delete si el modelo carece del campo).

No hay cambios de API pública, schema de DB, ni migraciones. No rompe consumidores existentes.

## Capabilities

### New Capabilities
- (none)

### Modified Capabilities
- `base-entities`: agrega un Requirement explícito sobre el comportamiento del `BaseRepository` respecto al soft delete (filtrado, semántica de `delete()`, fallback de hard delete). El Requirement existente de `BaseModel.eliminado_en` ya menciona "is included in default repository filters" pero no estaba siendo cumplido por el código — el delta lo materializa como Requirement separado y testeable.

## Impact

**Código afectado:**
- `backend/shared/repository.py` — único archivo con código vivo a modificar (10 ediciones puntuales).
- `backend/README.md` — 5 referencias a `deleted_at` a corregir en docs.
- `backend/tests/integration/test_base_repository.py` — archivo nuevo con 6 tests.

**Código NO afectado** (verificado con `rg "deleted_at" backend/`):
- Ningún módulo en `backend/features/*` referencia `deleted_at` directamente.
- `backend/shared/unit_of_work.py`, `service.py`, modelos de dominio: sin referencias.

**Consumidores aguas abajo:**
- `categories-backend` (en propose, no aplicado): puede eliminar la mitigación local que planteaba (sobreescribir `_get_base_query` y `delete` en `CategoryRepository`). No bloqueante para apply de este fix.
- Modules futuros (`products-backend`, `ingredients-backend`, `addresses-backend`, `orders-backend`): heredan el comportamiento corregido.

**Estimación**: 2 horas (15 min code change + 1.5 h tests).

**Dependencias**: ninguna. No bloquea ni requiere otros changes en flight.
