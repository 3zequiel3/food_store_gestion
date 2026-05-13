import { apiClient } from '../../../api/client';
import { ENDPOINTS } from '../../../lib/constants/endpoints';
import type {
  LoginCredentials,
  LoginResponse,
  RegisterPayload,
  Usuario,
} from '../types/auth.types';

/**
 * Servicio de autenticación.
 *
 * Todas las funciones importan paths desde ENDPOINTS — nunca hardcodeados.
 * Usan apiClient que ya tiene los interceptors cargados (auth + error).
 */

/** POST /auth/login — retorna tokens + usuario */
export async function login(credentials: LoginCredentials): Promise<LoginResponse> {
  const response = await apiClient.post<LoginResponse>(
    ENDPOINTS.auth.login,
    credentials,
  );
  return response.data;
}

/** POST /auth/register — crea cuenta y retorna tokens + usuario */
export async function register(payload: RegisterPayload): Promise<LoginResponse> {
  const response = await apiClient.post<LoginResponse>(
    ENDPOINTS.auth.register,
    payload,
  );
  return response.data;
}

/**
 * POST /auth/refresh — rota el refresh token.
 * Nota: el interceptor llama a axios directo para este endpoint,
 * no a apiClient, para evitar loops. Esta función está disponible
 * para uso explícito en código de negocio si hiciera falta.
 */
export async function refresh(refreshToken: string): Promise<LoginResponse> {
  const response = await apiClient.post<LoginResponse>(ENDPOINTS.auth.refresh, {
    refresh_token: refreshToken,
  });
  return response.data;
}

/** POST /auth/logout — invalida el refresh token en el backend */
export async function logout(): Promise<void> {
  await apiClient.post(ENDPOINTS.auth.logout);
}

/** GET /auth/me — retorna el usuario autenticado */
export async function me(): Promise<Usuario> {
  const response = await apiClient.get<Usuario>(ENDPOINTS.auth.me);
  return response.data;
}
