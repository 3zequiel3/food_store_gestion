# Food Store Backend API

FastAPI-based backend for Food Store application with feature-first modular architecture.

## Project Structure

```
backend/
├── main.py                 # FastAPI application entry point
├── config.py              # Configuration management (Pydantic BaseSettings)
├── logging_config.py      # Logging setup
├── dependencies.py        # Dependency injection (database, UoW, auth)
├── requirements.txt       # Python dependencies
├── features/              # Feature modules
│   ├── auth/              # Authentication & authorization
│   ├── users/             # User management
│   ├── products/          # Product management
│   ├── orders/            # Order management
│   └── payments/          # Payment processing
├── shared/                # Shared infrastructure
│   ├── models.py          # BaseModel (SQLAlchemy declarative base)
│   ├── repository.py      # BaseRepository with CRUD operations
│   ├── service.py         # BaseService for business logic
│   ├── unit_of_work.py    # UnitOfWork for transaction management
│   └── enums.py           # Enums (EstadoPedido, FormaPago, Role)
├── migrations/            # Alembic database migrations
└── tests/                 # Test suite
    ├── conftest.py        # Pytest fixtures
    ├── test_main.py       # Main app tests
    ├── unit/              # Unit tests
    └── integration/       # Integration tests
```

## Architecture

### Feature-First Organization

Each feature module contains:
- `router.py` - FastAPI router with endpoints
- `service.py` - Business logic layer
- `repository.py` - Data access layer
- `models.py` - SQLAlchemy ORM models
- `schemas.py` - Pydantic request/response schemas

### Layered Pattern Within Each Feature

```
HTTP Request
    ↓
Router (HTTP endpoint definitions)
    ↓
Service (Business logic, validation, orchestration)
    ↓
UnitOfWork (Transaction boundary)
    ↓
Repository (Data access abstraction)
    ↓
Model (SQLAlchemy ORM entity)
    ↓
Database
```

### Base Classes

#### BaseModel
SQLAlchemy declarative base with common fields:
- `id` (UUID)
- `created_at` (DateTime, auto-set)
- `updated_at` (DateTime, auto-managed)
- `deleted_at` (DateTime, nullable, for soft delete)

#### BaseRepository
Provides CRUD operations:
- `create(**kwargs)` - Create new entity
- `read(id)` - Fetch by ID
- `update(id, **kwargs)` - Update entity
- `delete(id)` - Soft delete (sets deleted_at)
- `hard_delete(id)` - Permanent delete
- `list(skip, limit)` - Paginated list
- `count()` - Count non-deleted entities

Automatically excludes soft-deleted records in queries.

#### BaseService
Business logic layer:
- Wraps repository for domain operations
- Implements business rules and validations
- Used by routers for logic coordination

#### UnitOfWork
Transaction management across multiple repositories:

```python
uow = UnitOfWork(session)
try:
    # Use repositories as attributes
    user = uow.users.create(email="user@example.com")
    order = uow.orders.create(user_id=user.id, total=100)
    uow.commit()
except Exception:
    uow.rollback()
    raise
```

### Soft Delete Support

Models with `deleted_at` field use soft delete:
- Records are marked as deleted, not removed
- Queries automatically exclude deleted records
- `hard_delete()` permanently removes records

```python
# Soft delete (recommended)
repository.delete(entity_id)

# Hard delete (permanent)
repository.hard_delete(entity_id)
```

## Getting Started

### 1. Install Dependencies

```bash
cd backend
pip install -r requirements.txt
```

### 2. Set Up Environment

Copy `.env` template:
```bash
cp .env.example .env
```

Edit `.env` with your local database:
```env
DATABASE_URL=postgresql://food_user:food_password@localhost:5432/food_store
JWT_SECRET=your-super-secret-key
API_PORT=8000
ENVIRONMENT=development
LOG_LEVEL=INFO
FRONTEND_URL=http://localhost:5173
```

### 3. Create Database

```bash
# Using Docker Compose
docker-compose up -d postgres

# Or use existing PostgreSQL instance
```

### 4. Run Application

```bash
# Development with auto-reload
uvicorn backend.main:app --reload

# Production
uvicorn backend.main:app --host 0.0.0.0 --port 8000
```

App runs on `http://localhost:8000`

API docs available at:
- Swagger: `http://localhost:8000/docs`
- ReDoc: `http://localhost:8000/redoc`

## Testing

### Run All Tests

```bash
pytest backend/tests/
```

### Run Specific Test File

```bash
pytest backend/tests/test_main.py
```

### Run With Coverage

```bash
pytest backend/tests/ --cov=backend --cov-report=html
```

### Run Unit Tests Only

```bash
pytest backend/tests/unit/
```

### Run Integration Tests Only

```bash
pytest backend/tests/integration/
```

## Domain Models

### User
User accounts with roles and permissions.

```python
class User(BaseModel):
    email: str (unique)
    username: str (unique)
    password_hash: str
    is_active: bool
    role: Enum(ADMIN, USER, DELIVERY)
    orders: List[Order]
```

### Product
Menu items and catalog products.

```python
class Product(BaseModel):
    name: str
    description: str
    price: Decimal
    is_active: bool
    deleted_at: Optional[DateTime]  # Soft delete
```

### Order
Customer orders with state machine.

```python
class Order(BaseModel):
    user_id: UUID (FK)
    total: Decimal
    estado: Enum(PENDIENTE, CONFIRMADO, EN_PREPARACIÓN, EN_CAMINO, ENTREGADO, CANCELADO)
    delivery_address: str
    user: User
    payment: Payment
    order_items: List[OrderItem]
    deleted_at: Optional[DateTime]  # Soft delete
```

### Payment
Payment records and transaction tracking.

