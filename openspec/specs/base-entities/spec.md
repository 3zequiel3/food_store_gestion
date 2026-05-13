# base-entities Specification

## Purpose
Define core ORM models and repository patterns for domain entities in the Food Store backend. Includes base model classes, catalog tables, business entities (users, products, orders, payments), pivot tables, and soft-delete semantics via BaseRepository.
## Requirements
### Requirement: BaseRepository enforces soft-delete semantics via `eliminado_en`
The `BaseRepository` SHALL detect at construction time whether the bound model declares an `eliminado_en` column. When present, default read paths MUST exclude soft-deleted rows and `delete()` MUST set the timestamp instead of physically removing the row. When absent, `delete()` MUST fall back to physical deletion.

#### Scenario: Default queries exclude soft-deleted rows for models with `eliminado_en`
- **WHEN** a repository is instantiated with a model that inherits from `BaseModel` (which declares `eliminado_en`)
- **AND** a row is soft-deleted (its `eliminado_en` column is non-null)
- **THEN** `read(id)`, `list()`, and `count()` MUST NOT return or count that row
- **AND** the row MUST remain physically present in the underlying table

#### Scenario: `delete()` performs soft delete on models with `eliminado_en`
- **WHEN** `repo.delete(id)` is called on a model that has the `eliminado_en` column
- **THEN** the row's `eliminado_en` is set to the current UTC timestamp
- **AND** the row is NOT physically removed from the table
- **AND** the method returns `True`

#### Scenario: `delete()` falls back to hard delete on models without `eliminado_en`
- **WHEN** `repo.delete(id)` is called on a model that does NOT declare an `eliminado_en` column (e.g. catalog tables like `Rol`)
- **THEN** the row is physically removed from the table via `session.delete(...)`
- **AND** the method returns `True`

#### Scenario: `hard_delete()` always removes the row physically
- **WHEN** `repo.hard_delete(id)` is called
- **THEN** the row is physically removed regardless of whether the model declares `eliminado_en`
- **AND** the method returns `True` if the row existed, `False` otherwise

### Requirement: BaseRepository protects immutable audit fields
The `update()` method of `BaseRepository` MUST NOT overwrite the `id` or `creado_en` fields of any entity, even if a caller passes them as keyword arguments. These fields are immutable after the row is inserted.

