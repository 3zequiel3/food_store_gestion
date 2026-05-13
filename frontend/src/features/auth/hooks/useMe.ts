import { useQuery } from '@tanstack/react-query';
import { me } from '../services/auth.service';
import { useAuthStore } from '../stores/authStore';

/**
 * Hook para obtener el usuario autenticado desde el backend.
 *
 * `enabled` vinculado a sesión local; la request se autentica por cookie HttpOnly.
 * El store ya tiene el usuario post-login; este hook refresca datos actualizados.
 */
export function useMe() {
  const isAuthenticated = useAuthStore((s) => s.user !== null);

  return useQuery({
    queryKey: ['auth', 'me'],
    queryFn: me,
    enabled: isAuthenticated,
  });
}
