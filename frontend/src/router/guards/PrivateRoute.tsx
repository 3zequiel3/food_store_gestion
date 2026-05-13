import { Navigate, Outlet, useLocation } from 'react-router-dom';
import { useAuthStore } from '../../features/auth/stores/authStore';

/**
 * Guard para rutas privadas (requieren autenticación).
 * D9 — Nested route guard: si el usuario NO está autenticado, redirige a /login
 * preservando la URL original en `location.state.from` para post-login redirect.
 */
export function PrivateRoute() {
  const isAuthenticated = useAuthStore((s) => s.user !== null);
  const location = useLocation();

  if (!isAuthenticated) {
    return (
      <Navigate
        to="/login"
        replace
        state={{ from: location.pathname }}
      />
    );
  }

  return <Outlet />;
}
