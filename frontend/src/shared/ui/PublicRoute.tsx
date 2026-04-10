import { Navigate } from 'react-router-dom'
import { authStore } from '../stores'

interface PublicRouteProps {
  children: React.ReactNode
}

/**
 * Public route guard component
 * Redirects authenticated users away from /login and /register
 */
export const PublicRoute: React.FC<PublicRouteProps> = ({ children }) => {
  const { isAuthenticated } = authStore()

  if (isAuthenticated) {
    return <Navigate to="/" replace />
  }

  return <>{children}</>
}
