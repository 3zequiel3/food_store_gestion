## Context

El change `setup-backend-core` (archivado 2026-04-10) dejó un BaseModel y 5 modelos parciales que se escribieron antes de cerrar la lectura del ERD v5 de `docs/Integrador.txt`. La regla de oro del proyecto (`CLAUDE.md`: "spec gana sobre cualquier .md") obliga a alinear el código a la spec, no al revés. Además, las historias US-000b ("modelo de datos completo y migrable") y US-000d ("datos iniciales mínimos para arrancar") son explícitas sobre el alcance: no es solo un schema, es schema + Alembic + seed idempotente. El roadmap (`docs/CHANGES.md` entrada #3) marca este change como bloqueador absoluto del Sprint 0; sin él no arrancan auth-backend (#4), products-backend (#5), ni ningún feature posterior.

El stack es FastAPI + SQLAlchemy 2.x + PostgreSQL. La estructura del backend sigue feature-folders (`backend/features/<dominio>/models.py`) con shared en `backend/shared/`. Los modelos heredan de un `BaseModel` único.

## Goals / Non-Goals

**Goals:**
- Schema canónico de las 16 entidades del ERD v5 (5 refactor + 11 nuevas) en código.
- Alembic configurado y migración inicial monolítica `0001_initial_schema` reproducible en BD vacía.
- Datos semilla mínimos cargados de forma idempotente (4 roles, 6 estados de pedido, 3 formas de pago, 1 admin).
- Patrón de soft delete documentado y aplicado coherentemente (`eliminado_en` en `BaseModel`, default filter en repos).
- Convenciones de naming cerradas (PK BIGSERIAL, columnas español, tablas inglés, timestamps con TZ) y documentadas para todos los features posteriores.

**Non-Goals:**
- No se escriben repositorios concretos ni servicios — solo modelos ORM, migración y seed.
- No se exponen endpoints HTTP (eso lo hace cada feature: auth-backend, etc.).
- No se ejecuta `alembic upgrade head` automáticamente al arranque del app (se invoca manual/CI).
- No se agregan tests automatizados; el smoke test es manual (`alembic upgrade head` + `seed.py` sobre BD vacía y vista en `\dt`).
- No se cargan datos demo (productos de ejemplo, categorías, etc.) — solo lo mínimo para autenticarse.
- No se construye un sistema de migraciones de datos (data migrations) más allá del seed; eso vendrá si un change futuro lo necesita.

## Decisions

### D1. PK strategy: BIGSERIAL para todas las entidades de dominio (catálogos exceptuados)

**Decisión**: cambiar `BaseModel.id` de `UUID(default=uuid4)` a `Integer primary_key=True autoincrement=True` (mapea a BIGSERIAL en PostgreSQL). Catálogos con PK semántica (`estado_pedidos`, `formas_pago`) usan `String` como PK. `roles` usa `Integer` con IDs estables 1..4.

**Rationale**: el ERD v5 lo prescribe explícitamente. BIGSERIAL es más barato en índices, joins y filesize en PG; los UUIDs solo aportan valor si hay merge multi-master o IDs expuestos a clientes no confiables, ninguno aplica acá. La spec gana por regla del usuario.

**Alternativas consideradas**:
- *Mantener UUID*: rechazada — viola la spec y obligaría a ignorar el ERD.
- *UUID v7 (orderable)*: rechazada — el ERD pide BIGSERIAL puntualmente y no hay caso de uso que lo requiera.

### D2. Naming: columnas en español, tablas en inglés

**Decisión**: columnas y atributos Python en español (`creado_en`, `actualizado_en`, `eliminado_en`, `nombre`, `apellido`, `precio`, `stock_cantidad`, `costo_envio`, etc.). Nombres de tabla (`__tablename__`) en inglés plural (`users`, `products`, `orders`, `order_items`, `payments`, `roles`, `categories`, `ingredients`, `payment_methods`, `order_states`, `order_state_history`, `refresh_tokens`, `delivery_addresses`, `user_roles`, `product_categories`, `product_ingredients`).

**Rationale**: el ERD v5 nombra columnas en español; mezclar es peor que cualquier extremo. Los nombres de tabla NO son prescritos por el ERD y mantener inglés (ya en uso por `setup-backend-core`) evita tocar refs SQL crudas y queda alineado con la convención SQL común. Los modelos Python son lo que ven los devs todos los días — español ahí baja la fricción cognitiva contra el ERD.

**Alternativas consideradas**:
- *Todo en inglés*: rechazada — viola ERD, cuesta mappear ERD ↔ código mentalmente todo el tiempo.
- *Todo en español incluyendo `__tablename__`*: rechazada — rompe queries SQL crudas existentes y no aporta valor (las tablas no se ven en el código día a día).

### D3. Timestamps: `DateTime(timezone=True)` universal

**Decisión**: `BaseModel.creado_en` y `BaseModel.actualizado_en` usan `DateTime(timezone=True)` (TIMESTAMPTZ en PG). Mismo criterio para `eliminado_en`, `expires_at`/`revoked_at` de refresh_tokens, y `cambiado_en` de historial_estado_pedidos. Los defaults se generan con `func.now()` en server, no con `datetime.utcnow()` en Python.

**Rationale**: el ERD pide TIMESTAMPTZ explícitamente para refresh_tokens e historial. Tener mitad TZ-aware y mitad naive es la receta de bugs sutiles (ej. comparar tokens expirados entre uvicorn y Postgres). El costo de unificar todo a TZ-aware es ~10 LOC en BaseModel y desaparece la categoría completa de bugs. `func.now()` deja la fuente de verdad en el motor.

**Alternativas consideradas**:
- *Mantener `DateTime` plano*: rechazada — viola ERD y crea inconsistencia.
- *Aplicar TZ solo donde el ERD lo pide explícitamente*: rechazada — costo casi cero por unificar y elimina footguns.

### D4. Roles como tabla catálogo + pivot M:N (no enum Python)

**Decisión**: eliminar `enum Role` de `backend/shared/enums.py`. Crear tabla `roles (id INTEGER PK, codigo VARCHAR UNIQUE, descripcion VARCHAR)` con IDs estables hardcoded en seed: 1=ADMIN, 2=STOCK, 3=PEDIDOS, 4=CLIENT. Crear pivot `user_roles (user_id BIGINT FK, role_id INTEGER FK, PRIMARY KEY (user_id, role_id))` para relación M:N (RN-DA01 permite múltiples roles por usuario). El campo `role` actualmente en `users` se elimina; el acceso queda vía `user.roles` (relationship).

**Rationale**: la regla de negocio RN-DA01 permite a un usuario tener múltiples roles (ej. admin que también es CLIENT). Un enum Python de un solo valor no lo modela. Tabla catálogo además permite agregar roles sin migración de schema (solo seed update) y deja descripción legible. IDs estables evitan que el seed los re-asigne.

**Alternativas consideradas**:
- *Enum Python con campo `roles VARCHAR[]`*: rechazada — pierde integridad referencial y filtros eficientes.
- *Tabla catálogo + FK 1:N en `users`*: rechazada — no soporta M:N que pide RN-DA01.

### D5. Estados de pedido y formas de pago como catálogos con PK semántica VARCHAR

**Decisión**: `estado_pedidos (codigo VARCHAR PK, descripcion VARCHAR, orden INTEGER, es_terminal BOOLEAN)` con valores seed: PENDIENTE(orden=1), CONFIRMADO(2), EN_PREPARACION(3), EN_CAMINO(4), ENTREGADO(5, es_terminal=true), CANCELADO(6, es_terminal=true). `formas_pago (codigo VARCHAR PK, descripcion VARCHAR, habilitada BOOLEAN)` con valores: MERCADOPAGO, EFECTIVO, TRANSFERENCIA, todas habilitadas. `orders.estado_codigo` y `orders.forma_pago_codigo` son FKs a estos catálogos.

**Rationale**: el ERD lo modela así. PK semántica VARCHAR (no INTEGER) hace que joins/filtros/logs sean legibles sin lookup (`WHERE estado_codigo = 'ENTREGADO'`). `orden` permite UI ordenada por flujo. `es_terminal` permite validar transiciones sin hardcodear. `habilitada` permite desactivar un método de pago sin migración.

**Alternativas consideradas**:
- *Mantener Enum Python*: rechazada — viola ERD, agregar un estado nuevo (ej. `EN_REVISION`) requiere deploy de código.
- *Catálogo con PK INTEGER*: rechazada — pierde legibilidad y obliga a JOIN para ver estado en logs.

### D6. Soft delete: `eliminado_en` en `BaseModel`, filtro default en repos

**Decisión**: `BaseModel.eliminado_en: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True, default=None)`. Repositorios (en changes posteriores) tienen método base `query()` que aplica `WHERE eliminado_en IS NULL`; método `query_with_deleted()` para casos puntuales (auditoría/admin). Excepción: `historial_estado_pedidos` es append-only y NO usa soft delete (ver D8).

**Rationale**: documentar el patrón ahora evita inconsistencias en cada feature. Tenerlo en `BaseModel` lo hace por defecto en TODA entidad, eliminando "uy me olvidé de agregarle soft delete a X". El filtro en repos es la convención (no en relationships SQLAlchemy) porque un `relationship()` con filter loaded no se actualiza si cambia el state.

**Alternativas consideradas**:
- *Hard delete*: rechazada — el ERD lo modela como soft, y para auditoría (logging-audit ya activo) necesitamos preservar.
- *Trigger SQL `INSTEAD OF DELETE`*: rechazada — magia oculta, dolor de testear, no aporta vs. patrón en repo.
- *Mixin opcional `SoftDeleteMixin`*: rechazada — el ERD pide soft delete en casi todas las entidades de dominio; un default en BaseModel con opt-out vía filter en repo es más simple.

### D7. `historial_estado_pedidos` con base alternativa (append-only)

**Decisión**: crear `AppendOnlyBaseModel` (o usar `__abstract__ = True` en BaseModel y derivar dos bases: `BaseModel` con `actualizado_en`/`eliminado_en` y `AppendOnlyBaseModel` solo con `id` + `creado_en`). `HistorialEstadoPedido` hereda de `AppendOnlyBaseModel`: tiene `id`, `pedido_id` FK, `estado_anterior_codigo` FK nullable (primer estado no tiene anterior), `estado_nuevo_codigo` FK, `cambiado_por_id` FK a users nullable (sistema), `creado_en` (TIMESTAMPTZ). Sin `actualizado_en`. Sin `eliminado_en`.

**Rationale**: un historial que se puede modificar no es un historial. RN-PA02 exige trazabilidad de transiciones. La forma más limpia de modelarlo es hacer físicamente imposible el UPDATE (sin columna `actualizado_en` el ORM no la pisa, y los repos del historial van a ser solo `insert` y `select`). Separar la base evita el footgun de modelos que heredan campos que no aplican.

**Alternativas consideradas**:
- *Mantener un solo BaseModel y dejar `actualizado_en` nullable*: rechazada — la presencia del campo invita a updates indebidos y confunde a los repos.
- *Trigger PG que rechaza UPDATEs*: futuro, opcional — capa adicional de defensa pero no reemplaza el modelado limpio.

### D8. Alembic: migración inicial monolítica, no autoupgrade

**Decisión**: configurar Alembic en `backend/alembic/`, con `alembic.ini` apuntando a `backend/alembic/`, `script_location = alembic`. `env.py` importa `Base.metadata` desde `backend.shared.database` y configura `target_metadata = Base.metadata`. `compare_type = True` y `compare_server_default = True` en context.configure para que autogenerate detecte cambios de tipo. Generar la primera migración con `alembic revision --autogenerate -m "0001_initial_schema"` y commit del archivo resultante (no se mantiene a mano). NO hay `alembic upgrade head` automático en el startup del FastAPI app: se ejecuta manualmente o vía CI/script de bootstrap.

**Rationale**: monolítico para la inicial es estándar (no tiene sentido fragmentar el primer schema en 16 revisions). No-autoupgrade evita que un deploy accidental modifique schema en entornos productivos sin revisión humana. El gotcha conocido de autogenerate es que NO detecta `ARRAY(Integer)` ni CHECK constraints custom — el plan de revisión humana de la migración generada está en tasks.md.

**Alternativas consideradas**:
- *Una migración por entidad*: rechazada — caos, no aporta granularidad real (no se va a hacer rollback parcial de un schema inicial).
- *Auto-upgrade en startup*: rechazada — viola el principio "no magia en deploys" y rompe en multi-instancia.
- *Drop-create con `Base.metadata.create_all()`*: rechazada — funciona pero deja el proyecto sin Alembic configurado, bloqueando todos los changes futuros que necesiten migrar.

### D9. Seed idempotente con `INSERT ... ON CONFLICT DO NOTHING`

**Decisión**: `backend/scripts/seed.py` ejecutable como módulo (`python -m backend.scripts.seed`). Carga: 4 roles, 6 estados, 3 formas de pago, 1 admin. Usa `pg_insert(...).on_conflict_do_nothing()` (de `sqlalchemy.dialects.postgresql.insert`) para que ejecutarlo dos veces no falle ni duplique. Password admin: leído de env `ADMIN_PASSWORD`; si no está set, default `admin1234` y log de WARNING ruidoso ("ADMIN_PASSWORD not set, using insecure default — change immediately"). Hash con `passlib.bcrypt`.

**Rationale**: idempotencia hace el seed seguro en CI, en re-deploys y en local sin tener que limpiar la BD. `on_conflict_do_nothing` es nativo de PG, más rápido y menos propenso a races que `SELECT ... INSERT IF NOT EXISTS` en Python. El default con warning balancea developer-experience (corre out-of-the-box en local) con seguridad (grita en logs si llega a prod). Bcrypt porque RN-DA08 lo manda.

**Alternativas consideradas**:
- *SQL plano vía psql*: rechazada — pierde integración con el modelo de SQLAlchemy y el hash bcrypt.
- *Fixture con SQL*: rechazada — duplica el modelo en otro formato.
- *Forzar `ADMIN_PASSWORD` siempre*: rechazada — fricción en setup local; mejor warning visible.

## Risks / Trade-offs

- **[Riesgo] Refactor masivo del BaseModel rompe los modelos existentes** → Mitigación: en este change se refactorean los 5 modelos en el mismo commit que el BaseModel; no hay etapa intermedia donde el código compile a medias. Migración monolítica desde cero (no incremental) en BD vacía.
- **[Riesgo] Autogenerate de Alembic NO detecta `ARRAY(Integer)`, CHECK constraints, índices funcionales ni server_default custom** → Mitigación: tasks.md tiene un step explícito de "revisar migración generada y agregar manualmente arrays/CHECKs faltantes" antes del primer commit. Conocido y documentado.
- **[Riesgo] Default `ADMIN_PASSWORD=admin1234` se filtra a producción** → Mitigación: WARNING ruidoso al boot del seed cuando se usa default; documentado en `.env.example` y README; el script de bootstrap de prod debe setear la env antes.
- **[Riesgo] Idempotencia del seed depende de UNIQUE constraints** → Mitigación: roles tiene UNIQUE en `codigo`, estados/formas tienen PK semántica VARCHAR, usuario admin tiene UNIQUE en `email`. Verificado en spec ADDED.
- **[Trade-off] BIGSERIAL expone IDs predecibles si se usan en URLs públicas** → Aceptado: este proyecto no expone IDs en URLs (las API usan slugs/UUIDs externos donde aplica, ej. `mp_payment_id`); si en el futuro un endpoint público necesita ID opaco, se agrega un `external_id` UUID a la entidad puntual.
- **[Trade-off] Tabla `roles` con PK INTEGER hardcoded en seed (1..4) acopla código a IDs específicos** → Aceptado: los códigos string (`ADMIN`, `STOCK`, etc.) son la API estable para el código aplicación; los IDs INTEGER son detalle interno y solo aparecen en JOINs.

## Migration Plan

1. Configurar Alembic y setear `env.py` ANTES de tocar modelos (para que el `--autogenerate` posterior compare contra el modelo refactoreado vs. una BD vacía).
2. Refactor de `BaseModel` y `enums.py` (eliminar enums de Role/EstadoPedido/FormaPago).
3. Refactor de los 5 modelos existentes + creación de los 11 nuevos en una sola serie de commits (no sirve mergear por mitad).
4. `alembic revision --autogenerate -m "0001_initial_schema"` en BD vacía.
5. Revisar migración generada: agregar manualmente `ARRAY(Integer)` para `personalizacion`, CHECK constraints (ej. `precio > 0`), índices compuestos del ERD.
6. Smoke test: drop BD dev → `alembic upgrade head` → `python -m backend.scripts.seed` → `\dt` en psql verifica las 16 tablas + filas seed.
7. Ningún rollback automatizado: si hay que revertir, drop BD dev y volver al commit anterior. En prod no aplica todavía (no hay prod).

## Open Questions

- ¿Vale la pena agregar `description = Column(Text)` con default `''` o `None` en catálogos para futura UI admin? — propuesta: nullable, sin default; agregar contenido en seed solo donde aplique.
- ¿El campo `personalizacion INTEGER[]` en `order_items` necesita FK array a `ingredients(id)`? PG no soporta FK en arrays — la integridad queda a nivel aplicación. Dejarlo así y documentar; si se vuelve un problema, migrar a tabla `order_item_ingredients` en un change futuro.
- ¿Index compuesto `(user_id, eliminado_en)` en `orders` desde el inicio? — el ERD no lo pide; agregar en el change que introduzca queries reales (orders-backend) cuando se sepa el patrón de acceso.
