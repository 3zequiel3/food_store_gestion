import { RouterProvider, createBrowserRouter } from 'react-router-dom'
import { AppLayout } from '../widgets/layout/AppLayout'
import { PrivateRoute, PublicRoute, RoleRoute } from '../shared/ui'
import { HomePage } from '../pages/home/HomePage'
import { LoginPage } from '../pages/login/LoginPage'
import { RegisterPage } from '../pages/register/RegisterPage'
import { NotFound } from '../pages/errors/NotFound'
import { Forbidden } from '../pages/errors/Forbidden'

// Create router configuration
const router = createBrowserRouter([
  {
    path: '/',
    element: <AppLayout />,
    errorElement: <NotFound />,
    children: [
      {
        index: true,
        element: <HomePage />,
      },
      {
        path: 'login',
        element: (
          <PublicRoute>
            <LoginPage />
          </PublicRoute>
        ),
      },
      {
        path: 'register',
        element: (
          <PublicRoute>
            <RegisterPage />
          </PublicRoute>
        ),
      },
      {
        path: 'products',
        element: <div className="p-8">Products Page (placeholder)</div>,
      },
      {
        path: 'checkout',
        element: (
          <PrivateRoute>
            <div className="p-8">Checkout Page (placeholder)</div>
          </PrivateRoute>
        ),
      },
      {
        path: 'orders',
        element: (
          <PrivateRoute>
            <div className="p-8">Orders Page (placeholder)</div>
          </PrivateRoute>
        ),
      },
      {
        path: 'admin/products',
        element: (
          <PrivateRoute>
            <RoleRoute allowedRoles={['ADMIN']}>
              <div className="p-8">Admin Products Page (placeholder)</div>
            </RoleRoute>
          </PrivateRoute>
        ),
      },
      {
        path: 'forbidden',
        element: <Forbidden />,
      },
      {
        path: '*',
        element: <NotFound />,
      },
    ],
  },
])

/**
 * Router component
 * Provides route configuration for react-router-dom v6
 * with public/private/role-based route guards
 */
export const Router: React.FC = () => {
  return <RouterProvider router={router} />
}
