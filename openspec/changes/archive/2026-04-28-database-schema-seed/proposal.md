## Why

El backend tiene 5 modelos parciales heredados de `setup-backend-core` (Usuario, Producto, Pedido, DetallePedido, Pago) que divergen del ERD v5 de `docs/Integrador.txt`: usan UUID en lugar de BIGSERIAL, columnas en inglés (`created_at`) en lugar de español (`creado_en`), `DateTime` sin TZ, un `Enum` Python roto para `Role` (USER/DELIVERY) en lugar de la tabla catálogo `roles`, y `unique=True` en `Payment` que viola RN-PA08 (1:N entre Pedido y Pago). Además faltan 11 entidades del ERD (catálogos, refresh tokens, direcciones, ingredientes, historial), no hay Alembic configurado y no hay datos semilla. Por la regla del usuario "spec gana sobre código" y por las historias US-000b (modelo de datos completo) y US-000d (datos iniciales mínimos), este es el bloqueador #3 del Sprint 0: sin schema canónico ni seed, ningún feature de auth/productos/pedidos puede arrancar.

## What Changes

- **BREAKING** Refactor de `BaseModel`: PK pasa de `UUID default uuid4` a `BIGSERIAL` (`Integer primary_key=True autoincrement=True`); columnas `created_at`/`updated_at`/`deleted_at` se renombran a `creado_en`/`actualizado_en`/`eliminado_en` y todas usan `DateTime(timezone=True)`.
- **BREAKING** Refactor de los 5 modelos existentes (Usuario, Producto, Pedido, DetallePedido, Pago) para alinear al ERD v5 (campos faltantes, snapshots, FKs a catálogos, eliminar `unique=True` en Pago).
- **BREAKING** Reemplazar el `Enum` Python `Role` por la tabla catálogo `roles` (PK estable 1=ADMIN, 2=STOCK, 3=PEDIDOS, 4=CLIENT) + pivot `usuario_roles` para soportar M:N (RN-DA01).
- **BREAKING** Reemplazar el `Enum` Python `EstadoPedido` por la tabla catálogo `estado_pedidos` (PK semántica VARCHAR, columnas `orden`, `es_terminal`) y el `Enum` `FormaPago` por la tabla `formas_pago` (PK semántica VARCHAR, `habilitada`).
- Agregar 11 modelos nuevos: `roles`, `usuario_roles`, `refresh_tokens`, `direcciones_entrega`, `categorias` (autoreferencial), `ingredientes`, `producto_categorias`, `producto_ingredientes`, `formas_pago`, `estado_pedidos`, `historial_estado_pedidos` (append-only, sin `actualizado_en`).
- Configurar Alembic en `backend/alembic/` con `env.py` apuntando a `Base.metadata`, `target_metadata` cargado desde `backend.shared.database`, y generar la migración monolítica inicial `0001_initial_schema`.
- Agregar script idempotente `backend/scripts/seed.py` que carga roles (4), estados de pedido (6), formas de pago (3) y un usuario admin (`admin@foodstore.local`, password desde env `ADMIN_PASSWORD`) usando `INSERT ... ON CONFLICT DO NOTHING`.
- Agregar a `backend/requirements.txt`: `alembic`, `passlib[bcrypt]`, `python-jose[cryptography]`, `slowapi`, `mercadopago`, `pydantic-settings`.
- Documentar el patrón de soft delete (`eliminado_en` en `BaseModel`, filtro default `eliminado_en IS NULL` en repositorios).

## Capabilities

### New Capabilities
- `database-migrations`: gestión de schema con Alembic (estrategia de migración inicial monolítica, conventions de naming, autogenerate gotchas con tipos PG-specific) y carga idempotente de datos semilla mínimos (roles, catálogos, admin).

### Modified Capabilities
- `base-entities`: cambia PK de UUID a BIGSERIAL, renombra timestamps a español, agrega `eliminado_en` a todos los modelos, reemplaza enums Python por catálogos, completa los 5 modelos existentes y agrega 11 nuevos según ERD v5.

## Impact

- **Código backend**: `backend/shared/models.py` (BaseModel refactor), `backend/shared/database.py` (metadata exposure), `backend/shared/enums.py` (eliminar `Role`/`EstadoPedido`/`FormaPago`), `backend/features/{users,products,orders,payments}/models.py` (refactor + nuevos), `backend/features/{auth,catalog,addresses}/models.py` (nuevos módulos para refresh tokens, categorías/ingredientes, direcciones).
- **Infraestructura nueva**: `backend/alembic/` (config + versions), `backend/alembic.ini`, `backend/scripts/seed.py`, `backend/scripts/__init__.py`.
- **Dependencias**: `backend/requirements.txt` suma 6 paquetes (alembic, passlib[bcrypt], python-jose[cryptography], slowapi, mercadopago, pydantic-settings).
- **Configuración**: `.env.example` agrega `ADMIN_PASSWORD` (default `admin1234` con warning de logs).
- **APIs**: ninguna expuesta todavía — este change es schema + seed, no endpoints.
- **Specs vivas**: `openspec/specs/base-entities/spec.md` recibe deltas masivos; nace `openspec/specs/database-migrations/spec.md`.
- **Tests**: no se agregan en este change (smoke test manual `alembic upgrade head` + `python -m backend.scripts.seed` sobre BD vacía); las suites de integración llegan con cada feature posterior.
- **Downstream**: desbloquea `auth-backend` (#4), `products-backend` (#5), `orders-backend` (#6) y todos los features que dependen del schema.
