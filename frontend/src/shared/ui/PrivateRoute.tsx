import { Navigate, useLocation } from 'react-router-dom'
import { useAuthStore, selectIsAuthenticated } from '../stores'

interface PrivateRouteProps {
  children: React.ReactNode
}

/**
 * Private route guard component.
 * Redirects unauthenticated users to /login.
 * Preserves the original location for post-login redirect.
 */
export const PrivateRoute: React.FC<PrivateRouteProps> = ({ children }) => {
  const isAuthenticated = useAuthStore(selectIsAuthenticated)
  const location = useLocation()

  if (!isAuthenticated) {
    return <Navigate to="/login" state={{ from: location }} replace />
  }

  return <>{children}</>
}
