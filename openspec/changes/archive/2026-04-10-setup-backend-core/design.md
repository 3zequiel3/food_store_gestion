## Context

The Food Store project requires a backend API that manages users, products, orders, and payments. The architecture must be:
- **Feature-first modular**: Each business capability (users, products, orders) in its own module
- **Layered within each feature**: Router → Service → UnitOfWork → Repository → Model
- **DDD-inspired**: Domain objects represent business logic, not just ORM entities
- **Testable**: Loose coupling, dependency injection, clear boundaries between layers
- **Scalable**: PostgreSQL with Alembic migrations, connection pooling, proper transaction management

Currently: No backend exists. This change creates the scaffolding and base patterns that all downstream features will follow.

## Goals / Non-Goals

**Goals:**
- Establish FastAPI project structure with feature-first organization
- Define layered architecture pattern (Router → Service → UoW → Repository → Model)
- Create base classes for repositories, services, and models
- Set up environment configuration and logging
- Implement CORS and middleware stack
- Create pytest structure for testing
- Define domain models foundation (User, Product, Order, Payment, Role, EstadoPedido)

**Non-Goals:**
- Implementing business logic (auth, product CRUD, order FSM) — done in later changes
- Database schema creation — done in `database-schema-seed` change
- API error handling (RFC 7807) — done in `backend-error-handling-validation` change
- Payment integration — done in `payment-mercadopago-integration` change

## Decisions

### Decision 1: Feature-First Architecture
**Choice**: Each feature (auth, users, products, orders, payments) lives in `backend/features/<feature>/` with its own router, service, UoW, and repository.

**Rationale**:
- Easier to locate code (business logic lives in one place)
- Modules are independently testable
- Clear boundaries reduce coupling
- Future teams onboard faster

**Alternative considered**: Layered by type (all routers in `routes/`, all services in `services/`). ❌ Poor for larger teams; business logic scattered across directories.

### Decision 2: Layered Within Each Feature
**Choice**: Inside each feature, enforce: Router → Service → Repository → Model. Services use Unit of Work pattern for atomic transactions.

**Rationale**:
- **Router**: HTTP endpoint definitions, request/response models
- **Service**: Business logic (validations, orchestration of multiple repositories)
- **UnitOfWork**: Transaction boundary; ensures atomicity across multiple tables (e.g., creating order + order items in one tx)
- **Repository**: Data access abstraction; queries and persistence only
- **Model**: SQLAlchemy ORM entity (database table)

This pattern is essential for order creation and payment webhook handling where multiple operations must succeed or all fail.

**Alternative considered**: Direct router → model. ❌ No abstraction; tests hard to mock; business logic in HTTP layer.

### Decision 3: Pydantic v2 for Validation
**Choice**: Use Pydantic v2 for request/response models and domain validation.

**Rationale**:
- Type hints + validation at API boundary (automatic error responses)
- JSON schema generation (OpenAPI docs)
- Serialization/deserialization built-in

### Decision 4: SQLAlchemy ORM + Alembic Migrations
**Choice**: SQLAlchemy for ORM (async driver: asyncpg), Alembic for schema versioning.

**Rationale**:
- Industry standard for Python/FastAPI
- Alembic integrates with FastAPI ecosystem
- Migrations version-controlled (easy rollback, team coordination)

### Decision 5: Environment Configuration via .env
**Choice**: Use `python-dotenv` for local dev; support environment variables for production (Docker, Cloud).

**Rationale**:
- Secrets (DB password, JWT secret) never in code
- Dev/prod parity (same code, different config)
- Works with containerization

## Risks / Trade-offs

**[Risk] Layered abstraction overhead**
- Complex for simple CRUD endpoints
- → Mitigated by: Code generation for boilerplate (future); this is upfront cost that pays off as system grows

**[Risk] Async complexity**
- Team unfamiliar with async/await patterns
- → Mitigated by: Start with blocking queries (sync SQLAlchemy); migrate to async driver as needed

**[Risk] Test database setup**
- Integration tests require spinning up PostgreSQL
- → Mitigated by: Use pytest fixtures + TestContainers or Docker Compose for test environment; CI/CD runs these

**[Trade-off] Feature-first can cause code duplication**
- Each feature might duplicate validation logic
- → Accepted because: Decoupling > DRY at feature boundaries; shared utilities extracted later when pattern emerges

## Migration Plan

1. **Create `backend/` directory structure** with feature module template
2. **Install dependencies** (FastAPI, SQLAlchemy, Alembic, pytest, etc.) via `requirements.txt`
3. **Set up `backend/main.py`** with FastAPI app, CORS, middleware
4. **Create base classes** (BaseRepository, BaseService, BaseUnitOfWork) in `backend/shared/`
5. **Initialize domain models** (User, Product, Order, etc.) as SQLAlchemy models
6. **Test locally** via `uvicorn backend.main:app --reload`
7. **Commit** with no breaking changes (green field, only additions)

No rollback needed; this is foundational scaffolding.

## Open Questions

1. **Async or sync SQLAlchemy?** → Decision: Start sync (sqlalchemy sync engine + psycopg2), migrate to async (asyncpg) in `database-schema-seed` or later if performance demands it.
2. **Request logging depth?** → Decision: Log all requests (method, path, status, duration); business logic logging added per-feature.
3. **CORS allowed origins?** → Decision: `["http://localhost:5173"]` (Vite dev); production origins set via .env