```python
class Payment(BaseModel):
    order_id: UUID (FK, unique)
    amount: Decimal
    method: Enum(EFECTIVO, TARJETA_CREDITO, MERCADOPAGO)
    status: str (PENDING, COMPLETED, FAILED)
    external_id: str (MercadoPago ID)
```

## Logging

### Configuration

Logging configured via environment:
- `LOG_LEVEL`: DEBUG, INFO, WARNING, ERROR, CRITICAL
- Format: `[LEVEL] [TIMESTAMP] [MODULE] MESSAGE`

### Request Logging

All HTTP requests are logged with:
- Method (GET, POST, etc.)
- Path
- Status code
- Duration (ms)

Example:
```
[INFO] [2024-01-15 10:30:45] [backend.main] GET /api/products → 200 OK (45ms)
```

### Slow Query/Endpoint Logging

- Queries taking >1000ms logged as WARNING
- Endpoints taking >5000ms logged as WARNING

## Configuration

### Environment Variables

| Variable | Default | Description |
|----------|---------|-------------|
| `DATABASE_URL` | `postgresql://...` | PostgreSQL connection string |
| `JWT_SECRET` | `your-super-secret-key...` | Secret for JWT token signing |
| `API_PORT` | `8000` | Server port |
| `ENVIRONMENT` | `development` | `development` or `production` |
| `LOG_LEVEL` | `INFO` | Logging level |
| `FRONTEND_URL` | `http://localhost:5173` | Frontend URL for CORS |

## CORS Configuration

By default, CORS allows:
- `http://localhost:5173` (Vite dev server)
- `http://localhost:3000` (React dev server)
- URLs in `FRONTEND_URL` environment variable

For production, set `FRONTEND_URL` to your domain:
```env
ENVIRONMENT=production
FRONTEND_URL=https://foodstore.com
```

## API Endpoints

### Health Check
```
GET /health
```

### Authentication
```
POST /api/auth/login
POST /api/auth/logout
```

### Users
```
GET    /api/users/
GET    /api/users/{user_id}
POST   /api/users/
PUT    /api/users/{user_id}
DELETE /api/users/{user_id}
```

### Products
```
GET    /api/products/
GET    /api/products/{product_id}
POST   /api/products/
PUT    /api/products/{product_id}
DELETE /api/products/{product_id}
```

### Orders
```
GET    /api/orders/
GET    /api/orders/{order_id}
POST   /api/orders/
PUT    /api/orders/{order_id}
DELETE /api/orders/{order_id}
```

### Payments
```
GET    /api/payments/{payment_id}
POST   /api/payments/
POST   /api/payments/webhook/mercadopago
```

## Development Workflow

### 1. Create Feature Module

Create directories:
```bash
mkdir -p backend/features/feature_name
touch backend/features/feature_name/__init__.py
touch backend/features/feature_name/{router,service,repository,models,schemas}.py
```

### 2. Define Models

Edit `backend/features/feature_name/models.py`:
```python
from backend.shared.models import BaseModel
from sqlalchemy import Column, String

class FeatureModel(BaseModel):
    __tablename__ = "feature_models"
    field_name = Column(String, nullable=False)
```

### 3. Create Repository

Edit `backend/features/feature_name/repository.py`:
```python
from backend.shared.repository import BaseRepository
from .models import FeatureModel

class FeatureRepository(BaseRepository[FeatureModel]):
    def __init__(self, session):
        super().__init__(session, FeatureModel)
```

### 4. Create Service

Edit `backend/features/feature_name/service.py`:
```python
from backend.shared.service import BaseService
from .repository import FeatureRepository

class FeatureService(BaseService[FeatureModel]):
    def __init__(self, repository: FeatureRepository):
        super().__init__(repository)
```

### 5. Define Schemas

Edit `backend/features/feature_name/schemas.py`:
```python
from pydantic import BaseModel

class FeatureCreate(BaseModel):
    field_name: str

class FeatureResponse(BaseModel):
    id: UUID
    field_name: str
```

### 6. Create Router

Edit `backend/features/feature_name/router.py`:
```python
from fastapi import APIRouter, Depends
from backend.dependencies import get_db_session

router = APIRouter()

@router.get("/")
async def list_features(session = Depends(get_db_session)):
    repository = FeatureRepository(session)
    service = FeatureService(repository)
    return service.get_all()
```

### 7. Register Router

In `backend/main.py`:
```python
from backend.features.feature_name.router import router as feature_router
app.include_router(feature_router, prefix="/api/feature", tags=["feature"])
```

## Troubleshooting

### Import Errors

Ensure `backend/` is in PYTHONPATH:
```bash
export PYTHONPATH="${PYTHONPATH}:$(pwd)"
```

### Database Connection Issues

Check PostgreSQL is running:
```bash
docker-compose ps postgres
```

Verify `DATABASE_URL` in `.env`.

### Tests Fail

Reset test database:
```bash
pytest backend/tests/ --tb=short
```

### Slow Queries

Enable SQL logging in development:
```env
LOG_LEVEL=DEBUG
```

## Next Steps

1. **Database Schema**: `database-schema-seed` change creates initial schema
2. **Error Handling**: `backend-error-handling-validation` change adds RFC 7807 support
3. **Authentication**: Implement JWT login/logout in auth feature
4. **Business Logic**: Implement CRUD operations in each feature
5. **Payment Integration**: MercadoPago integration in payments feature

## References

- [FastAPI Docs](https://fastapi.tiangolo.com/)
- [SQLAlchemy Docs](https://docs.sqlalchemy.org/)
- [Pydantic Docs](https://docs.pydantic.dev/2.0/)
- [Alembic Docs](https://alembic.sqlalchemy.org/)
