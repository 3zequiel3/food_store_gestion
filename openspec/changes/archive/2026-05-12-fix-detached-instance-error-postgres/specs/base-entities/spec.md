## MODIFIED Requirements

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
