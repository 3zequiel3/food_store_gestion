import { useQuery } from '@tanstack/react-query';
import { me } from '../services/auth.service';
import { useAuthStore } from '../stores/authStore';

/**
 * Hook para obtener el usuario autenticado desde el backend.
 *
 * `enabled` vinculado a `isAuthenticated()` — no dispara ningún request
 * si el usuario no está autenticado (spec: useMe disabled when unauthenticated).
 *
 * El store ya tiene el usuario en `user` post-login; este hook es para
 * refrescar datos actualizados (ej: cambio de perfil desde otro dispositivo).
 */
export function useMe() {
  const isAuthenticated = useAuthStore((s) => s.accessToken !== null);

  return useQuery({
    queryKey: ['auth', 'me'],
    queryFn: me,
    enabled: isAuthenticated,
  });
}
