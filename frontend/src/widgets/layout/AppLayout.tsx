import { Outlet } from 'react-router-dom'
import { Navbar } from './Navbar'

/**
 * AppLayout component
 * Provides the main layout structure with navbar and content area
 */
export const AppLayout: React.FC = () => {
  return (
    <div className="flex flex-col min-h-screen bg-white dark:bg-gray-900">
      <Navbar />
      <main className="flex-1">
        <Outlet />
      </main>
      <footer className="bg-gray-100 dark:bg-gray-800 border-t border-gray-200 dark:border-gray-700 py-8">
        <div className="max-w-6xl mx-auto px-4 text-center text-gray-600 dark:text-gray-400">
          <p>&copy; 2026 Food Store. Todos los derechos reservados.</p>
        </div>
      </footer>
    </div>
  )
}
