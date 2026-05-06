import { Link } from 'react-router-dom'
import {
  useAuthStore,
  selectIsAuthenticated,
  selectUsuario,
  selectHasRol,
  useUIStore,
  selectTheme,
} from '../../shared/stores'

/**
 * Navbar component.
 * Displays logo, navigation links, dark mode toggle, and auth buttons.
 */
export const Navbar: React.FC = () => {
  const isAuthenticated = useAuthStore(selectIsAuthenticated)
  const usuario = useAuthStore(selectUsuario)
  const isAdmin = useAuthStore(selectHasRol('ADMIN'))
  const theme = useUIStore(selectTheme)

  const toggleTheme = () => {
    useUIStore.getState().setTheme(theme === 'dark' ? 'light' : 'dark')
  }

  return (
    <nav className="bg-white dark:bg-gray-800 border-b border-gray-200 dark:border-gray-700 sticky top-0 z-50">
      <div className="max-w-6xl mx-auto px-4 py-4 flex items-center justify-between">
        {/* Logo */}
        <Link to="/" className="flex items-center space-x-2">
          <div className="w-8 h-8 bg-primary rounded-lg flex items-center justify-center">
            <span className="text-white font-bold">FS</span>
          </div>
          <span className="text-xl font-bold text-gray-900 dark:text-white">Food Store</span>
        </Link>

        {/* Navigation Links */}
        <div className="hidden md:flex items-center space-x-8">
          <Link
            to="/products"
            className="text-gray-700 dark:text-gray-300 hover:text-primary transition-colors"
          >
            Productos
          </Link>
          {isAuthenticated && isAdmin && (
            <Link
              to="/admin/products"
              className="text-gray-700 dark:text-gray-300 hover:text-primary transition-colors"
            >
              Admin
            </Link>
          )}
        </div>

        {/* Actions */}
        <div className="flex items-center space-x-4">
          {/* Dark Mode Toggle */}
          <button
            onClick={toggleTheme}
            className="p-2 rounded-lg hover:bg-gray-100 dark:hover:bg-gray-700 transition-colors"
            title={theme === 'dark' ? 'Modo claro' : 'Modo oscuro'}
          >
            {theme === 'dark' ? '☀️' : '🌙'}
          </button>

          {/* Cart Icon (placeholder) */}
          {isAuthenticated && (
            <Link
              to="/orders"
              className="p-2 hover:bg-gray-100 dark:hover:bg-gray-700 rounded-lg transition-colors"
              title="Mis pedidos"
            >
              📦
            </Link>
          )}

          {/* Auth Buttons */}
          {isAuthenticated ? (
            <div className="flex items-center space-x-4">
              <span className="text-sm text-gray-700 dark:text-gray-300">
                {usuario?.nombre}
              </span>
              <button
                onClick={() => useAuthStore.getState().logout()}
                className="px-4 py-2 bg-error text-white rounded-lg hover:bg-error-dark transition-colors text-sm font-medium"
              >
                Salir
              </button>
            </div>
          ) : (
            <div className="flex items-center space-x-2">
              <Link
                to="/login"
                className="px-4 py-2 text-primary hover:text-primary-dark transition-colors font-medium"
              >
                Iniciar sesión
              </Link>
              <Link
                to="/register"
                className="px-4 py-2 bg-primary text-white rounded-lg hover:bg-primary-dark transition-colors font-medium"
              >
                Registrarse
              </Link>
            </div>
          )}
        </div>
      </div>
    </nav>
  )
}