#### Scenario: `update()` cannot overwrite `creado_en`
- **GIVEN** a `Usuario` row inserted at timestamp `T0` (`creado_en = T0`)
- **WHEN** `repo.update(user.id, creado_en=T1)` is called with `T1 != T0`
- **THEN** the persisted `creado_en` value remains `T0`
- **AND** no exception is raised (the caller's kwarg is silently ignored)

#### Scenario: `update()` cannot overwrite `id`
- **GIVEN** a `Usuario` row with `id = N`
- **WHEN** a caller invokes `repo.update(N, **payload)` with a `payload` dict that contains `"id": 999999`
- **THEN** the call raises `TypeError` (the method signature has `id` as a positional parameter, so it collides with the splatted kwarg)
- **AND** the persisted `id` remains `N`
- **AND** no row exists with `id = 999999`
- **AND** the row is not otherwise mutated

## MODIFIED Requirements

### Requirement: Base model infrastructure
The system SHALL provide a `BaseModel` class with common fields (`id`, `creado_en`, `actualizado_en`, `eliminado_en`) that all domain entities inherit from, plus a separate `AppendOnlyBaseModel` for log-style entities that never update.

#### Scenario: BaseModel provides BIGSERIAL id
- **WHEN** an entity inherits from `BaseModel`
- **THEN** it automatically has an `id` field of type `Integer`, `primary_key=True`, `autoincrement=True` mapping to PostgreSQL `BIGSERIAL`

#### Scenario: BaseModel provides timezone-aware timestamps
- **WHEN** an entity inherits from `BaseModel`
- **THEN** it automatically has `creado_en` (`DateTime(timezone=True)`, `server_default=func.now()`, `nullable=False`) and `actualizado_en` (`DateTime(timezone=True)`, `server_default=func.now()`, `onupdate=func.now()`, `nullable=False`)

#### Scenario: BaseModel provides nullable soft-delete column
- **WHEN** an entity inherits from `BaseModel`
- **THEN** it automatically has `eliminado_en` (`DateTime(timezone=True)`, `nullable=True`, `default=None`) and is included in default repository filters

#### Scenario: AppendOnlyBaseModel excludes update and soft-delete fields
- **WHEN** an entity inherits from `AppendOnlyBaseModel`
- **THEN** it has `id` (BIGSERIAL) and `creado_en` (`DateTime(timezone=True)`, `server_default=func.now()`) but does NOT have `actualizado_en` or `eliminado_en`

### Requirement: User entity
The system SHALL define a `Usuario` ORM model mapped to table `users` aligned with ERD v5.

#### Scenario: Usuario contains required fields
- **WHEN** the `Usuario` model is defined
- **THEN** it has `id` (BIGSERIAL PK), `email` (`String`, `unique=True`, `nullable=False`), `password_hash` (`String`, `nullable=False`), `nombre` (`String`, `nullable=False`), `apellido` (`String`, `nullable=False`), `telefono` (`String`, `nullable=True`), `is_active` (`Boolean`, `nullable=False`, `default=True`), `creado_en`, `actualizado_en`, `eliminado_en`

#### Scenario: Usuario has many-to-many relationship to Rol
- **WHEN** a `Usuario` instance is loaded
- **THEN** it has a `roles` relationship populated via the `user_roles` pivot table (no `role_id` direct FK on `users`)

#### Scenario: Usuario does not expose username
- **WHEN** the `Usuario` model is defined
- **THEN** there is NO `username` column (login is by email per RN-DA08)

### Requirement: Product entity
The system SHALL define a `Producto` ORM model mapped to table `products` aligned with ERD v5.

#### Scenario: Producto contains required fields
- **WHEN** the `Producto` model is defined
- **THEN** it has `id` (BIGSERIAL PK), `nombre` (`String`, `nullable=False`), `descripcion` (`Text`, `nullable=True`), `precio` (`Numeric(10, 2)`, `nullable=False`, CHECK `precio > 0`), `stock_cantidad` (`Integer`, `nullable=False`, `default=0`, CHECK `stock_cantidad >= 0`), `disponible` (`Boolean`, `nullable=False`, `default=True`), `imagen_url` (`String`, `nullable=True`), `creado_en`, `actualizado_en`, `eliminado_en`

#### Scenario: Producto has many-to-many relationships to Categoria and Ingrediente
- **WHEN** a `Producto` instance is loaded
- **THEN** it has `categorias` (via `product_categories`) and `ingredientes` (via `product_ingredients`) relationships

### Requirement: Order entity
The system SHALL define a `Pedido` ORM model mapped to table `orders` aligned with ERD v5.

#### Scenario: Pedido contains required fields
- **WHEN** the `Pedido` model is defined
- **THEN** it has `id` (BIGSERIAL PK), `user_id` (FK to `users.id`, `nullable=False`), `direccion_entrega_id` (FK to `delivery_addresses.id`, `nullable=False`), `direccion_snapshot` (`String`, `nullable=False`, snapshot of address text at order time), `total` (`Numeric(10, 2)`, `nullable=False`), `costo_envio` (`Numeric(10, 2)`, `nullable=False`, `default=0`), `forma_pago_codigo` (FK to `payment_methods.codigo`, `nullable=False`), `estado_codigo` (FK to `order_states.codigo`, `nullable=False`, `default='PENDIENTE'`), `notas` (`Text`, `nullable=True`), `creado_en`, `actualizado_en`, `eliminado_en`

#### Scenario: Pedido does not store delivery address as plain string
- **WHEN** the `Pedido` model is defined
- **THEN** there is NO `delivery_address` column of type plain `String`; address is referenced via `direccion_entrega_id` FK and snapshotted via `direccion_snapshot`

### Requirement: Order item entity
The system SHALL define a `DetallePedido` ORM model mapped to table `order_items` aligned with ERD v5.

#### Scenario: DetallePedido contains snapshot fields and integer quantity
- **WHEN** the `DetallePedido` model is defined
- **THEN** it has `id` (BIGSERIAL PK), `pedido_id` (FK to `orders.id`, `nullable=False`), `producto_id` (FK to `products.id`, `nullable=False`), `nombre_snapshot` (`String`, `nullable=False`), `precio_snapshot` (`Numeric(10, 2)`, `nullable=False`), `cantidad` (`Integer`, `nullable=False`, CHECK `cantidad > 0`), `personalizacion` (`ARRAY(Integer)`, `nullable=True`, array of `ingredients.id`), `creado_en`, `actualizado_en`, `eliminado_en`

### Requirement: Payment entity
The system SHALL define a `Pago` ORM model mapped to table `payments` aligned with ERD v5 and RN-PA08 (1:N pedido↔pagos).

#### Scenario: Pago does NOT enforce 1:1 with order
- **WHEN** the `Pago` model is defined
- **THEN** the `pedido_id` FK does NOT have `unique=True`, allowing multiple payment attempts per order

#### Scenario: Pago contains MercadoPago integration fields
- **WHEN** the `Pago` model is defined
- **THEN** it has `id` (BIGSERIAL PK), `pedido_id` (FK to `orders.id`, `nullable=False`), `monto` (`Numeric(10, 2)`, `nullable=False`), `forma_pago_codigo` (FK to `payment_methods.codigo`, `nullable=False`), `mp_payment_id` (`String`, `nullable=True`, MercadoPago payment ID), `mp_status` (`String`, `nullable=True`), `external_reference` (`String`, `nullable=True`), `idempotency_key` (`String`, `unique=True`, `nullable=False`), `creado_en`, `actualizado_en`, `eliminado_en`

## REMOVED Requirements

### Requirement: Enum definitions for order state and payment status
**Reason**: ERD v5 models order states and payment methods as catalog tables (`order_states`, `payment_methods`) with semantic VARCHAR primary keys, not Python enums. RN-DA01 also requires roles as a catalog table with M:N to users, removing the rationale for an enum-based approach.
**Migration**: Replace enum imports/usages by FK references to `order_states.codigo` and `payment_methods.codigo`. Seed loads canonical values (PENDIENTE, CONFIRMADO, EN_PREPARACION, EN_CAMINO, ENTREGADO, CANCELADO for states; MERCADOPAGO, EFECTIVO, TRANSFERENCIA for methods).

## ADDED Requirements

### Requirement: Role catalog
The system SHALL define a `Rol` ORM model mapped to table `roles` with stable hardcoded IDs.

#### Scenario: Rol catalog contains canonical roles with stable IDs
- **WHEN** the seed runs
- **THEN** the `roles` table contains exactly: `(1, 'ADMIN', 'Administrador del sistema')`, `(2, 'STOCK', 'Gestiona inventario')`, `(3, 'PEDIDOS', 'Gestiona pedidos y entregas')`, `(4, 'CLIENT', 'Cliente final')`, all idempotent on re-run

#### Scenario: Rol has unique codigo
- **WHEN** the `Rol` model is defined
- **THEN** it has `id` (`Integer` PK), `codigo` (`String`, `unique=True`, `nullable=False`), `descripcion` (`String`, `nullable=True`)

### Requirement: User-Role pivot
The system SHALL define a `UsuarioRol` association mapped to table `user_roles` for M:N between users and roles (RN-DA01).

#### Scenario: User can have multiple roles
- **WHEN** a `Usuario` is associated with two `Rol` rows via `user_roles`
- **THEN** loading the user exposes both roles in the `roles` relationship

#### Scenario: Pivot uses composite primary key
- **WHEN** the `UsuarioRol` model is defined
- **THEN** the primary key is composite `(user_id, role_id)` and both columns are FKs

### Requirement: Refresh token entity
The system SHALL define a `RefreshToken` ORM model mapped to table `refresh_tokens` for JWT refresh-token persistence.

#### Scenario: RefreshToken contains required fields
- **WHEN** the `RefreshToken` model is defined
- **THEN** it has `id` (BIGSERIAL PK), `user_id` (FK to `users.id`, `nullable=False`), `token_hash` (`String`, `unique=True`, `nullable=False`), `expires_at` (`DateTime(timezone=True)`, `nullable=False`), `revoked_at` (`DateTime(timezone=True)`, `nullable=True`), `creado_en`, `actualizado_en`, `eliminado_en`

### Requirement: Delivery address entity
The system SHALL define a `DireccionEntrega` ORM model mapped to table `delivery_addresses`.

#### Scenario: DireccionEntrega contains required fields
- **WHEN** the `DireccionEntrega` model is defined
- **THEN** it has `id` (BIGSERIAL PK), `user_id` (FK to `users.id`, `nullable=False`), `calle` (`String`, `nullable=False`), `numero` (`String`, `nullable=False`), `ciudad` (`String`, `nullable=False`), `codigo_postal` (`String`, `nullable=False`), `referencia` (`String`, `nullable=True`), `es_principal` (`Boolean`, `nullable=False`, `default=False`), `creado_en`, `actualizado_en`, `eliminado_en`

### Requirement: Category catalog with self-reference
The system SHALL define a `Categoria` ORM model mapped to table `categories` with a self-referential parent.

#### Scenario: Categoria supports tree structure
- **WHEN** the `Categoria` model is defined
- **THEN** it has `id` (BIGSERIAL PK), `nombre` (`String`, `nullable=False`), `padre_id` (FK to `categories.id`, `nullable=True`), `creado_en`, `actualizado_en`, `eliminado_en` and a self-referential relationship `padre`/`hijos`

### Requirement: Ingredient entity
The system SHALL define an `Ingrediente` ORM model mapped to table `ingredients`.

#### Scenario: Ingrediente flags allergens
- **WHEN** the `Ingrediente` model is defined
- **THEN** it has `id` (BIGSERIAL PK), `nombre` (`String`, `unique=True`, `nullable=False`), `es_alergeno` (`Boolean`, `nullable=False`, `default=False`), `creado_en`, `actualizado_en`, `eliminado_en`

### Requirement: Product-Category pivot
The system SHALL define a `ProductoCategoria` association mapped to table `product_categories` for M:N between products and categories.

#### Scenario: Pivot uses composite primary key
- **WHEN** the `ProductoCategoria` model is defined
- **THEN** the primary key is composite `(product_id, category_id)`

### Requirement: Product-Ingredient pivot
The system SHALL define a `ProductoIngrediente` association mapped to table `product_ingredients` for M:N between products and ingredients.

#### Scenario: Pivot uses composite primary key
- **WHEN** the `ProductoIngrediente` model is defined
- **THEN** the primary key is composite `(product_id, ingredient_id)`

### Requirement: Payment-method catalog
The system SHALL define a `FormaPago` ORM model mapped to table `payment_methods` with VARCHAR primary key.

#### Scenario: FormaPago uses semantic VARCHAR PK
- **WHEN** the `FormaPago` model is defined
- **THEN** it has `codigo` (`String` PK), `descripcion` (`String`, `nullable=False`), `habilitada` (`Boolean`, `nullable=False`, `default=True`), `creado_en`, `actualizado_en`

#### Scenario: FormaPago seed loads canonical methods
- **WHEN** the seed runs
- **THEN** the `payment_methods` table contains exactly `('MERCADOPAGO', ..., true)`, `('EFECTIVO', ..., true)`, `('TRANSFERENCIA', ..., true)`, idempotent on re-run

### Requirement: Order-state catalog
The system SHALL define an `EstadoPedido` ORM model mapped to table `order_states` with VARCHAR primary key, ordering, and terminal flag.

#### Scenario: EstadoPedido contains ordering and terminal columns
- **WHEN** the `EstadoPedido` model is defined
- **THEN** it has `codigo` (`String` PK), `descripcion` (`String`, `nullable=False`), `orden` (`Integer`, `nullable=False`), `es_terminal` (`Boolean`, `nullable=False`, `default=False`), `creado_en`, `actualizado_en`

#### Scenario: EstadoPedido seed loads canonical states with order and terminal flag
- **WHEN** the seed runs
- **THEN** the `order_states` table contains exactly: `('PENDIENTE', 1, false)`, `('CONFIRMADO', 2, false)`, `('EN_PREPARACION', 3, false)`, `('EN_CAMINO', 4, false)`, `('ENTREGADO', 5, true)`, `('CANCELADO', 6, true)`, idempotent on re-run

### Requirement: Order-state history entity (append-only)
The system SHALL define a `HistorialEstadoPedido` ORM model mapped to table `order_state_history` for trazabilidad de transiciones (RN-PA02).

#### Scenario: HistorialEstadoPedido inherits from AppendOnlyBaseModel
- **WHEN** the `HistorialEstadoPedido` model is defined
- **THEN** it inherits from `AppendOnlyBaseModel` and has NO `actualizado_en` or `eliminado_en` columns

#### Scenario: HistorialEstadoPedido contains transition fields
- **WHEN** the `HistorialEstadoPedido` model is defined
- **THEN** it has `id` (BIGSERIAL PK), `pedido_id` (FK to `orders.id`, `nullable=False`), `estado_anterior_codigo` (FK to `order_states.codigo`, `nullable=True`, allows first transition with no prior state), `estado_nuevo_codigo` (FK to `order_states.codigo`, `nullable=False`), `cambiado_por_id` (FK to `users.id`, `nullable=True`, NULL means system), `creado_en` (TIMESTAMPTZ)

### Requirement: Admin user seed
The system SHALL seed exactly one admin user during initial seed execution.

#### Scenario: Admin user is created with bcrypt hash and ADMIN role
- **WHEN** the seed runs against an empty database
- **THEN** a `Usuario` row is created with `email='admin@foodstore.local'`, `password_hash` produced by bcrypt over `os.environ.get('ADMIN_PASSWORD', 'admin1234')`, `is_active=True`, and an entry in `user_roles` linking that user to `roles.id=1` (ADMIN)

#### Scenario: Default admin password emits warning
- **WHEN** the seed runs without `ADMIN_PASSWORD` set in env
- **THEN** a WARNING-level log line is emitted indicating the insecure default is in use, and the admin is still created

#### Scenario: Re-running seed does not duplicate admin
- **WHEN** the seed runs twice in a row against the same database
- **THEN** the second run does not raise an error and does not create duplicate admin or duplicate role bindings (idempotent via `ON CONFLICT DO NOTHING`)

### Requirement: UnitOfWork SHALL implement the context manager protocol

The `UnitOfWork` class in `backend/shared/unit_of_work.py` SHALL implement `__enter__` and `__exit__` so it can be used with the `with` statement. On clean exit (`exc_type is None`) `__exit__` MUST call `self.session.commit()`. On exception, `__exit__` MUST call `self.session.rollback()`. In every case, `__exit__` MUST call `self.session.close()` in a `finally` block. `__exit__` MUST return `False` so exceptions are not suppressed.

#### Scenario: Clean exit commits the transaction

- **GIVEN** a `UnitOfWork` instance entered via `with UnitOfWork() as uow:`
- **WHEN** the body of the `with` runs to completion without raising
- **THEN** `uow.session.commit()` is called exactly once when the block exits
- **AND** `uow.session.close()` is called exactly once
- **AND** no rollback is performed

#### Scenario: Exception inside the with block triggers rollback

- **GIVEN** a `UnitOfWork` instance entered via `with UnitOfWork() as uow:`
- **WHEN** the body of the `with` raises any exception
- **THEN** `uow.session.rollback()` is called exactly once
- **AND** `uow.session.close()` is called exactly once
- **AND** the exception propagates out of the `with` block (not suppressed)

#### Scenario: __enter__ returns the UoW itself

- **WHEN** code executes `with UnitOfWork() as uow:`
- **THEN** the value bound to `uow` is the same instance that `__enter__` returned
- **AND** `uow.session` is a non-None SQLAlchemy `Session`

### Requirement: UnitOfWork SHALL create its own session by default

The `UnitOfWork.__init__` method SHALL accept an optional `session_factory: Optional[Callable]` argument. When called with no arguments (`UnitOfWork()`), the constructor MUST resolve `get_session_factory` from `backend.shared.unit_of_work`'s namespace and call it to obtain a session factory, then call that factory to construct the session and assign it to `self.session`. When called with a `session_factory` argument, the constructor MUST call that factory to obtain the session.

#### Scenario: Default constructor creates session via get_session_factory

- **GIVEN** the production environment where `get_session_factory()` returns a Postgres-bound `sessionmaker`
- **WHEN** code executes `UnitOfWork()`
- **THEN** `self.session` is a `Session` constructed by the factory returned from `get_session_factory()`
- **AND** no session was passed in by the caller

#### Scenario: Tests override session via monkeypatch of get_session_factory

- **GIVEN** test infrastructure that monkeypatches `backend.shared.unit_of_work.get_session_factory` to return a factory bound to an in-memory SQLite session
- **WHEN** a service inside its method body executes `with UnitOfWork() as uow:`
- **THEN** `uow.session` is the SQLite session injected by the test fixture
- **AND** no Postgres connection is opened

#### Scenario: Explicit session_factory argument bypasses module lookup

- **WHEN** code executes `UnitOfWork(session_factory=lambda: my_session)`
- **THEN** `self.session is my_session`
- **AND** `get_session_factory` is not called

### Requirement: Services SHALL own the transactional boundary via UnitOfWork context manager

Every service in `backend/features/<module>/service.py` (for modules `categories`, `ingredients`, `products`, `users`, `addresses`) SHALL be constructed with `__init__(self)` (no arguments). Each public method of these services SHALL open its own `with UnitOfWork() as uow:` block, register the required repositories inside the block, execute the use case logic, and rely on the context manager's `__exit__` to perform the `commit()`. Service methods MUST NOT receive a `UnitOfWork` instance as an argument from the caller.

#### Scenario: Service is constructed without arguments

- **WHEN** a router instantiates a service via `CategoryService()`, `IngredientService()`, `ProductService()`, `UserProfileService()`, or `AddressService()`
- **THEN** the constructor accepts no positional or keyword arguments related to transactional state
- **AND** the resulting instance has no `self.uow`, `self.repo`, or other transactional-scoped attributes

#### Scenario: Service method opens its own UnitOfWork context

- **GIVEN** any public method of a service in scope (e.g. `CategoryService.create`, `ProductService.set_categorias`, `UserProfileService.update_profile`)
- **WHEN** the method is invoked
- **THEN** the method body contains a `with UnitOfWork() as uow:` block that wraps the entire use case logic
- **AND** the repositories are registered (`uow.register_repository(...)`) inside that `with` block
- **AND** the method does NOT call `uow.commit()` explicitly (the context manager's `__exit__` performs the commit)

#### Scenario: Service method completes the use case in one transaction

- **WHEN** a router invokes a service method that performs multiple repository operations (e.g. `AddressService.set_principal` clears the previous principal and sets the new one)
- **THEN** all operations execute inside the same `with UnitOfWork() as uow:` block
- **AND** all operations commit atomically when the block exits without exception
- **AND** all operations roll back atomically if any operation raises

### Requirement: Routers SHALL NOT depend on UnitOfWork

No router in `backend/features/<module>/router.py` (for modules `categories`, `ingredients`, `products`, `users`, `addresses`) SHALL declare `uow: UnitOfWork = Depends(get_uow)` as a parameter. The function `get_uow` SHALL NOT exist in `backend/dependencies.py` after the change is archived. Routers SHALL NOT call `uow.commit()`, `uow.rollback()`, or any method of `UnitOfWork` directly.

#### Scenario: Router endpoint signature has no uow parameter

- **GIVEN** any endpoint in `categories/router.py`, `ingredients/router.py`, `products/router.py`, `users/router.py`, or `addresses/router.py`
- **WHEN** inspecting the endpoint's function signature
- **THEN** there is no parameter typed as `UnitOfWork`
- **AND** there is no `Depends(get_uow)` reference

#### Scenario: get_uow is removed from dependencies module

- **WHEN** importing `backend.dependencies`
- **THEN** the symbol `get_uow` does NOT exist
- **AND** any attempt to `from backend.dependencies import get_uow` raises `ImportError`

#### Scenario: Router does not invoke uow.commit() or uow.rollback()

- **GIVEN** any endpoint in the modules in scope
- **WHEN** searching the body of the endpoint function
- **THEN** there is no call to `uow.commit()`, `uow.rollback()`, or `uow.close()`
- **AND** the endpoint instantiates the service via `Service()` (no arguments) and delegates entirely

### Requirement: Double-read pattern SHALL be collapsed into a single service call

The endpoints `PUT /products/{producto_id}/categorias` and `PATCH /users/me` SHALL invoke their respective service exactly once per request. The service method SHALL perform both the mutation and the hydrated read inside the same `with UnitOfWork() as uow:` block, returning the fully-loaded entity ready for the response schema. Routers SHALL NOT call the service twice with a `commit()` between calls.

In addition, **every entity returned by a service method after its `UnitOfWork` block has exited MUST remain usable by Pydantic `model_validate(...)` in the router**, without triggering any further database access. Concretely: after `UoW.__exit__()` has run `commit()` + `close()`, all attributes consumed by the response schema — scalar columns, server-defaults populated during the commit (e.g. `creado_en`, `actualizado_en`, `estado_codigo` resolved by trigger), and any many-to-many or one-to-many relationships exposed in that schema — MUST be readable from the returned ORM instance without raising `DetachedInstanceError` and without issuing a lazy SELECT. The mechanism is twofold:

1. The session factory in `backend/shared/database.py` MUST be configured with `expire_on_commit=False` so scalar attributes (including server-default columns refreshed pre-commit) survive `session.commit()`.
2. Any relationship that appears in a response schema (e.g. `Usuario.roles` in `ProfileResponse`) MUST be eager-loaded by the repository call that produces the returned entity (typically via `selectinload`), BEFORE `UoW.__exit__()` runs. `expire_on_commit=False` does NOT cover relationships that were never loaded inside the block.

#### Scenario: products.set_categorias returns the hydrated detail in one call

- **WHEN** the router endpoint `PUT /products/{producto_id}/categorias` invokes `ProductService.set_categorias(producto_id, categoria_ids)`
- **THEN** the service replaces the `product_categories` pivot rows AND returns a `Producto` (or detail object) with categorias and ingredientes already loaded
- **AND** all DB operations occur inside the same `with UnitOfWork() as uow:` block
- **AND** the router does not call any other service method before returning the response

#### Scenario: users.update_profile returns the hydrated profile in one call

- **WHEN** the router endpoint `PATCH /users/me` invokes `UserProfileService.update_profile(user_id, payload)`
- **THEN** the service updates the user row AND returns a `Usuario` with relationships hydrated for the response schema
- **AND** all DB operations occur inside the same `with UnitOfWork() as uow:` block
- **AND** the router does not call `get_profile` separately after the update

#### Scenario: Returned ORM entity is serializable after UoW commit (PATCH /users/me)

- **GIVEN** a request to `PATCH /users/me` with a valid payload, executed against a real Postgres database
- **WHEN** `UserProfileService.update_profile(...)` returns a `Usuario` instance and its `with UnitOfWork() as uow:` block has already exited (commit + close completed)
- **AND** the router constructs the response via `ProfileResponse.model_validate(user)` (or equivalent helper) AFTER the `with` block
- **THEN** the call MUST NOT raise `sqlalchemy.orm.exc.DetachedInstanceError`
- **AND** the response includes `email`, `nombre`, `apellido`, `telefono`, `is_active`, and the list of `roles` populated from the eager-loaded relationship
- **AND** no additional SQL is issued for the response build (verified at the integration-test level by counting issued statements or asserting absence of `DetachedInstanceError`)

#### Scenario: Returned ORM entity is serializable after UoW commit (POST /direcciones/)

- **GIVEN** a request to `POST /direcciones/` with a valid payload, executed against a real Postgres database
- **WHEN** `AddressService.create(...)` returns a `DireccionEntrega` instance and its `with UnitOfWork() as uow:` block has already exited
- **AND** the router constructs the response via `DireccionRead.model_validate(address)` AFTER the `with` block
- **THEN** the call MUST NOT raise `DetachedInstanceError`
- **AND** the response includes scalar fields plus server-default timestamps `creado_en` and `actualizado_en` populated by the commit

#### Scenario: Returned ORM entity is serializable after UoW commit (POST /pedidos/)

- **GIVEN** a request to `POST /pedidos/` with a valid payload, executed against a real Postgres database
- **WHEN** `OrderService.crear_pedido(...)` returns a `Pedido` instance and its `with UnitOfWork() as uow:` block has already exited
- **AND** the router constructs the response via `PedidoRead.model_validate(pedido)` AFTER the `with` block
- **THEN** the call MUST NOT raise `DetachedInstanceError`
- **AND** the response includes `id`, `estado_codigo` (defaulted to `'PENDIENTE'` by the DB), `total`, and `creado_en` (server-default)

#### Scenario: Session factory enforces expire_on_commit=False in production

- **GIVEN** the production session factory returned by `backend.shared.database.get_session_factory()`
- **WHEN** a new session is built and a row is committed inside a UoW
- **THEN** the bound `sessionmaker` MUST have `expire_on_commit=False`
- **AND** scalar attributes of objects attached to that session remain readable after `session.commit()` and `session.close()`
- **AND** the test session factory in `backend/tests/conftest.py` mirrors this configuration (it is NOT a test-only workaround)

#### Scenario: Relationships exposed in a response schema are eager-loaded by the repo

- **GIVEN** a service method that returns an entity whose response schema exposes a many-to-many or one-to-many relationship (e.g. `Usuario.roles` in `ProfileResponse`)
- **WHEN** the entity is loaded by the repository inside the `UnitOfWork` block
- **THEN** the repository call MUST use `selectinload` (or equivalent eager-loading strategy) to populate that relationship
- **AND** the relationship MUST be hydrated BEFORE `UoW.__exit__()` runs
- **AND** relying on `expire_on_commit=False` alone to cover unloaded relationships is FORBIDDEN (it does not)
