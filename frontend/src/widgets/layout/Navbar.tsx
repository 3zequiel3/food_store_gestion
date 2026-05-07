import { useState } from 'react'
import { Link, useNavigate } from 'react-router-dom'
import {
  useAuthStore,
  selectIsAuthenticated,
  selectUsuario,
  selectHasRol,
  selectRefreshToken,
  useUIStore,
  selectTheme,
} from '../../shared/stores'
import { logout as authLogout } from '../../features/auth'

interface NavItem {
  label: string
  to: string
}

function useNavItems(): NavItem[] {
  const isAuthenticated = useAuthStore(selectIsAuthenticated)
  const isAdmin = useAuthStore(selectHasRol('ADMIN'))
  const isStock = useAuthStore(selectHasRol('STOCK'))
  const isPedidos = useAuthStore(selectHasRol('PEDIDOS'))
  const isClient = useAuthStore(selectHasRol('CLIENT'))

  if (!isAuthenticated) {
    return [{ label: 'Catálogo', to: '/products' }]
  }

  const items: NavItem[] = []

  if (isClient || isAdmin) {
    items.push(
      { label: 'Catálogo', to: '/products' },
      { label: 'Mi Carrito', to: '/cart' },
      { label: 'Mis Pedidos', to: '/orders' },
      { label: 'Mi Perfil', to: '/profile' },
      { label: 'Mis Direcciones', to: '/addresses' },
    )
  }

  if (isStock || isAdmin) {
    items.push(
      { label: 'Productos', to: '/admin/products' },
      { label: 'Categorías', to: '/admin/categories' },
      { label: 'Ingredientes', to: '/admin/ingredients' },
    )
  }

  if (isPedidos || isAdmin) {
    items.push({ label: 'Panel de Pedidos', to: '/admin/orders' })
  }

  if (isAdmin) {
    items.push(
      { label: 'Usuarios', to: '/admin/users' },
      { label: 'Métricas', to: '/admin/metrics' },
    )
  }

  return items
}

export const Navbar: React.FC = () => {
  const navigate = useNavigate()
  const [mobileOpen, setMobileOpen] = useState(false)

  const isAuthenticated = useAuthStore(selectIsAuthenticated)
  const usuario = useAuthStore(selectUsuario)
  const refreshToken = useAuthStore(selectRefreshToken)
  const theme = useUIStore(selectTheme)
  const navItems = useNavItems()

  const toggleTheme = () => {
    useUIStore.getState().setTheme(theme === 'dark' ? 'light' : 'dark')
  }

  const handleLogout = () => {
    authLogout(refreshToken ?? '').finally(() => {
      useAuthStore.getState().logout()
      navigate('/')
    })
  }

  return (
    <nav className="bg-white dark:bg-gray-800 border-b border-gray-200 dark:border-gray-700 sticky top-0 z-50">
      <div className="max-w-6xl mx-auto px-4 py-4 flex items-center justify-between">
        {/* Logo */}
        <Link to="/" className="flex items-center space-x-2 shrink-0">
          <div className="w-8 h-8 bg-primary rounded-lg flex items-center justify-center">
            <span className="text-white font-bold text-sm">FS</span>
          </div>
          <span className="text-xl font-bold text-gray-900 dark:text-white">Food Store</span>
        </Link>

        {/* Desktop nav links */}
        <div className="hidden md:flex items-center gap-6 overflow-x-auto">
          {navItems.map((item) => (
            <Link
              key={item.to}
              to={item.to}
              className="text-gray-700 dark:text-gray-300 hover:text-primary transition-colors whitespace-nowrap text-sm"
            >
              {item.label}
            </Link>
          ))}
        </div>

        {/* Actions */}
        <div className="flex items-center gap-3">
          {/* Theme toggle */}
          <button
            onClick={toggleTheme}
            className="p-2 rounded-lg hover:bg-gray-100 dark:hover:bg-gray-700 transition-colors"
            title={theme === 'dark' ? 'Modo claro' : 'Modo oscuro'}
          >
            {theme === 'dark' ? '☀️' : '🌙'}
          </button>

          {/* Mobile menu toggle */}
          <button
            className="md:hidden p-2 rounded-lg hover:bg-gray-100 dark:hover:bg-gray-700 transition-colors"
            onClick={() => setMobileOpen((v) => !v)}
            aria-label="Menú"
          >
            <span className="text-gray-700 dark:text-gray-300 text-xl">{mobileOpen ? '✕' : '☰'}</span>
          </button>

          {/* Auth section */}
          {isAuthenticated ? (
            <div className="hidden md:flex items-center gap-3">
              <span className="text-sm text-gray-700 dark:text-gray-300">{usuario?.nombre}</span>
              <button
                onClick={handleLogout}
                className="px-4 py-2 bg-error text-white rounded-lg hover:bg-error-dark transition-colors text-sm font-medium"
              >
                Salir
              </button>
            </div>
          ) : (
            <div className="hidden md:flex items-center gap-2">
              <Link
                to="/login"
                className="px-4 py-2 text-primary hover:text-primary-dark transition-colors font-medium text-sm"
              >
                Iniciar sesión
              </Link>
              <Link
                to="/register"
                className="px-4 py-2 bg-primary text-white rounded-lg hover:bg-primary-dark transition-colors font-medium text-sm"
              >
                Registrarse
              </Link>
            </div>
          )}
        </div>
      </div>

      {/* Mobile menu */}
      {mobileOpen && (
        <div className="md:hidden border-t border-gray-200 dark:border-gray-700 bg-white dark:bg-gray-800 px-4 py-3 flex flex-col gap-2">
          {navItems.map((item) => (
            <Link
              key={item.to}
              to={item.to}
              onClick={() => setMobileOpen(false)}
              className="py-2 text-gray-700 dark:text-gray-300 hover:text-primary transition-colors text-sm"
            >
              {item.label}
            </Link>
          ))}
          <div className="border-t border-gray-200 dark:border-gray-700 pt-2 mt-1">
            {isAuthenticated ? (
              <>
                <p className="text-sm text-gray-500 dark:text-gray-400 mb-2">{usuario?.nombre}</p>
                <button
                  onClick={() => { setMobileOpen(false); handleLogout() }}
                  className="w-full text-left py-2 text-error text-sm font-medium"
                >
                  Salir
                </button>
              </>
            ) : (
              <div className="flex flex-col gap-2">
                <Link to="/login" onClick={() => setMobileOpen(false)} className="py-2 text-primary text-sm font-medium">
                  Iniciar sesión
                </Link>
                <Link to="/register" onClick={() => setMobileOpen(false)} className="py-2 text-primary text-sm font-medium">
                  Registrarse
                </Link>
              </div>
            )}
          </div>
        </div>
      )}
    </nav>
  )
}
