import { describe, it, expect, beforeEach } from 'vitest'
import { useAuthStore } from '../authStore'
import {
  selectIsAuthenticated,
  selectAccessToken,
  selectRefreshToken,
  selectUsuario,
  selectHasRol,
} from '../authStore'
import { useCartStore } from '../cartStore'
import type { Usuario, AuthTokens } from '../../../entities/user/model'
import type { CartItem } from '../../../entities/order/model'

// ---------------------------------------------------------------------------
// Fixtures
// ---------------------------------------------------------------------------

const mockTokens: AuthTokens = {
  accessToken: 'access-token-abc',
  refreshToken: 'refresh-token-xyz',
}

const mockUsuario: Usuario = {
  id: 1,
  email: 'test@example.com',
  nombre: 'Test User',
  roles: [{ id: 4, codigo: 'CLIENT' }],
}

const adminUsuario: Usuario = {
  id: 2,
  email: 'admin@example.com',
  nombre: 'Admin User',
  roles: [
    { id: 1, codigo: 'ADMIN' },
    { id: 4, codigo: 'CLIENT' },
  ],
}

const mockCartItem: CartItem = {
  producto_id: 1,
  nombre: 'Pizza Margherita',
  precio: 100,
  cantidad: 2,
  personalizacion: { ingredientes_excluidos: [] },
}

const authInitial = {
  accessToken: null,
  refreshToken: null,
  usuario: null,
  isAuthenticated: false,
}

// ---------------------------------------------------------------------------
// Tests
// ---------------------------------------------------------------------------

