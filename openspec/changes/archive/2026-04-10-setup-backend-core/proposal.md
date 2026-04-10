## Why

The Food Store backend requires a solid foundation with proper architecture patterns, dependency management, and configuration. Currently, there is no backend scaffolding. This change establishes the feature-first modular architecture, FastAPI setup, and essential infrastructure that all downstream services (auth, products, orders, payments) depend on.

## What Changes

- Create backend project structure following feature-first architecture (each feature in its own module with router → service → repository layers)
- Install and configure FastAPI, Uvicorn, Pydantic v2, SQLAlchemy ORM, and python-dotenv
- Set up environment configuration (.env management, dev/prod modes)
- Implement base models and domain entities (User, Product, Order, Payment foundational classes)
- Create standardized logging configuration
- Set up CORS, middleware stack, and exception handlers (foundation for RFC 7807 in next change)
- Initialize pytest and test configuration

## Capabilities

### New Capabilities
- `backend-setup`: FastAPI application initialization, feature-first module structure, dependency injection patterns, environment configuration
- `base-entities`: Domain model foundation (User, Product, Order, Payment, Role, EstadoPedido base classes without business logic)
- `logging-audit`: Standardized logging configuration for audit trails and debugging

### Modified Capabilities
<!-- No existing capabilities are modified in this change -->

## Impact

- **Code**: Creates `/backend/` directory structure with feature modules, main.py, requirements.txt
- **APIs**: Foundation for all future FastAPI routers
- **Dependencies**: FastAPI, SQLAlchemy, Pydantic v2, Uvicorn, python-dotenv, pytest
- **Systems**: Establishes the backend development environment and build pipeline
- **Team**: Defines naming conventions and project structure for all developers
