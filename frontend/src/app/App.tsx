import { Router } from './Router'

/**
 * Root App component.
 *
 * Theme management (dark class on <html>) is handled internally by
 * `useUIStore.setTheme()` and its `onRehydrateStorage` hook — no
 * explicit side-effect needed here.
 */
function App() {
  return (
    <div className="bg-white dark:bg-gray-900 text-gray-900 dark:text-white min-h-screen">
      <Router />
    </div>
  )
}

export default App
