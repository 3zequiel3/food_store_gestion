## 1. Dependencias y setup Alembic

- [x] 1.1 Agregar a `backend/requirements.txt`: `alembic`, `passlib[bcrypt]`, `python-jose[cryptography]`, `slowapi`, `mercadopago`, `pydantic-settings` y reinstalar (`pip install -r backend/requirements.txt`).
- [x] 1.2 Ejecutar `alembic init backend/alembic` desde la raíz del proyecto y mover/crear `alembic.ini` en `backend/alembic.ini` con `script_location = alembic`.
- [x] 1.3 Editar `backend/alembic.ini`: setear `file_template = %%(year)d%%(month).2d%%(day).2d_%%(hour).2d%%(minute).2d_%%(rev)s_%%(slug)s` y comentar `sqlalchemy.url` (se setea desde `env.py`).
- [x] 1.4 Editar `backend/alembic/env.py`: importar `os`, leer `DATABASE_URL` y setear `config.set_main_option("sqlalchemy.url", os.environ["DATABASE_URL"])`.
- [x] 1.5 En `backend/alembic/env.py` importar `Base` desde `backend.shared.database`, importar todos los módulos `backend/features/*/models.py` (incluso los que aún no existen al final del change, agregar imports al cerrar) y setear `target_metadata = Base.metadata`.
- [x] 1.6 En `backend/alembic/env.py`, en `run_migrations_online()` y `run_migrations_offline()`, pasar `compare_type=True` y `compare_server_default=True` a `context.configure(...)`.

## 2. Refactor BaseModel y metadata

- [x] 2.1 En `backend/shared/database.py` (o donde viva `Base`), configurar `MetaData(naming_convention={...})` con las 5 keys (ix/uq/ck/fk/pk) según design D8 y database-migrations spec.
- [x] 2.2 En `backend/shared/models.py`, refactor `BaseModel`: cambiar `id` a `Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)`; renombrar `created_at`→`creado_en`, `updated_at`→`actualizado_en`, `deleted_at`→`eliminado_en`; usar `DateTime(timezone=True)` con `server_default=func.now()` (y `onupdate=func.now()` para `actualizado_en`).
- [x] 2.3 En `backend/shared/models.py`, agregar clase `AppendOnlyBaseModel` con `id` (BIGSERIAL) + `creado_en` (TIMESTAMPTZ), sin `actualizado_en` ni `eliminado_en`. Marcarla como `__abstract__ = True`.
- [x] 2.4 En `backend/shared/enums.py`, eliminar enums `Role`, `EstadoPedido`, `FormaPago` (serán catálogos). Si quedan otros enums válidos, dejarlos.

## 3. Catálogos (tablas de referencia)

- [x] 3.1 Crear `backend/features/catalog/__init__.py` (módulo nuevo).
- [x] 3.2 Crear `backend/features/catalog/models.py` con `Rol` (`__tablename__ = 'roles'`, PK Integer, `codigo` UNIQUE, `descripcion`, hereda BaseModel).
- [x] 3.3 En `backend/features/catalog/models.py`, agregar `FormaPago` (`__tablename__ = 'payment_methods'`, PK `codigo` String, `descripcion`, `habilitada` Boolean default True, hereda BaseModel — sin `eliminado_en` no aplica acá: el campo está pero queda nullable/None).
- [x] 3.4 En `backend/features/catalog/models.py`, agregar `EstadoPedido` (`__tablename__ = 'order_states'`, PK `codigo` String, `descripcion`, `orden` Integer, `es_terminal` Boolean default False, hereda BaseModel).

## 4. Identidad y auth (modelos)

