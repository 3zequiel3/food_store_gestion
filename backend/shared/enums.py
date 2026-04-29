"""
Enumeration definitions for domain entities.

NOTE: Role, EstadoPedido, and FormaPago were removed in the database-schema-seed
change. They are now modeled as catalog tables with FK references:
  - roles       (backend/features/catalog/models.py)
  - order_states (backend/features/catalog/models.py)
  - payment_methods (backend/features/catalog/models.py)

Add new Python enums here only for cases NOT covered by the ERD catalog tables.
"""
