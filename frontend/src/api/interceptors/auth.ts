import axios from 'axios';
import type { AxiosInstance, InternalAxiosRequestConfig } from 'axios';
import { useAuthStore } from '../../features/auth/stores/authStore';
import { ENDPOINTS } from '../../lib/constants/endpoints';

let refreshPromise: Promise<void> | null = null;

/** Registra refresh automático para sesiones cookie-backed. */
export function applyAuthInterceptor(client: AxiosInstance): void {
  client.interceptors.response.use(
    (response) => response,
    async (error) => {
      const originalRequest = error.config as InternalAxiosRequestConfig & {
        _retry?: boolean;
      };

      const status = error.response?.status;
      const isRefreshEndpoint = originalRequest.url?.includes(ENDPOINTS.auth.refresh);

      if (status !== 401 || originalRequest._retry || isRefreshEndpoint) {
        return Promise.reject(error);
      }

      originalRequest._retry = true;

      try {
        if (!refreshPromise) {
          refreshPromise = performRefresh().finally(() => {
            refreshPromise = null;
          });
        }

        await refreshPromise;
        return client(originalRequest);
      } catch {
        handleLogout();
        return Promise.reject(error);
      }
    },
  );
}

async function performRefresh(): Promise<void> {
  const response = await axios.post(
    `/api/v1${ENDPOINTS.auth.refresh}`,
    undefined,
    {
      withCredentials: true,
      headers: { 'Content-Type': 'application/json' },
    },
  );

  const { user } = response.data;
  useAuthStore.getState().setSession({ user });
}

function handleLogout(): void {
  useAuthStore.getState().clearSession();
  window.location.assign('/login');
}
