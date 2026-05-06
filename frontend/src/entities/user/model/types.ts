/**
 * User domain types.
 *
 * Naming convention:
 * - `Usuario` and `Rol` mirror backend domain entities
 *   (backend/features/users/models.py::Usuario, backend/features/catalog/models.py::Rol)
 *   per canonical spec Integrador.txt:256.
 * - `RolCode` is a TypeScript union of valid role `codigo` values from the backend catalog.
 * - `AuthTokens` stays in English — it is a technical DTO, not a DB entity.
 */

export type RolCode = 'ADMIN' | 'STOCK' | 'PEDIDOS' | 'CLIENT'

export interface Rol {
  id: number
  codigo: RolCode
}

export interface Usuario {
  id: number
  email: string
  nombre: string
  roles: Rol[]
}

export interface AuthTokens {
  accessToken: string
  refreshToken: string
}
