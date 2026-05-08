## Context

`BaseRepository.update()` (`backend/shared/repository.py:84-105`) recibe kwargs y los aplica al instance vía `setattr`. Para evitar que un caller corrompa los identificadores y los timestamps de auditoría, hay un guard:

```python
for key, value in kwargs.items():
    if hasattr(instance, key) and key not in ("id", "created_at"):
        setattr(instance, key, value)
```

El problema: `"created_at"` no es el nombre del campo en este proyecto. El campo se llama `creado_en` (ver `backend/shared/models.py:42` y `:121`, alineado con la spec canónica `docs/Integrador.txt §3` y RN-CA09). Resultado: el guard protege un nombre fantasma. `creado_en` queda libremente mutable vía kwargs.

**Mismo modo de falla** que `fix-base-repository-soft-delete` (también recién aplicado): cadena en inglés que no matchea con el nombre real del campo en español.

**Por qué pasó silencioso**: ningún caller activo del proyecto invoca `update()` con kwargs de auditoría todavía. La superficie de ataque potencial son flows que pasan kwargs derivados de input externo (deserialización de Pydantic con `model_dump()`, body de PATCH/PUT, etc.). Sin tests específicos, el bug es invisible.

## Goals / Non-Goals

**Goals:**
- Hacer que `update()` proteja efectivamente `creado_en` (y mantenga la protección existente de `id`).
- Documentar la inmutabilidad como Requirement OpenSpec con scenarios atómicos.
- Capturar el contrato con dos tests de regresión que se ejecuten en CI.

