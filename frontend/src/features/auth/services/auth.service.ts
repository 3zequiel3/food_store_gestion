import { apiClient } from '../../../api/client';
import { ENDPOINTS } from '../../../lib/constants/endpoints';
import type {
  AuthSessionResponse,
  LoginCredentials,
  RegisterPayload,
  Usuario,
} from '../types/auth.types';

/** Servicio de autenticación cookie-backed. */

/** POST /auth/login — setea cookies HttpOnly y retorna usuario */
export async function login(
  credentials: LoginCredentials,
): Promise<AuthSessionResponse> {
  const response = await apiClient.post<AuthSessionResponse>(
    ENDPOINTS.auth.login,
    credentials,
  );
  return response.data;
}

/** POST /auth/register — crea cuenta, setea cookies HttpOnly y retorna usuario */
export async function register(
  payload: RegisterPayload,
): Promise<AuthSessionResponse> {
  const response = await apiClient.post<AuthSessionResponse>(
    ENDPOINTS.auth.register,
    payload,
  );
  return response.data;
}

/** POST /auth/refresh — rota cookies HttpOnly */
export async function refresh(): Promise<AuthSessionResponse> {
  const response = await apiClient.post<AuthSessionResponse>(ENDPOINTS.auth.refresh);
  return response.data;
}

/** POST /auth/logout — revoca refresh cookie y limpia cookies */
export async function logout(): Promise<void> {
  await apiClient.post(ENDPOINTS.auth.logout);
}

/** GET /auth/me — retorna el usuario autenticado por cookie */
export async function me(): Promise<Usuario> {
  const response = await apiClient.get<Usuario>(ENDPOINTS.auth.me);
  return response.data;
}

/** GET /auth/token — retorna access token en body (para WebSocket auth) */
export async function getToken(): Promise<{ access_token: string; token_type: string }> {
  const response = await apiClient.get(ENDPOINTS.auth.token);
  return response.data;
}
