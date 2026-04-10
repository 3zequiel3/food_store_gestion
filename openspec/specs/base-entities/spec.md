## ADDED Requirements

### Requirement: Base domain models
The system SHALL define foundational SQLAlchemy ORM models for User, Product, Order, and Payment entities with standard fields and relationships stubs (business logic relationships added later).

#### Scenario: User model exists with required fields
- **WHEN** the User model is defined
- **THEN** it contains fields: `id` (UUID), `email` (unique, string), `username` (unique, string), `is_active` (boolean), `created_at`, `updated_at`, `role_id` (foreign key to Role)

#### Scenario: Product model exists with required fields
- **WHEN** the Product model is defined
- **THEN** it contains fields: `id` (UUID), `name` (string), `description` (text), `price` (decimal), `is_active` (boolean), `created_at`, `updated_at`

#### Scenario: Order model exists with required fields
- **WHEN** the Order model is defined
- **THEN** it contains fields: `id` (UUID), `user_id` (foreign key), `total` (decimal), `estado` (enum reference), `created_at`, `updated_at`, `deleted_at` (soft delete)

#### Scenario: Payment model exists with required fields
- **WHEN** the Payment model is defined
- **THEN** it contains fields: `id` (UUID), `order_id` (foreign key), `amount` (decimal), `method` (enum reference), `status` (enum reference), `external_id` (string for MercadoPago ID), `created_at`, `updated_at`

### Requirement: Enum definitions for order state and payment status
The system SHALL define Python Enums for EstadoPedido (order states) and FormaPago (payment methods).

#### Scenario: EstadoPedido enum is defined
- **WHEN** the EstadoPedido enum is created
- **THEN** it contains values: PENDIENTE, CONFIRMADO, EN_PREPARACIÓN, EN_CAMINO, ENTREGADO, CANCELADO

#### Scenario: FormaPago enum is defined
- **WHEN** the FormaPago enum is created
- **THEN** it contains values: EFECTIVO, TARJETA_CREDITO, MERCADOPAGO

### Requirement: Base model infrastructure
The system SHALL provide a BaseModel class with common fields (id, created_at, updated_at) that all entities inherit from.

#### Scenario: BaseModel provides id field
- **WHEN** an entity inherits from BaseModel
- **THEN** it automatically has an `id` field of type UUID with default generation

#### Scenario: BaseModel provides timestamps
- **WHEN** an entity inherits from BaseModel
- **THEN** it automatically has `created_at` and `updated_at` timestamp fields that are automatically managed

### Requirement: Soft delete support
The system SHALL add a `deleted_at` field to models that support soft deletion (Order, OrderItem, etc.).

#### Scenario: Soft delete field exists
- **WHEN** a model uses soft delete
- **THEN** it contains a `deleted_at` field (nullable datetime) that records when the entity was deleted

#### Scenario: Queries exclude soft-deleted records by default
- **WHEN** a repository queries an entity with soft delete enabled
- **THEN** the query automatically includes `WHERE deleted_at IS NULL` filter

### Requirement: Model relationships stubs
The system SHALL define SQLAlchemy relationships between models (User ↔ Order, Order ↔ OrderItem, Product ↔ Category, etc.) without implementing business logic validation.

#### Scenario: User can access related orders
- **WHEN** a User instance is loaded
- **THEN** it has a `.orders` relationship that can be accessed to fetch associated Order instances

#### Scenario: Order can access related order items
- **WHEN** an Order instance is loaded
- **THEN** it has an `.order_items` relationship
