## 1. Pre-fix verification

- [x] 1.1 Verificar que `backend/tests/conftest.py` NO tiene ya un override de `get_uow` (regression check). Si lo tiene, parar y reportar — la situación es distinta a la analizada.
- [x] 1.2 Crear `backend/tests/integration/test_conftest_overrides.py` con `test_get_uow_uses_test_db_session_not_real_postgres` (ver design.md, Decisión 4 para el cuerpo del test).
- [x] 1.3 Correr `pytest backend/tests/integration/test_conftest_overrides.py -v` ANTES del fix y confirmar que falla con connection refused o status 500. Esto valida que el test de regresión efectivamente captura el bug.

## 2. Apply fix

- [x] 2.1 Agregar import en `backend/tests/conftest.py`: `from backend.dependencies import get_uow`.
- [x] 2.2 Dentro del fixture `client`, definir la función `override_get_uow` que construye `UnitOfWork(test_db_session)` y la yieldea (con rollback en `except` y SIN `uow.close()` — ver design.md, Decisión 2).
- [x] 2.3 Registrar el override: `app.dependency_overrides[get_uow] = override_get_uow`. Debe ir junto al `app.dependency_overrides[get_db] = override_get_db` existente, antes del `with TestClient(app) as test_client`.
- [x] 2.4 Verificar que `app.dependency_overrides.clear()` al final del fixture sigue limpiando ambos overrides (es el comportamiento default — `clear()` borra todos).

## 3. Post-fix validation

- [x] 3.1 Correr `pytest backend/tests/integration/test_conftest_overrides.py -v` y confirmar que pasa. Si falla con error de transacción/sessión, aplicar el fallback `join_transaction_mode="create_savepoint"` (ver design.md, Decisión 3).
- [x] 3.2 Correr `pytest backend/tests/integration/test_auth.py -v` y confirmar que sigue pasando (no debe haber regresión — el suite de auth ya pasaba con el override de `get_db`).
- [x] 3.3 **Validación de éxito secundaria:** correr `pytest backend/tests/integration/test_categories.py -v` y reportar el delta de tests pasados vs los 2 anteriores al fix:
  - Si pasan 31/31: perfecto, reportar al usuario para desbloquear el archive de `categories-backend`.
  - Si pasan menos de 31 con errores de connection/OperationalError: el fix está incompleto — diagnosticar.
  - Si pasan menos de 31 con OTROS errores (Assertion, 4xx, IntegrityError sin connection): bugs residuales en el código de categories. Listarlos en el summary del apply para que el orquestador decida si abrir un change separado. NO se arreglan en este change.
- [x] 3.4 Validar el change con `openspec validate fix-test-setup-uow-override`.

## 4. Cierre

- [x] 4.1 Reportar resultado al usuario con: lista de tests del nuevo archivo, resultado del suite de auth, resultado del suite de categories (X/31), bugs residuales detectados (si los hay). Esperar OK antes de archivar.