**Non-Goals:**
- NO expandir la lista de campos protegidos a `actualizado_en` (lo cubre `onupdate=func.now()` del ORM — ver "Decisiones" #2).
- NO incluir `eliminado_en` en el set de inmutables (no es estrictamente inmutable; un futuro restore podría hacer `eliminado_en=None` — ver "Decisiones" #3).
- NO refactorizar la API pública del repositorio.
- NO crear nuevas fixtures: reutilizamos `test_db_session` y `sample_user` del `conftest.py`.
- NO bloquear updates de TODOS los campos de un `AppendOnlyBaseModel`. Acá solo se cierra `creado_en`. La política completa de "append-only no admite update" es trabajo separado si surge la necesidad.

## Decisions

### Decisión 1: Solo cambiar `"created_at"` → `"creado_en"`, no expandir el set
**Elegido**: tocar solo la cadena equivocada. El set queda `("id", "creado_en")`.
**Alternativa descartada**: pasar el set a `("id", "creado_en", "actualizado_en", "eliminado_en")`.
**Razón**: el reporte del bug es nominal — el guard ya estaba pensado para proteger `id` y el timestamp de creación. La cadena estaba mal escrita, no había una decisión de "y qué otros campos meto". Expandir el alcance sería un cambio de contrato distinto que merece su propio análisis.

### Decisión 2: Dejar `actualizado_en` fuera del set protegido
**Elegido**: NO incluir en el guard.
**Razón**: `BaseModel.actualizado_en` (línea 47 de `models.py`) usa `onupdate=func.now()`. Cualquier `setattr(instance, "actualizado_en", X)` queda pisado por SQLAlchemy en el siguiente flush. Si el cableado ORM rompiera, ESE es el bug, no el guard del repo. Mantener el set "limpio" evita ofuscar dónde vive realmente la garantía.

### Decisión 3: Dejar `eliminado_en` fuera del set protegido
**Elegido**: NO incluir en el guard.
**Razón**: `eliminado_en` se manipula intencionalmente (en `delete()` para soft delete; eventualmente en una operación de restore que ponga `eliminado_en = None`). Bloquearlo en `update()` rompería esos flujos legítimos. El control de mutación de `eliminado_en` debe vivir en operaciones específicas (`delete()`, `hard_delete()`, futuro `restore()`), no en el guard genérico de `update()`.

### Decisión 4: Tests sobre `Usuario` con fixture existente
**Elegido**: usar `Usuario` y la fixture `sample_user` ya definidas en `conftest.py`.
**Razón**: `Usuario` hereda de `BaseModel`, así que tiene `id` y `creado_en`. Reutilizamos infra del change anterior sin agregar fixtures.

### Decisión 5: Spec delta — Requirement separado del de soft-delete
**Elegido**: agregar un nuevo Requirement bajo `## ADDED Requirements` adyacente al existente "BaseRepository enforces soft-delete semantics via `eliminado_en`".
**Alternativa descartada**: reescribir el Requirement existente para incluir un scenario de inmutabilidad.
**Razón**: dos invariantes ortogonales (filtrado por soft delete vs inmutabilidad de auditoría). Mantenerlos separados hace que cada uno sea testeable de forma atómica y que la auditoría futura distinga claramente cuál se rompió si hay regresión.

### Decisión 6: Test 2 (`test_update_does_not_overwrite_id`) — descubrimiento durante el apply
**Elegido**: incluir el test de `id`, ajustado tras un descubrimiento durante la implementación.
**Descubrimiento**: la firma de `update()` es `def update(self, id, **kwargs)`. El parámetro `id` es posicional, así que cualquier caller que intente `repo.update(target_id, id=forged)` (o un `repo.update(target_id, **payload)` donde `payload` contiene `"id"`) dispara un `TypeError "got multiple values for argument 'id'"` ANTES de que el flujo llegue al guard del set. **El "id" dentro del set protegido en `repository.py:100` es inalcanzable por la API pública actual — la firma del método es la defensa real.**
**Implicancia para el test 2**: el test verifica el path realista (un payload spread con `"id"`) y assertea el `TypeError`. La protección es correcta y robusta, solo que vive en la firma, no en el set. Si alguien en el futuro refactoriza a `update(self, **kwargs)` (sin `id` posicional), el guard del set pasaría a ser la única defensa, y el test seguiría siendo válido (después del refactor revisaría que `repo.update(id=target_id, id=forged)` no mute la row — aunque la sintaxis colisionaría también). Por ahora, el assert principal es el `pytest.raises(TypeError)` con verificaciones secundarias del estado.
**Razón para mantener el test**: documenta el invariante completo ("el id no se puede mutar vía update bajo ninguna ruta razonable") y captura el descubrimiento para futuros mantenedores.

## Diff exacto del fix

| Archivo | Línea | Antes | Después |
|---------|-------|-------|---------|
| `backend/shared/repository.py` | 100 | `if hasattr(instance, key) and key not in ("id", "created_at"):` | `if hasattr(instance, key) and key not in ("id", "creado_en"):` |

## Estrategia de tests (2 tests nuevos en archivo existente)

Archivo: `backend/tests/integration/test_base_repository.py` (creado por `fix-base-repository-soft-delete`).

| Test | Propósito | Fixture | Comportamiento esperado |
|------|-----------|---------|-------------------------|
| `test_update_does_not_overwrite_creado_en` | Confirmar que `repo.update(id, creado_en=otro_ts)` NO muta `creado_en`. | `sample_user` | Capturar `creado_en` antes, llamar `update()` con un `creado_en` muy distinto, releer del DB, assert que no cambió. |
| `test_update_does_not_overwrite_id` | Regression test del comportamiento existente: `repo.update(id, id=999)` no muta `id`. | `sample_user` | Capturar `id` antes, llamar `update()` con `id=999999`, assert que el `id` original sigue intacto. |

**Contrato de regresión:**
- Test 1 (`test_update_does_not_overwrite_creado_en`): DEBE fallar antes del fix (porque `"creado_en"` no estaba en el set protegido) y pasar después.
- Test 2 (`test_update_does_not_overwrite_id`): pasa antes y después del fix (el guard ya protege `id`). Sirve como blindaje futuro.

**Verificación previa al fix**: el agente DEBE correr el test 1 ANTES de aplicar el fix y mostrar que falla. Luego aplica el fix y muestra que pasa. Esto valida que el contrato detecta el bug.

**Comando de ejecución local** (no buildear, regla del proyecto):
```
pytest backend/tests/integration/test_base_repository.py -v
```

## Risks / Trade-offs

- **Riesgo**: alguien en el futuro agrega `actualizado_en` al guard pensando que "completa" la protección, pero el `onupdate` del ORM ya lo cubre y mete inconsistencia. → **Mitigación**: la decisión 2 está documentada acá; el code review futuro debería bloquearlo o referenciar este design.
- **Riesgo**: el test de `creado_en` depende de que `creado_en` ya tenga un valor cuando se ejecuta el test. SQLite con `server_default=func.now()` debería resolverlo, pero si la fixture no flushea, podría ser `None`. → **Mitigación**: la fixture `sample_user` hace `test_db_session.flush()` y `refresh()` (ver `conftest.py:135,141`), así que `creado_en` queda cargado antes del test.
- **Trade-off**: el test 2 (`id`) puede parecer redundante. Trade-off aceptado por la red de seguridad permanente (decisión 6).

## Migration Plan

No aplica migración de schema ni datos. Cambio interno al repositorio Python.

**Rollback**: `git revert` del commit. Cero efectos persistentes.

**Despliegue**: el fix entra junto con cualquier deploy regular del backend; no requiere ventana ni coordinación.

## Open Questions

Ninguna abierta. Alcance, set de campos protegidos, tests y spec delta están totalmente especificados arriba.
