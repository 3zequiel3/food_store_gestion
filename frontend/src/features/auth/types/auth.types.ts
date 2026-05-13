/**
 * Tipos del dominio auth.
 * Tokens are transported via HttpOnly cookies and are not exposed to JS.
 */

export interface Usuario {
  id: number;
  email: string;
  nombre: string;
  apellido: string;
  /** Códigos de rol (ADMIN, STOCK, PEDIDOS, CLIENT). */
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

/** Response público de auth: no expone access/refresh token. */
export interface AuthSessionResponse {
  user: Usuario;
  expires_in: number;
  token_type: 'cookie';
}

/** Payload de sesión que se mantiene en authStore. */
export interface SessionPayload {
  user: Usuario;
}
