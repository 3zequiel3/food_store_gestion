import { useEffect } from 'react'
import { Router } from './Router'
import { uiStore } from '../shared/stores'

/**
 * Root App component
 * Provides:
 * - Router configuration
 * - Theme management (dark mode class on html)
 * - Global app state subscription
 */
function App() {
  const { darkMode } = uiStore()

  useEffect(() => {
    // Apply dark mode class on mount and when darkMode changes
    if (darkMode) {
      document.documentElement.classList.add('dark')
    } else {
      document.documentElement.classList.remove('dark')
    }
  }, [darkMode])

  return (
    <div className="bg-white dark:bg-gray-900 text-gray-900 dark:text-white min-h-screen">
      <Router />
    </div>
  )
}

export default App
