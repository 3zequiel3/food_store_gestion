import { Navigate } from 'react-router-dom'
import { authStore, type User } from '../stores'

interface RoleRouteProps {
  children: React.ReactNode
  allowedRoles: User['role'][]
}

/**
 * Role-based route guard component
 * Restricts access based on user role
 * Shows 403 Forbidden page if unauthorized
 */
export const RoleRoute: React.FC<RoleRouteProps> = ({ children, allowedRoles }) => {
  const { user } = authStore()

  if (!user || !allowedRoles.includes(user.role)) {
    return <Navigate to="/forbidden" replace />
  }

  return <>{children}</>
}
