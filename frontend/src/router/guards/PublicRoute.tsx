import { Navigate, Outlet } from 'react-router-dom';
import { useAuthStore } from '../../features/auth/stores/authStore';

/**
 * Guard para rutas públicas (login, register).
 * D9 — Nested route guard: si el usuario YA está autenticado, lo redirige a `/`.
 * Las rutas hijas se renderizan dentro del <Outlet /> cuando no hay auth.
 */
export function PublicRoute() {
  const isAuthenticated = useAuthStore((s) => s.accessToken !== null);

  if (isAuthenticated) {
    return <Navigate to="/" replace />;
  }

  return <Outlet />;
}
