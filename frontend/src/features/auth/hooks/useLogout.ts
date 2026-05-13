import { useMutation, useQueryClient } from '@tanstack/react-query';
import { logout } from '../services/auth.service';
import { useAuthStore } from '../stores/authStore';

/**
 * Hook de logout.
 *
 * onSettled (en vez de onSuccess) para que la limpieza ocurra
 * aunque el backend retorne error (el token ya no es válido de todas formas).
 *
 * Uso:
 *   const { mutate } = useLogout();
 *   mutate();
 */
export function useLogout() {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: logout,
    onSettled() {
      // Limpiar sesión y cache de queries sin importar el resultado del backend
      useAuthStore.getState().clearSession();
      queryClient.clear();
    },
  });
}
