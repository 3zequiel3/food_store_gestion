"""
Admin Users feature module.

Exposes endpoints for administrators to manage user accounts:
- Paginated listing with search and role filters
- Personal data update
- Role assignment (atomic, with refresh token revocation)
- Account activation / deactivation (with refresh token revocation)

All endpoints require the ADMIN role.
Prefix: /api/v1/admin/usuarios
"""
