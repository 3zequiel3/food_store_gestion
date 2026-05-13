/**
 * Tipos del dominio auth.
 * Matchean el schema del backend (backend/features/auth/schemas.py).
 * Campos en snake_case para espejear el contrato JSON del backend.
 */

export interface Usuario {
  id: number;
  email: string;
  nombre: string;
  apellido: string;
  /** Códigos de rol (ADMIN, STOCK, PEDIDOS, CLIENT). El backend devuelve strings, no objetos. */
  roles: string[];
}

export interface LoginCredentials {
  email: string;
  password: string;
}

export interface RegisterPayload {
  nombre: string;
  apellido: string;
  email: string;
  password: string;
}

export interface PasswordChangePayload {
  current_password: string;
  new_password: string;
}

export interface TokenPair {
  access_token: string;
  refresh_token: string;
}

/** Response completo de /auth/login — incluye tokens + usuario */
export interface LoginResponse extends TokenPair {
  user: Usuario;
}

/** Payload de sesión que se persiste en authStore */
export interface SessionPayload {
  accessToken: string;
  refreshToken: string;
  user: Usuario;
}
