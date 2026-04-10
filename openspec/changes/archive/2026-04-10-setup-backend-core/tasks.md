## 1. Project Setup

- [x] 1.1 Create `backend/` directory structure with subdirectories: `features/`, `shared/`, `tests/`, `migrations/`
- [x] 1.2 Create `backend/requirements.txt` with dependencies: fastapi, uvicorn, sqlalchemy, psycopg2-binary, python-dotenv, pydantic[email], pytest, pytest-asyncio
- [x] 1.3 Create `.env` file with template entries: `DATABASE_URL`, `JWT_SECRET`, `API_PORT`, `LOG_LEVEL`, `FRONTEND_URL`
- [x] 1.4 Create `backend/.gitignore` to exclude `.env.local`, `__pycache__/`, `.pytest_cache/`, `*.pyc`
- [x] 1.5 Initialize git submodule or link for backend (if separate repo) or just add backend/ to main repo

## 2. FastAPI Application Initialization

- [x] 2.1 Create `backend/main.py` with FastAPI app instance
- [x] 2.2 Add CORS middleware configured for `["http://localhost:5173"]` (Vite dev) + environment variable for production URLs
- [x] 2.3 Add request logging middleware that logs method, path, status, and duration (ms)
- [x] 2.4 Add basic health check endpoint `GET /health` returning `{"status": "ok"}`
- [x] 2.5 Test locally: `uvicorn backend.main:app --reload` should start on `http://localhost:8000`

## 3. Environment Configuration

- [x] 3.1 Create `backend/config.py` with Pydantic BaseSettings that reads from `.env` and environment variables
- [x] 3.2 Load: `DATABASE_URL`, `JWT_SECRET`, `API_PORT`, `LOG_LEVEL`, `FRONTEND_URL`, `ENVIRONMENT` (dev/prod)
- [x] 3.3 Set defaults: `API_PORT=8000`, `LOG_LEVEL=INFO`, `ENVIRONMENT=development`
- [x] 3.4 Validate that `JWT_SECRET` is not empty; raise error on startup if missing

## 4. Logging Infrastructure

- [x] 4.1 Create `backend/logging_config.py` with logging configuration
- [x] 4.2 Set format: `[%(levelname)s] [%(asctime)s] [%(name)s] %(message)s`
- [x] 4.3 Configure root logger and FastAPI logger levels based on `LOG_LEVEL` env var
- [x] 4.4 Add to `backend/main.py` to initialize logging on startup
- [x] 4.5 Create slow query/endpoint logging (threshold: 1000ms for queries, 5000ms for endpoints)

## 5. Base Classes and Shared Infrastructure

- [x] 5.1 Create `backend/shared/` directory structure
- [x] 5.2 Create `backend/shared/models.py` with BaseModel (SQLAlchemy declarative base with id, created_at, updated_at fields)
- [x] 5.3 Create `backend/shared/repository.py` with BaseRepository class (CRUD boilerplate: create, read, update, delete, list)
- [x] 5.4 Create `backend/shared/service.py` with BaseService class (accepts repository, provides business logic layer)
- [x] 5.5 Create `backend/shared/unit_of_work.py` with UnitOfWork class (manages transaction scope, session lifecycle)
- [x] 5.6 Add soft delete support to BaseRepository (queries exclude deleted_at IS NOT NULL by default)

## 6. Database Models - Foundation

- [x] 6.1 Create `backend/shared/enums.py` with EstadoPedido enum: PENDIENTE, CONFIRMADO, EN_PREPARACIÓN, EN_CAMINO, ENTREGADO, CANCELADO
- [x] 6.2 Create FormaPago enum: EFECTIVO, TARJETA_CREDITO, MERCADOPAGO
- [x] 6.3 Create `backend/features/users/models.py` with User model: id, email (unique), username (unique), is_active, role_id, created_at, updated_at
- [x] 6.4 Create `backend/features/products/models.py` with Product model: id, name, description, price, is_active, created_at, updated_at, deleted_at
- [x] 6.5 Create `backend/features/orders/models.py` with Order model: id, user_id, total, estado, created_at, updated_at, deleted_at
- [x] 6.6 Create `backend/features/payments/models.py` with Payment model: id, order_id, amount, method, status, external_id, created_at, updated_at
- [x] 6.7 Add relationships: User.orders, Order.payment, Order.order_items (stub, items table created in separate change)

## 7. Feature Module Structure

- [x] 7.1 Create feature directory structure for each module: `backend/features/{auth,products,orders,payments,users}/` 
- [x] 7.2 In each feature, create: `__init__.py`, `router.py`, `service.py`, `repository.py`, `models.py`, `schemas.py` (for request/response)
- [x] 7.3 Create `backend/features/__init__.py` to organize feature imports
- [x] 7.4 In `backend/main.py`, import and register routers: `app.include_router(auth_router, prefix="/api/auth", tags=["auth"])`, etc.
- [x] 7.5 Ensure all routers are prefixed with `/api/` for consistency

## 8. Dependency Injection Setup

- [x] 8.1 Create `backend/dependencies.py` with dependency functions for database session, UnitOfWork, current user (placeholder)
- [x] 8.2 Implement `get_db_session()` dependency that yields SQLAlchemy session
- [x] 8.3 Implement `get_uow()` dependency that yields UnitOfWork instance
- [x] 8.4 Add to FastAPI app's `Depends()` utilities for use in routers

## 9. Testing Infrastructure

- [x] 9.1 Create `backend/tests/` directory structure: `conftest.py`, `unit/`, `integration/`
- [x] 9.2 Create `backend/tests/conftest.py` with pytest fixtures: `test_db_session`, `client` (TestClient)
- [x] 9.3 Create test database setup (use in-memory SQLite for unit tests, or Docker Compose PostgreSQL for integration tests)
- [x] 9.4 Create `backend/tests/test_main.py` with test for GET /health endpoint
- [x] 9.5 Run `pytest backend/tests/` and verify all tests pass

## 10. Documentation and Validation

- [x] 10.1 Create `backend/README.md` documenting project structure, how to run locally, how to run tests
- [x] 10.2 Document feature-first architecture and layered pattern
- [x] 10.3 Document UnitOfWork and BaseRepository usage patterns with examples
- [x] 10.4 Verify all models compile without errors: `python -c "from backend.features.users.models import User; print('OK')"`
- [x] 10.5 Verify FastAPI app starts: `python -c "from backend.main import app; print(app.title)"`
- [x] 10.6 Commit all changes with message: "feat(backend): setup core architecture, models, DI, logging"
