import { Navigate, Outlet } from 'react-router-dom';
import { useAuthStore } from '../../features/auth/stores/authStore';

interface RoleGuardProps {
  /** Códigos de rol permitidos. El usuario debe tener AL MENOS uno de ellos. */
  roles: string[];
}

/**
 * Guard de rol para rutas con acceso restringido.
 * D9 — Nested route guard: si el usuario no tiene ninguno de los roles requeridos,
 * redirige a /403 (Forbidden). PrivateRoute garantiza que el usuario esté autenticado
 * antes de llegar acá, por lo que no se necesita chequeo de auth adicional.
 */
export function RoleGuard({ roles }: RoleGuardProps) {
  // Subscribimos directo al `user` (objeto estable mientras no cambie la sesión).
  // NO usamos `s.hasRole.bind(s)` como selector porque `bind()` crea una función
  // nueva en cada llamada y React 19 + useSyncExternalStore lo lee como
  // snapshot cambiado → infinite re-render loop.
  const user = useAuthStore((s) => s.user);

  const allowed =
    user != null && user.roles.some((codigo) => roles.includes(codigo));

  if (!allowed) {
    return <Navigate to="/403" replace />;
  }

  return <Outlet />;
}