describe('useAuthStore', () => {
  beforeEach(() => {
    // jsdom provides a real localStorage implementation. Clear it before each test
    // so that persist middleware doesn't rehydrate stale data from previous tests.
    localStorage.clear()

    // Reset both stores to initial state.
    // In Zustand v5, setState without replace=true does a partial merge,
    // which is sufficient here because we explicitly reset every data field.
    useAuthStore.setState(authInitial)
    useCartStore.setState({ items: [] })
  })

  // ---- login ---------------------------------------------------------------

  it('login populates all auth fields and sets isAuthenticated = true', () => {
    useAuthStore.getState().login(mockTokens, mockUsuario)

    const s = useAuthStore.getState()
    expect(s.accessToken).toBe('access-token-abc')
    expect(s.refreshToken).toBe('refresh-token-xyz')
    expect(s.usuario).toEqual(mockUsuario)
    expect(s.isAuthenticated).toBe(true)
  })

  // ---- logout --------------------------------------------------------------

  it('logout clears all auth fields', () => {
    useAuthStore.getState().login(mockTokens, mockUsuario)
    useAuthStore.getState().logout()

    const s = useAuthStore.getState()
    expect(s.accessToken).toBeNull()
    expect(s.refreshToken).toBeNull()
    expect(s.usuario).toBeNull()
    expect(s.isAuthenticated).toBe(false)
  })

  it('logout does NOT touch useCartStore (RN-CR02)', () => {
    // Populate cart first
    useCartStore.getState().addItem(
      { producto_id: mockCartItem.producto_id, nombre: mockCartItem.nombre, precio: mockCartItem.precio },
      mockCartItem.cantidad,
      mockCartItem.personalizacion
    )
    expect(useCartStore.getState().items).toHaveLength(1)

    // Login then logout
    useAuthStore.getState().login(mockTokens, mockUsuario)
    useAuthStore.getState().logout()

    // Cart must be untouched
    expect(useCartStore.getState().items).toHaveLength(1)
    expect(useCartStore.getState().items[0].producto_id).toBe(1)
  })

  // ---- updateTokens --------------------------------------------------------

  it('updateTokens rotates tokens without changing usuario or isAuthenticated', () => {
    useAuthStore.getState().login(mockTokens, mockUsuario)

    const newTokens: AuthTokens = { accessToken: 'new-access', refreshToken: 'new-refresh' }
    useAuthStore.getState().updateTokens(newTokens)

    const s = useAuthStore.getState()
    expect(s.accessToken).toBe('new-access')
    expect(s.refreshToken).toBe('new-refresh')
    expect(s.usuario).toEqual(mockUsuario)
    expect(s.isAuthenticated).toBe(true)
  })

  // ---- selectHasRol --------------------------------------------------------

  it('selectHasRol returns false when usuario is null', () => {
    expect(selectHasRol('ADMIN')(useAuthStore.getState())).toBe(false)
  })

  it('selectHasRol returns false when usuario does not have the role', () => {
    useAuthStore.getState().login(mockTokens, mockUsuario)
    expect(selectHasRol('ADMIN')(useAuthStore.getState())).toBe(false)
  })

  it('selectHasRol returns true when usuario has the role', () => {
    useAuthStore.getState().login(mockTokens, adminUsuario)
    expect(selectHasRol('ADMIN')(useAuthStore.getState())).toBe(true)
    expect(selectHasRol('CLIENT')(useAuthStore.getState())).toBe(true)
  })

  it('selectHasRol returns false for a role the usuario does not have', () => {
    useAuthStore.getState().login(mockTokens, adminUsuario)
    expect(selectHasRol('STOCK')(useAuthStore.getState())).toBe(false)
  })

  // ---- atomic selectors ----------------------------------------------------

  it('selectIsAuthenticated, selectAccessToken, selectRefreshToken, selectUsuario', () => {
    expect(selectIsAuthenticated(useAuthStore.getState())).toBe(false)
    expect(selectAccessToken(useAuthStore.getState())).toBeNull()
    expect(selectRefreshToken(useAuthStore.getState())).toBeNull()
    expect(selectUsuario(useAuthStore.getState())).toBeNull()

    useAuthStore.getState().login(mockTokens, mockUsuario)

    expect(selectIsAuthenticated(useAuthStore.getState())).toBe(true)
    expect(selectAccessToken(useAuthStore.getState())).toBe('access-token-abc')
    expect(selectRefreshToken(useAuthStore.getState())).toBe('refresh-token-xyz')
    expect(selectUsuario(useAuthStore.getState())).toEqual(mockUsuario)
  })

  // ---- persistence ---------------------------------------------------------

  it('persist: login writes to localStorage under food-store-auth', () => {
    useAuthStore.getState().login(mockTokens, mockUsuario)

    const raw = localStorage.getItem('food-store-auth')
    expect(raw).not.toBeNull()
    const stored = JSON.parse(raw!)
    expect(stored.state.accessToken).toBe('access-token-abc')
    expect(stored.state.usuario.email).toBe('test@example.com')
  })

  it('persist: partialize stores only the expected fields', () => {
    useAuthStore.getState().login(mockTokens, mockUsuario)

    const raw = localStorage.getItem('food-store-auth')!
    const stored = JSON.parse(raw)
    // Must contain the four persisted fields
    expect(stored.state).toHaveProperty('accessToken')
    expect(stored.state).toHaveProperty('refreshToken')
    expect(stored.state).toHaveProperty('usuario')
    expect(stored.state).toHaveProperty('isAuthenticated')
    // Must NOT contain action functions
    expect(stored.state.login).toBeUndefined()
    expect(stored.state.logout).toBeUndefined()
  })

  it('persist: manual rehydrate restores auth state', async () => {
    // Reset state FIRST (this also triggers a persist write which clears localStorage)
    useAuthStore.setState(authInitial)

    // Write the stored data AFTER setState so persist doesn't overwrite it
    const stored = JSON.stringify({
      state: {
        accessToken: 'stored-access',
        refreshToken: 'stored-refresh',
        usuario: mockUsuario,
        isAuthenticated: true,
      },
      version: 0,
    })
    localStorage.setItem('food-store-auth', stored)

    // Trigger rehydration and wait for onFinishHydration which fires AFTER set() is called
    await new Promise<void>((resolve) => {
      const unsub = useAuthStore.persist.onFinishHydration(() => {
        unsub()
        resolve()
      })
      useAuthStore.persist.rehydrate()
    })

    const s = useAuthStore.getState()
    expect(s.accessToken).toBe('stored-access')
    expect(s.isAuthenticated).toBe(true)
    expect(s.usuario?.email).toBe('test@example.com')
  })
})