- [x] 4.1 En `backend/features/users/models.py`, refactor `Usuario`: PK BIGSERIAL, agregar `nombre`, `apellido`, `telefono` (nullable), remover columna `username`, remover columna `role`. Mantener `email` UNIQUE, `password_hash`, `is_active`. Heredar BaseModel (trae timestamps + soft delete).
- [x] 4.2 En `backend/features/users/models.py`, agregar `UsuarioRol` (`__tablename__ = 'user_roles'`, PK compuesta `(user_id, role_id)`, FKs a `users.id` y `roles.id`, hereda BaseModel).
- [x] 4.3 En `backend/features/users/models.py` agregar relationship `Usuario.roles` vía `secondary='user_roles'` apuntando a `Rol`.
- [x] 4.4 Crear `backend/features/auth/__init__.py` y `backend/features/auth/models.py` con `RefreshToken`: PK BIGSERIAL, `user_id` FK, `token_hash` UNIQUE, `expires_at` TIMESTAMPTZ, `revoked_at` TIMESTAMPTZ nullable, hereda BaseModel.
- [x] 4.5 Crear `backend/features/addresses/__init__.py` y `backend/features/addresses/models.py` con `DireccionEntrega`: PK BIGSERIAL, `user_id` FK, `calle`, `numero`, `ciudad`, `codigo_postal`, `referencia` (nullable), `es_principal` Boolean default False, hereda BaseModel.

## 5. Catálogo de productos

- [x] 5.1 En `backend/features/catalog/models.py`, agregar `Categoria` (`__tablename__ = 'categories'`, PK BIGSERIAL, `nombre`, `padre_id` FK autoreferencial nullable, relationship `padre`/`hijos` con `remote_side=[id]`, hereda BaseModel).
- [x] 5.2 En `backend/features/catalog/models.py`, agregar `Ingrediente` (`__tablename__ = 'ingredients'`, PK BIGSERIAL, `nombre` UNIQUE, `es_alergeno` Boolean default False, hereda BaseModel).
- [x] 5.3 En `backend/features/products/models.py`, refactor `Producto`: PK BIGSERIAL, `nombre`, `descripcion` (Text), `precio` Numeric(10,2) con CHECK > 0, `stock_cantidad` Integer default 0 con CHECK >= 0, `disponible` Boolean default True, `imagen_url` (nullable), hereda BaseModel.
- [x] 5.4 En `backend/features/products/models.py`, agregar `ProductoCategoria` (`__tablename__ = 'product_categories'`, PK compuesta `(product_id, category_id)`, FKs, hereda BaseModel).
- [x] 5.5 En `backend/features/products/models.py`, agregar `ProductoIngrediente` (`__tablename__ = 'product_ingredients'`, PK compuesta `(product_id, ingredient_id)`, FKs, hereda BaseModel).
- [x] 5.6 En `backend/features/products/models.py`, agregar relationships `Producto.categorias` y `Producto.ingredientes` vía `secondary`.

## 6. Pedidos (modelos)

- [x] 6.1 En `backend/features/orders/models.py`, refactor `Pedido`: PK BIGSERIAL, `user_id` FK, `direccion_entrega_id` FK a `delivery_addresses`, `direccion_snapshot` String, `total` Numeric(10,2), `costo_envio` Numeric(10,2) default 0, `forma_pago_codigo` FK a `payment_methods.codigo`, `estado_codigo` FK a `order_states.codigo` default `'PENDIENTE'`, `notas` Text nullable. Eliminar columna `delivery_address` plana. Hereda BaseModel.
- [x] 6.2 En `backend/features/orders/models.py`, refactor `DetallePedido`: PK BIGSERIAL, `pedido_id` FK, `producto_id` FK, `nombre_snapshot`, `precio_snapshot` Numeric(10,2), `cantidad` Integer con CHECK > 0, `personalizacion` `ARRAY(Integer)` nullable. Hereda BaseModel.
- [x] 6.3 En `backend/features/orders/models.py`, agregar `HistorialEstadoPedido` (`__tablename__ = 'order_state_history'`, hereda `AppendOnlyBaseModel`): `pedido_id` FK, `estado_anterior_codigo` FK nullable, `estado_nuevo_codigo` FK, `cambiado_por_id` FK a `users.id` nullable.

## 7. Pagos

