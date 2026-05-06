import { create } from 'zustand'
import { persist } from 'zustand/middleware'
import type { Theme, Toast } from '../types/ui'

interface UIState {
  theme: Theme
  sidebarOpen: boolean
  toasts: Toast[]

  /** Set the color theme. Persisted. Applies `dark` class to `<html>`. */
  setTheme: (theme: Theme) => void

  /** Flip sidebar visibility. NOT persisted. */
  toggleSidebar: () => void

  /** Append a toast to the queue. */
  pushToast: (toast: Toast) => void

  /** Remove a toast by id. */
  dismissToast: (id: string) => void
}

/** Apply or remove the `dark` class on the `<html>` element. */
const applyThemeClass = (theme: Theme) => {
  if (typeof document !== 'undefined') {
    document.documentElement.classList.toggle('dark', theme === 'dark')
  }
}

export const useUIStore = create<UIState>()(
  persist(
    (set) => ({
      theme: 'light',
      sidebarOpen: false,
      toasts: [],

      setTheme: (theme) => {
        applyThemeClass(theme)
        set({ theme })
      },

      toggleSidebar: () => {
        set((state) => ({ sidebarOpen: !state.sidebarOpen }))
      },

      pushToast: (toast) => {
        set((state) => ({ toasts: [...state.toasts, toast] }))
      },

      dismissToast: (id) => {
        set((state) => ({ toasts: state.toasts.filter((t) => t.id !== id) }))
      },
    }),
    {
      name: 'food-store-ui',
      // Only persist `theme` — sidebarOpen and toasts are transient (design.md §Decisión 4).
      partialize: (state) => ({ theme: state.theme }),
      // On rehydration, re-apply the dark class so the page renders with the correct theme
      // before React hydrates. Preserves behavior from the previous stub.
      onRehydrateStorage: () => (state) => {
        if (state?.theme) {
          applyThemeClass(state.theme)
        }
      },
    }
  )
)

// ---------------------------------------------------------------------------
// Atomic selectors
// ---------------------------------------------------------------------------

export const selectTheme = (s: UIState) => s.theme
export const selectSidebarOpen = (s: UIState) => s.sidebarOpen
export const selectToasts = (s: UIState) => s.toasts
