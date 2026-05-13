import axios from 'axios';
import type { AxiosInstance, InternalAxiosRequestConfig } from 'axios';
import { useAuthStore } from '../../features/auth/stores/authStore';
import { ENDPOINTS } from '../../lib/constants/endpoints';

/**
 * D1 — Single-flight refresh: variable de módulo compartida entre todos los
 * interceptors de la misma instancia. Mientras esté activa, los 401 concurrentes
 * esperan la misma promesa en vez de disparar refreshes paralelos.
 *
 * R2: Evita el refresh stampede (cuando catálogo + pedidos cargan en paralelo
 * y ambos reciben 401 al mismo tiempo).
 */
let refreshPromise: Promise<string> | null = null;

/**
 * Registra el interceptor de autenticación en la instancia axios.
 * Se llama desde client.ts antes de exportar apiClient (D7 — wiring eager).
 */
export function applyAuthInterceptor(client: AxiosInstance): void {
  // ─── Request interceptor: inyectar Authorization header ─────────────────
  client.interceptors.request.use(
    (config: InternalAxiosRequestConfig) => {
      const token = useAuthStore.getState().getAccessToken();
      if (token) {
        config.headers.Authorization = `Bearer ${token}`;
      }
      return config;
    },
    (error) => Promise.reject(error),
  );

  // ─── Response interceptor: manejo de 401 con single-flight refresh ──────
  client.interceptors.response.use(
    // Respuestas 2xx pasan sin modificar
    (response) => response,
    async (error) => {
      const originalRequest = error.config as InternalAxiosRequestConfig & {
        _retry?: boolean;
      };

      const status = error.response?.status;

      // Solo manejar 401 que no sean del endpoint de refresh (evitar loop infinito)
      const isRefreshEndpoint =
        originalRequest.url?.includes(ENDPOINTS.auth.refresh);

      if (status !== 401 || originalRequest._retry || isRefreshEndpoint) {
        return Promise.reject(error);
      }

      // Marcar como reintento para no volver a entrar si el retry da 401
      originalRequest._retry = true;

      try {
        // Si no hay refresh en vuelo, iniciarlo
        if (!refreshPromise) {
          const refreshToken = useAuthStore.getState().getRefreshToken();

          if (!refreshToken) {
            // Sin refresh token → logout directo
            handleLogout();
            return Promise.reject(error);
          }

          refreshPromise = performRefresh(client, refreshToken).finally(() => {
            refreshPromise = null;
          });
        }

        // Todos los 401 concurrentes esperan la misma promesa
        const newAccessToken = await refreshPromise;

        // Retry con el nuevo token
        originalRequest.headers.Authorization = `Bearer ${newAccessToken}`;
        return client(originalRequest);
      } catch {
        // El refresh falló — limpiar sesión y redirigir
        handleLogout();
        return Promise.reject(error);
      }
    },
  );
}

/**
 * Hace el POST a /auth/refresh y actualiza el store.
 * Retorna el nuevo access_token para que los reintentos lo usen.
 */
async function performRefresh(
  client: AxiosInstance,
  refreshToken: string,
): Promise<string> {
  // Usamos axios directamente (sin interceptors) para evitar loops
  const response = await axios.post(
    `/api/v1${ENDPOINTS.auth.refresh}`,
    { refresh_token: refreshToken },
    { headers: { 'Content-Type': 'application/json' } },
  );

  const { access_token, refresh_token, user } = response.data;

  useAuthStore.getState().setSession({
    accessToken: access_token,
    refreshToken: refresh_token,
    user,
  });

  return access_token;
}

/** Limpia la sesión y redirige a /login */
function handleLogout(): void {
  useAuthStore.getState().clearSession();
  // Usamos assign (hard redirect) para resetear el estado React completo
  window.location.assign('/login');
}