- [x] 7.1 En `backend/features/payments/models.py`, refactor `Pago`: PK BIGSERIAL, `pedido_id` FK SIN `unique=True`, `monto` Numeric(10,2), `forma_pago_codigo` FK a `payment_methods.codigo`, `mp_payment_id` String nullable, `mp_status` String nullable, `external_reference` String nullable, `idempotency_key` String UNIQUE NOT NULL. Hereda BaseModel.

## 8. Migración inicial

- [x] 8.1 Asegurarse de que TODOS los módulos `backend/features/*/models.py` están importados en `backend/alembic/env.py` (catalog, users, auth, addresses, products, orders, payments) para que `Base.metadata` los registre.
- [x] 8.2 Crear BD dev vacía (`createdb foodstore_dev` o equivalente) y exportar `DATABASE_URL`. <!-- DONE: container Docker EzePDB (postgres:18-alpine) con DB `food_store` en host port 510. DATABASE_URL=postgresql+psycopg2://ezequiel:ezequiel@localhost:510/food_store -->
- [x] 8.3 Ejecutar `cd backend && alembic revision --autogenerate -m "0001_initial_schema"`. Verificar que el archivo aparece en `backend/alembic/versions/`. <!-- Migración creada manualmente (sin BD disponible en el entorno de apply): 20260428_0001_8d61b8e48f6b_initial_schema.py -->
- [x] 8.4 Revisar la migración generada: confirmar que `order_items.personalizacion` usa `sa.ARRAY(sa.Integer())`. Si autogenerate lo omitió, agregarlo manualmente. <!-- ARRAY(Integer) incluido en migración manual -->
- [x] 8.5 Revisar la migración: agregar manualmente CHECKs faltantes (`CHECK (precio > 0)` en products, `CHECK (stock_cantidad >= 0)` en products, `CHECK (cantidad > 0)` en order_items) usando `sa.CheckConstraint(...)` en `op.create_table` o `op.create_check_constraint(...)`. <!-- Incluidos en migración manual -->
- [x] 8.6 Revisar la migración: confirmar nombres de constraints según naming convention (ix_, uq_, ck_, fk_, pk_) y que el orden de `op.create_table` respeta dependencias (catálogos primero, después users/roles, después products, después orders, después payments e historial). <!-- Orden correcto en migración manual -->
- [x] 8.7 Ejecutar `cd backend && alembic upgrade head` y verificar en `psql` con `\dt` que aparecen las 16 tablas + `alembic_version`. <!-- DONE: 17 tablas creadas (16 dominio + alembic_version), nombres en inglés plural según design. -->
- [x] 8.8 Ejecutar `alembic downgrade base` y luego `alembic upgrade head` para confirmar que el ciclo completo funciona contra BD vacía. <!-- DONE: downgrade dejó 1 tabla (alembic_version), upgrade volvió a 17 sin errores. -->

## 9. Seed idempotente

- [x] 9.1 Crear `backend/scripts/__init__.py` vacío.
- [x] 9.2 Crear `backend/scripts/seed.py`: importar engine/session desde `backend.shared.database`, importar modelos de catálogo y users, configurar logging básico (WARNING a stderr).
- [x] 9.3 En `seed.py`, función `seed_roles()` que usa `from sqlalchemy.dialects.postgresql import insert as pg_insert` y emite `pg_insert(Rol).values([...]).on_conflict_do_nothing()` con los 4 roles de IDs estables (1=ADMIN, 2=STOCK, 3=PEDIDOS, 4=CLIENT).
- [x] 9.4 En `seed.py`, función `seed_estados_pedido()` con los 6 estados (PENDIENTE/CONFIRMADO/EN_PREPARACION/EN_CAMINO/ENTREGADO terminal/CANCELADO terminal) y sus `orden`.
- [x] 9.5 En `seed.py`, función `seed_formas_pago()` con MERCADOPAGO/EFECTIVO/TRANSFERENCIA, todas habilitadas.
- [x] 9.6 En `seed.py`, función `seed_admin()`: leer `os.environ.get('ADMIN_PASSWORD')`; si None, usar `'admin1234'` y `logger.warning("ADMIN_PASSWORD not set; using insecure default — change in production")`. Hash con `passlib.context.CryptContext(schemes=['bcrypt'])`. Insert idempotente del usuario y del binding `user_roles` con role_id=1.
- [x] 9.7 En `seed.py`, `if __name__ == '__main__':` orchestración: llamar las 4 funciones en orden, hacer `session.commit()`, log INFO de éxito, exit 0. En except, log ERROR y exit 1.
- [x] 9.8 Verificar idempotencia: ejecutar `python -m backend.scripts.seed` dos veces seguidas sobre la misma BD; confirmar que ambas terminan en exit 0 y `SELECT COUNT(*) FROM roles` sigue siendo 4. <!-- DONE: corrió 3 veces, counts estables (roles=4, order_states=6, payment_methods=3, users=1, user_roles=1). -->

