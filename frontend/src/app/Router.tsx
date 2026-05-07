import { RouterProvider, createBrowserRouter } from 'react-router-dom'
import { AppLayout } from '../widgets/layout/AppLayout'
import { PrivateRoute, PublicRoute, RoleRoute } from '../shared/ui'
import { HomePage } from '../pages/home/HomePage'
import { LoginPage } from '../pages/login/LoginPage'
import { RegisterPage } from '../pages/register/RegisterPage'
import { NotFound } from '../pages/errors/NotFound'
import { Forbidden } from '../pages/errors/Forbidden'

const Placeholder = ({ label }: { label: string }) => (
  <div className="p-8 text-center text-gray-500 dark:text-gray-400">{label} — Próximamente</div>
)

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

      // ── Public auth routes (redirect if already authenticated) ──
      {
        path: 'login',
        element: <PublicRoute><LoginPage /></PublicRoute>,
      },
      {
        path: 'register',
        element: <PublicRoute><RegisterPage /></PublicRoute>,
      },

      // ── Public catalog ──
      {
        path: 'products',
        element: <Placeholder label="Catálogo de productos" />,
      },

      // ── Private — all authenticated users ──
      {
        path: 'cart',
        element: <PrivateRoute><Placeholder label="Mi Carrito" /></PrivateRoute>,
      },
      {
        path: 'checkout',
        element: <PrivateRoute><Placeholder label="Checkout" /></PrivateRoute>,
      },
      {
        path: 'profile',
        element: <PrivateRoute><Placeholder label="Mi Perfil" /></PrivateRoute>,
      },

      // ── Private — CLIENT only ──
      {
        path: 'orders',
        element: (
          <PrivateRoute>
            <RoleRoute allowedRoles={['CLIENT']}>
              <Placeholder label="Mis Pedidos" />
            </RoleRoute>
          </PrivateRoute>
        ),
      },
      {
        path: 'addresses',
        element: (
          <PrivateRoute>
            <RoleRoute allowedRoles={['CLIENT']}>
              <Placeholder label="Mis Direcciones" />
            </RoleRoute>
          </PrivateRoute>
        ),
      },

      // ── Private — ADMIN + STOCK ──
      {
        path: 'admin/products',
        element: (
          <PrivateRoute>
            <RoleRoute allowedRoles={['ADMIN', 'STOCK']}>
              <Placeholder label="Gestión de Productos" />
            </RoleRoute>
          </PrivateRoute>
        ),
      },
      {
        path: 'admin/categories',
        element: (
          <PrivateRoute>
            <RoleRoute allowedRoles={['ADMIN', 'STOCK']}>
              <Placeholder label="Gestión de Categorías" />
            </RoleRoute>
          </PrivateRoute>
        ),
      },
      {
        path: 'admin/ingredients',
        element: (
          <PrivateRoute>
            <RoleRoute allowedRoles={['ADMIN', 'STOCK']}>
              <Placeholder label="Gestión de Ingredientes" />
            </RoleRoute>
          </PrivateRoute>
        ),
      },

      // ── Private — ADMIN + PEDIDOS ──
      {
        path: 'admin/orders',
        element: (
          <PrivateRoute>
            <RoleRoute allowedRoles={['ADMIN', 'PEDIDOS']}>
              <Placeholder label="Panel de Pedidos" />
            </RoleRoute>
          </PrivateRoute>
        ),
      },

      // ── Private — ADMIN only ──
      {
        path: 'admin/users',
        element: (
          <PrivateRoute>
            <RoleRoute allowedRoles={['ADMIN']}>
              <Placeholder label="Gestión de Usuarios" />
            </RoleRoute>
          </PrivateRoute>
        ),
      },
      {
        path: 'admin/metrics',
        element: (
          <PrivateRoute>
            <RoleRoute allowedRoles={['ADMIN']}>
              <Placeholder label="Métricas y Dashboard" />
            </RoleRoute>
          </PrivateRoute>
        ),
      },

      // ── Error pages ──
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

export const Router: React.FC = () => {
  return <RouterProvider router={router} />
}
