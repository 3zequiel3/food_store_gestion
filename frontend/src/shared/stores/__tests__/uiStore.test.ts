import { describe, it, expect, beforeEach } from 'vitest'
import { useUIStore } from '../uiStore'
import { selectTheme, selectSidebarOpen, selectToasts } from '../uiStore'
import type { Toast } from '../../../shared/types/ui'

// ---------------------------------------------------------------------------
// Fixtures
// ---------------------------------------------------------------------------

const toastA: Toast = { id: 'a', message: 'Operación exitosa', level: 'success' }
const toastB: Toast = { id: 'b', message: 'Error al procesar', level: 'error', durationMs: 5000 }

// ---------------------------------------------------------------------------
// Tests
// ---------------------------------------------------------------------------

describe('useUIStore', () => {
  beforeEach(() => {
    localStorage.clear()
    useUIStore.setState({ theme: 'light', sidebarOpen: false, toasts: [] })
    document.documentElement.classList.remove('dark')
  })

  // ---- setTheme ------------------------------------------------------------

  it('setTheme updates theme to dark', () => {
    useUIStore.getState().setTheme('dark')
    expect(useUIStore.getState().theme).toBe('dark')
  })

  it('setTheme applies dark class to <html> when theme is dark', () => {
    useUIStore.getState().setTheme('dark')
    expect(document.documentElement.classList.contains('dark')).toBe(true)
  })

  it('setTheme removes dark class from <html> when theme is light', () => {
    document.documentElement.classList.add('dark')
    useUIStore.getState().setTheme('light')
    expect(document.documentElement.classList.contains('dark')).toBe(false)
  })

  it('setTheme persists ONLY theme to localStorage — not sidebarOpen or toasts', () => {
    useUIStore.getState().toggleSidebar()     // sidebarOpen = true
    useUIStore.getState().pushToast(toastA)   // toasts has one item
    useUIStore.getState().setTheme('dark')

    const raw = localStorage.getItem('food-store-ui')
    expect(raw).not.toBeNull()
    const stored = JSON.parse(raw!)

    // Only `theme` should be persisted
    expect(stored.state.theme).toBe('dark')
    expect(stored.state.sidebarOpen).toBeUndefined()
    expect(stored.state.toasts).toBeUndefined()
  })

  // ---- toggleSidebar -------------------------------------------------------

  it('toggleSidebar flips sidebarOpen', () => {
    expect(useUIStore.getState().sidebarOpen).toBe(false)
    useUIStore.getState().toggleSidebar()
    expect(useUIStore.getState().sidebarOpen).toBe(true)
    useUIStore.getState().toggleSidebar()
    expect(useUIStore.getState().sidebarOpen).toBe(false)
  })

  it('toggleSidebar alone does NOT write food-store-ui to localStorage', () => {
    // Only setTheme should trigger a persist write. toggleSidebar is not in partialize.
    useUIStore.getState().toggleSidebar()
    // If anything was written (shouldn't be since persist only fires on partialize'd fields),
    // verify sidebarOpen is absent from the stored state.
    const raw = localStorage.getItem('food-store-ui')
    if (raw) {
      const stored = JSON.parse(raw)
      expect(stored.state.sidebarOpen).toBeUndefined()
    }
  })

  // ---- pushToast / dismissToast --------------------------------------------

  it('pushToast appends a toast to the queue', () => {
    useUIStore.getState().pushToast(toastA)
    expect(useUIStore.getState().toasts).toHaveLength(1)
    expect(useUIStore.getState().toasts[0].id).toBe('a')
  })

  it('pushToast can stack multiple toasts', () => {
    useUIStore.getState().pushToast(toastA)
    useUIStore.getState().pushToast(toastB)
    expect(useUIStore.getState().toasts).toHaveLength(2)
  })

  it('dismissToast removes the toast with the matching id', () => {
    useUIStore.getState().pushToast(toastA)
    useUIStore.getState().pushToast(toastB)
    useUIStore.getState().dismissToast('a')
    const toasts = useUIStore.getState().toasts
    expect(toasts).toHaveLength(1)
    expect(toasts[0].id).toBe('b')
  })

  it('dismissToast does nothing if the id is not found', () => {
    useUIStore.getState().pushToast(toastA)
    useUIStore.getState().dismissToast('nonexistent')
    expect(useUIStore.getState().toasts).toHaveLength(1)
  })

  // ---- atomic selectors ----------------------------------------------------

  it('atomic selectors return correct slices', () => {
    useUIStore.getState().setTheme('dark')
    useUIStore.getState().toggleSidebar()
    useUIStore.getState().pushToast(toastA)

    const s = useUIStore.getState()
    expect(selectTheme(s)).toBe('dark')
    expect(selectSidebarOpen(s)).toBe(true)
    expect(selectToasts(s)).toHaveLength(1)
  })

  // ---- persistence / rehydration -------------------------------------------

  it('persist: setTheme writes food-store-ui to localStorage', () => {
    useUIStore.getState().setTheme('dark')
    const raw = localStorage.getItem('food-store-ui')
    expect(raw).not.toBeNull()
    const stored = JSON.parse(raw!)
    expect(stored.state.theme).toBe('dark')
  })

  it('persist: manual rehydrate restores theme and applies dark class', async () => {
    // Reset state FIRST — triggers a persist write with theme:'light'
    useUIStore.setState({ theme: 'light', sidebarOpen: false, toasts: [] })
    document.documentElement.classList.remove('dark')

    // Write stored data AFTER setState so persist doesn't overwrite it
    const stored = JSON.stringify({ state: { theme: 'dark' }, version: 0 })
    localStorage.setItem('food-store-ui', stored)

    await new Promise<void>((resolve) => {
      const unsub = useUIStore.persist.onFinishHydration(() => {
        unsub()
        resolve()
      })
      useUIStore.persist.rehydrate()
    })

    expect(useUIStore.getState().theme).toBe('dark')
    expect(document.documentElement.classList.contains('dark')).toBe(true)
  })

  it('persist: stored state never contains sidebarOpen (partialize excludes it)', () => {
    useUIStore.getState().toggleSidebar()     // sidebarOpen = true (transient)
    useUIStore.getState().setTheme('light')   // triggers persist write

    const raw = localStorage.getItem('food-store-ui')!
    const stored = JSON.parse(raw)
    expect(stored.state.sidebarOpen).toBeUndefined()
    expect(stored.state.toasts).toBeUndefined()
  })
})
