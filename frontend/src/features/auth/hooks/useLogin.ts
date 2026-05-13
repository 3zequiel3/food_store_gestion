import { useMutation } from '@tanstack/react-query';
import { login } from '../services/auth.service';
import { useAuthStore } from '../stores/authStore';
import type { LoginCredentials } from '../types/auth.types';

/**
 * Hook de login. Wrappea useMutation y en onSuccess persiste la sesión.
 *
 * Uso:
 *   const { mutate, isPending, error } = useLogin();
 *   mutate({ email, password });
 */
export function useLogin() {
  return useMutation({
    mutationFn: (credentials: LoginCredentials) => login(credentials),
    onSuccess(data) {
      useAuthStore.getState().setSession({
        accessToken: data.access_token,
        refreshToken: data.refresh_token,
        user: data.user,
      });
    },
  });
}
