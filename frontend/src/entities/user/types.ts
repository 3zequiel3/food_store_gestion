/**
 * User entity types
 */

export type Role = 'CLIENTE' | 'ADMIN'

export interface User {
  id: string
  email: string
  name: string
  role: Role
  avatar?: string
  createdAt?: string
  updatedAt?: string
}

export interface AuthState {
  user: User | null
  token: string | null
  isAuthenticated: boolean
}
