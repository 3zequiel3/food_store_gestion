import { Link } from 'react-router-dom'

export const Forbidden: React.FC = () => {
  return (
    <div className="flex flex-col items-center justify-center min-h-screen bg-gray-50 dark:bg-gray-900">
      <div className="text-center">
        <h1 className="text-6xl font-bold text-error mb-4">403</h1>
        <h2 className="text-2xl font-semibold text-gray-900 dark:text-white mb-4">
          Acceso prohibido
        </h2>
        <p className="text-gray-600 dark:text-gray-400 mb-8 max-w-md">
          No tienes permisos para acceder a esta página. Si crees que esto es un error, contacta al administrador.
        </p>
        <Link
          to="/"
          className="inline-block px-6 py-3 bg-primary text-white rounded-lg font-medium hover:bg-primary-dark transition-colors"
        >
          Volver al inicio
        </Link>
      </div>
    </div>
  )
}
