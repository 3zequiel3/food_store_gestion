# base-entities Spec Delta — refactor-uow-to-context-manager

## ADDED Requirements

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
