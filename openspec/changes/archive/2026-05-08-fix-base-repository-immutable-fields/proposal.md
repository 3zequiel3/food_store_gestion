## Why

Mientras se aplicaba `fix-base-repository-soft-delete` se descubrió un segundo bug del MISMO patrón en `backend/shared/repository.py`. El método `update()` (línea 100) intenta proteger campos de auditoría inmutables con un guard:

```python
if hasattr(instance, key) and key not in ("id", "created_at"):
    setattr(instance, key, value)
```

El set `("id", "created_at")` está mal: el proyecto nombra el campo en español como **`creado_en`** (ver `backend/shared/models.py:42` en `BaseModel` y `backend/shared/models.py:121` en `AppendOnlyBaseModel`, alineado con `docs/Integrador.txt §3` y RN-CA09). El string literal `"created_at"` no existe en ningún modelo del proyecto.

**Consecuencia**: `repo.update(id, creado_en=<lo-que-sea>)` queda autorizado y **sobreescribe el timestamp original de creación**, rompiendo la inmutabilidad del audit trail. Cualquier flow que reciba kwargs externos (form parsing, deserialización de JSON, mass-assignment) puede inadvertidamente mutar `creado_en`.

**Por qué pasó silencioso**: ningún módulo aplicado expuso `update()` con kwargs de campos de auditoría todavía. No hay tests que prueben la inmutabilidad del campo. Es exactamente el mismo modo de falla que el bug fixeado en `fix-base-repository-soft-delete` — código que referencia campos en inglés (`deleted_at`, `created_at`) cuando el proyecto los nombra en español (`eliminado_en`, `creado_en`).

**Por qué fixear ahora**: el fix es de 1 línea de código. Si lo dejamos pasar, el primer módulo que use `update()` con kwargs de auditoría lo va a romper en producción y va a ser difícil de detectar (no tira excepción, solo mutila el audit trail). Mejor cerrarlo junto al hermano `soft-delete`.

## What Changes

- **Una línea** en `backend/shared/repository.py`, línea 100:
  - **Antes**: `if hasattr(instance, key) and key not in ("id", "created_at"):`
  - **Después**: `if hasattr(instance, key) and key not in ("id", "creado_en"):`
- **Dos tests de regresión** en `backend/tests/integration/test_base_repository.py` (archivo ya creado por el change anterior):
  - `test_update_does_not_overwrite_creado_en` — DEBE fallar antes del fix, pasar después.
  - `test_update_does_not_overwrite_id` — regression test del comportamiento existente que ya funciona; lo blindamos para que no se rompa en futuros cambios.
- **Spec delta**: agregar al capability `base-entities` un nuevo Requirement adyacente al de soft-delete: "BaseRepository protects immutable audit fields".

No se tocan otros archivos. No hay cambios de API pública, schema de DB ni migraciones.

## Capabilities

### New Capabilities
- (none)

### Modified Capabilities
- `base-entities`: agrega un Requirement explícito sobre la inmutabilidad de los campos de auditoría (`id` y `creado_en`) en el método `update()` del `BaseRepository`. El Requirement existente de `BaseModel` define que `creado_en` se setea por `server_default=func.now()` al INSERT, pero NO declara que sea inmutable después de eso. Este delta lo materializa como contrato testeable a nivel del repositorio.

## Impact

**Código afectado:**
- `backend/shared/repository.py` — 1 línea (línea 100).
- `backend/tests/integration/test_base_repository.py` — agrega 2 tests al archivo existente. NO se tocan los 6 tests existentes.

**Código NO afectado** (verificado por inspección):
- `backend/features/*` — ningún módulo invoca `repo.update()` con kwargs de auditoría todavía.
- Otros campos teóricamente inmutables (`actualizado_en`, `eliminado_en`) quedan **fuera de alcance** intencionalmente:
  - `actualizado_en` debería refrescarse por SQLAlchemy `onupdate=func.now()` automáticamente; si se pasa por kwargs, el `onupdate` lo va a pisar igual al flush.
  - `eliminado_en` se maneja por `delete()` y `hard_delete()`. No es estrictamente inmutable (un futuro "restore" podría hacer `eliminado_en=None`).
- `AppendOnlyBaseModel` (sin `actualizado_en` ni `eliminado_en`): si se llama `update()` sobre una instancia, ahora queda protegido `creado_en` (correcto — append-only debería rechazar TODO update, pero eso es trabajo separado).

**Consumidores aguas abajo:**
- `categories-backend` (en propose, no aplicado), `products-backend`, `ingredients-backend`, `addresses-backend`, `orders-backend` — todos heredan el comportamiento corregido sin código defensivo.

**Estimación**: 30 min (1 línea de código + 2 tests).

**Dependencias**: el archivo `backend/tests/integration/test_base_repository.py` debe existir (lo crea `fix-base-repository-soft-delete`, ya aplicado). No bloquea ni requiere otros changes en flight.
