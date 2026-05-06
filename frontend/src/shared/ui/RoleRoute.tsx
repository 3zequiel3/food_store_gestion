import { Navigate } from 'react-router-dom'
import { useAuthStore, selectUsuario, type RolCode } from '../stores'

interface RoleRouteProps {
  children: React.ReactNode
  /** Roles that are allowed to access this route. */
  allowedRoles: RolCode[]
}

/**
 * Role-based route guard component.
 * Restricts access based on the authenticated user's roles.
 * Shows a redirect to /forbidden if the user does not have any of the required roles.
 */
export const RoleRoute: React.FC<RoleRouteProps> = ({ children, allowedRoles }) => {
  const usuario = useAuthStore(selectUsuario)

  const hasRole = usuario?.roles.some((r) => allowedRoles.includes(r.codigo)) ?? false

  if (!hasRole) {
    return <Navigate to="/forbidden" replace />
  }

  return <>{children}</>
}
