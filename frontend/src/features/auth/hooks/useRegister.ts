import { useMutation } from '@tanstack/react-query';
import { register } from '../services/auth.service';
import { useAuthStore } from '../stores/authStore';
import type { RegisterPayload } from '../types/auth.types';

/**
 * Hook de registro. En onSuccess persiste la sesión (login automático post-registro).
 *
 * Uso:
 *   const { mutate, isPending, error } = useRegister();
 *   mutate({ nombre, apellido, email, password });
 */
export function useRegister() {
  return useMutation({
    mutationFn: (payload: RegisterPayload) => register(payload),
    onSuccess(data) {
      useAuthStore.getState().setSession({
        accessToken: data.access_token,
        refreshToken: data.refresh_token,
        user: data.user,
      });
    },
  });
}
