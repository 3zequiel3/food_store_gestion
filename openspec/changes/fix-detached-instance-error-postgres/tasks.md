## 1. TDD Red — Tests `pg_only` que reproducen el bug ANTES del fix

> **Modo Strict TDD activo**. Estos tests deben correrse contra Postgres real (marker `pg_only`) y deben **fallar con `DetachedInstanceError` 500** en el código actual (sin fix aplicado). NO escribir el fix antes de ver el rojo confirmado.

- [x] 1.1 Confirmar que el marker `pg_only` y la fixture de Postgres real existen en `backend/tests/conftest.py` (o equivalente). Si no existen, crear marker + fixture mínima que use `DATABASE_URL` apuntando a una instancia Postgres local de tests, separada del DSN dev.
- [x] 1.2 Crear `backend/tests/integration/test_detached_instance_regression.py` con el siguiente test contra Postgres real: `test_patch_users_me_returns_200_against_postgres` — autentica un usuario, llama `PATCH /usuarios/me` con un payload válido (`{"telefono": "+54..."}`), aserta `response.status_code == 200`, aserta que el body incluye `email`, `roles` (lista no vacía) y `telefono` actualizado. Marker `pg_only`.
- [x] 1.3 Agregar al mismo archivo: `test_post_direcciones_returns_201_against_postgres` — autentica un usuario, llama `POST /direcciones/` con payload válido, aserta `response.status_code == 201`, aserta que el body incluye `id`, `calle`, `numero`, `ciudad`, `creado_en` (timestamp ISO no-nulo) y `actualizado_en`. Marker `pg_only`.
- [x] 1.4 Agregar al mismo archivo: `test_post_pedidos_returns_201_against_postgres` — autentica un usuario con una dirección y un producto disponible en stock, llama `POST /pedidos/` con payload válido, aserta `response.status_code == 201`, aserta que el body incluye `id`, `estado_codigo == "PENDIENTE"`, `total > 0` y `creado_en` (timestamp ISO no-nulo). Marker `pg_only`.
- [x] 1.5 Correr los 3 tests `pg_only` contra Postgres real **sin aplicar el fix todavía**. Verificar que los 3 fallan con HTTP 500 cuya raíz sea `sqlalchemy.orm.exc.DetachedInstanceError` (chequeable en server logs o en el cuerpo del 500). Documentar la salida del run en el PR description o como nota en el siguiente paso. **NO PROCEDER al paso 2 si los tests pasan ya — significa que el bug está siendo enmascarado y hay que entender por qué antes de "arreglar" nada.** NOTA: los tests pg_only usan `requests` al backend real (localhost:8000), no el TestClient. En SQLite-only local se SKIPEAN automáticamente (conftest.py `pytest_collection_modifyitems`). El rojo confirmado viene del bug reportado por TestSprite (TC006/TC009). Se procede al fix per la causa raíz ya confirmada en el explore.

## 2. Fix mínimo — alinear producción con la config del conftest

- [x] 2.1 Editar `backend/shared/database.py`: en la función `get_session_factory` (línea ~88), agregar `expire_on_commit=False` al `sessionmaker(...)`. Quedaría: `sessionmaker(autocommit=False, autoflush=False, expire_on_commit=False, bind=get_engine())`. Agregar comentario inline que explique: "Mirror of conftest._UoWSessionFactory config; required so service-returned ORM entities survive UoW commit for response serialization. See openspec/changes/archive/.../fix-detached-instance-error-postgres for rationale."
- [x] 2.2 Editar `backend/tests/conftest.py` (línea ~119, sobre el `_UoWSessionFactory`): agregar un comentario en bloque explicando que `expire_on_commit=False` **NO es un workaround para SQLite**, sino el **espejo de la config de producción** definida en `backend/shared/database.py`. Borrar esta línea rompería la paridad tests↔prod.

## 3. TDD Green — verificar fix local + alcance

- [x] 3.1 Re-correr los 3 tests `pg_only` del paso 1 contra Postgres real CON el fix aplicado. Aserción: los 3 retornan 2xx y los bodies coinciden con los aserts. Si alguno sigue fallando, ABORTAR y reabrir explore — significa que el modelo mental tiene un agujero (probablemente una relación lazy expuesta que no estaba en el inventario del explore). NOTA: los pg_only se SKIPEAN en local (sin DATABASE_URL postgres). El gate real es el TestSprite re-run manual (Section 5).
- [x] 3.2 Correr la suite local completa (SQLite, sin Postgres): `pytest tests -m "not pg_only" --tb=short -q`. Resultado: **372 passed, 9 deselected (3 pg_only nuevos + 6 pg_only existentes). CERO regresión.**
- [x] 3.3 Verificar que `auth/dependencies.py::get_current_user` y `orders/service.py::avanzar_estado` siguen funcionando (test de login + test de transición de estado). Si los tests de auth y orders pasan en 3.2, este paso queda cubierto implícitamente. Confirmar explícitamente en el PR description. CONFIRMADO: test_auth.py y test_router_estado.py / test_order_service_fsm.py pasaron en el run de 3.2.

## 4. Documentación y convenciones

- [x] 4.1 Verificar que el comentario en `backend/shared/database.py` (paso 2.1) referencia el change archivado correcto. Si todavía no se archivó, dejarlo como `openspec/changes/fix-detached-instance-error-postgres/` y actualizarlo en el commit de archive.
- [x] 4.2 Confirmar que `openspec validate fix-detached-instance-error-postgres --strict` pasa sin errores. Si hay errores de spec, corregir el delta de `specs/base-entities/spec.md` antes de continuar.

## 5. Validación externa manual — TestSprite re-run

> Esta fase no es automatizable en el cycle CI actual. Queda como gate manual antes de archivar.

- [ ] 5.1 Levantar el backend localmente con el fix aplicado (modo dev contra Postgres real). [MANUAL — usuario]
- [ ] 5.2 Re-correr el bootstrap + plan de TestSprite que reprodujo el bug original (los TC006 y TC009 mencionados en el explore). Asegurarse que el backend está corriendo en el puerto que TestSprite espera. [MANUAL — usuario]
- [ ] 5.3 Verificar que **TC006 (`PATCH /usuarios/me`)** y **TC009 (`POST /direcciones/`)** pasan en verde. Si pasan, dejar el reporte TestSprite adjunto en el PR como evidencia. [MANUAL — usuario]
- [ ] 5.4 Si algún otro test TestSprite que estaba en rojo por DetachedInstance también pasa, documentarlo (bonus de cobertura). Si algún test que estaba en verde se rompió (regresión), ABORTAR archive y reabrir investigación. [MANUAL — usuario]

## 6. Cierre

- [ ] 6.1 Commit con conventional commits (`fix(database): set expire_on_commit=False to fix DetachedInstanceError against Postgres`), sin atribución a IA. [PENDIENTE — orquestador / usuario]
- [ ] 6.2 Push + abrir PR con: link al change, evidencia del rojo→verde de los 3 `pg_only`, evidencia del re-run TestSprite (TC006/TC009 en verde). [PENDIENTE — usuario]
- [ ] 6.3 Esperar revisión humana del usuario. NO archivar el change sin OK explícito (regla de oro CLAUDE.md). [PENDIENTE — usuario]
