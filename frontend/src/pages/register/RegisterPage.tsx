import { Link } from 'react-router-dom'
import { RegisterForm } from '../../features/auth'

export const RegisterPage: React.FC = () => {
  return (
    <div className="min-h-screen bg-gradient-to-br from-primary-light to-secondary-light dark:from-gray-900 dark:to-gray-800 flex items-center justify-center">
      <div className="bg-white dark:bg-gray-800 rounded-lg shadow-lg p-8 max-w-md w-full">
        <h1 className="text-3xl font-bold text-gray-900 dark:text-white mb-6 text-center">
          Crear cuenta
        </h1>

        <RegisterForm />

        <p className="text-center text-gray-600 dark:text-gray-400 mt-4">
          ¿Ya tienes cuenta?{' '}
          <Link to="/login" className="text-primary hover:text-primary-dark font-semibold">
            Inicia sesión aquí
          </Link>
        </p>
      </div>
    </div>
  )
}