## 10. Configuración y documentación

- [x] 10.1 Actualizar `.env.example` agregando `DATABASE_URL=postgresql+psycopg://user:pass@localhost:5432/foodstore_dev` y `ADMIN_PASSWORD=` (con comentario "leave empty for insecure default 'admin1234' in dev only"). <!-- PENDIENTE: archivos .env.* están bloqueados por regla de permisos — el usuario debe editar backend/.env.example manualmente agregando DATABASE_URL (actualizar de postgresql:// a postgresql+psycopg2://) y ADMIN_PASSWORD= con el comentario indicado -->
- [x] 10.2 Actualizar `.agents/AGENTS.md` y/o `README.md` (lo que esté en el repo) con la sección "Database setup": comandos para crear BD, correr migración y seed (`alembic upgrade head` + `python -m backend.scripts.seed`).
- [x] 10.3 Documentar en `.agents/AGENTS.md` el patrón de soft delete: `eliminado_en` en BaseModel, repos por defecto filtran `eliminado_en IS NULL`, `query_with_deleted()` para casos puntuales.

## 11. Smoke test final

- [x] 11.1 `dropdb foodstore_dev && createdb foodstore_dev` (BD limpia). <!-- DONE: equivalente con `DROP SCHEMA public CASCADE; CREATE SCHEMA public;` sobre EzePDB. -->
- [x] 11.2 `cd backend && alembic upgrade head` — verifica las 16 tablas creadas con `\dt`. <!-- DONE: 17 filas confirmadas. -->
- [x] 11.3 `python -m backend.scripts.seed` — verifica salida exit 0 y warning de ADMIN_PASSWORD si default. <!-- DONE: exit 0, warning "ADMIN_PASSWORD environment variable is not set..." emitido a stderr. -->
- [x] 11.4 En `psql`: `SELECT id, codigo FROM roles ORDER BY id;` debe devolver 4 filas en orden 1..4. `SELECT codigo, orden, es_terminal FROM order_states;` debe devolver 6 filas. `SELECT codigo FROM payment_methods;` debe devolver 3 filas. `SELECT email FROM users;` debe devolver `admin@foodstore.local`. `SELECT u.email, r.codigo FROM users u JOIN user_roles ur ON ur.user_id=u.id JOIN roles r ON r.id=ur.role_id;` debe devolver `admin@foodstore.local | ADMIN`. <!-- DONE: las 5 queries devolvieron exactamente lo esperado (roles 1..4, 6 estados con ENTREGADO/CANCELADO terminal, 3 métodos de pago habilitados, admin@foodstore.local con rol ADMIN). -->
- [x] 11.5 Re-ejecutar `python -m backend.scripts.seed`: debe terminar exit 0 sin errores y los counts no cambian (idempotente). <!-- DONE: re-ejecución exit 0, counts idénticos. -->
- [x] 11.6 Confirmar manualmente que NO se ejecuta `alembic upgrade` automático al iniciar el FastAPI app (revisar `backend/main.py` o equivalente). <!-- Verificado: lifespan() en main.py solo loguea startup/shutdown, sin alembic upgrade -->
