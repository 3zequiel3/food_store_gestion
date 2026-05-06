import { create } from 'zustand'
import { persist } from 'zustand/middleware'
import type { Usuario, AuthTokens, RolCode } from '../../entities/user/model'

interface AuthState {
  accessToken: string | null
  refreshToken: string | null
  /** Authenticated user profile. Named `usuario` per canonical spec (Integrador.txt:256). */
  usuario: Usuario | null
  isAuthenticated: boolean

  /** Populate auth state after a successful login response. */
  login: (tokens: AuthTokens, usuario: Usuario) => void

  /**
   * Clear auth state only.
   *
   * IMPORTANT — RN-CR02: this action MUST NOT touch `useCartStore`.
   * The cart must survive logout/login, page refresh, and browser close.
   * If a specific flow needs to clear the cart on logout, the orchestrating
   * code (feature/page) should call `useCartStore.getState().clearCart()`
   * explicitly — never from here.
   */
  logout: () => void

  /** Atomically rotate the access + refresh token pair after a silent refresh. */
  updateTokens: (tokens: AuthTokens) => void
}

const initialState = {
  accessToken: null,
  refreshToken: null,
  usuario: null,
  isAuthenticated: false,
} as const

export const useAuthStore = create<AuthState>()(
  persist(
    (set) => ({
      ...initialState,

      login: (tokens: AuthTokens, usuario: Usuario) => {
        set({
          accessToken: tokens.accessToken,
          refreshToken: tokens.refreshToken,
          usuario,
          isAuthenticated: true,
        })
      },

      logout: () => {
        // Clears auth state only — cart is intentionally untouched (RN-CR02).
        set({ ...initialState })
      },

      updateTokens: (tokens: AuthTokens) => {
        // Replaces both tokens atomically; usuario and isAuthenticated remain unchanged.
        set({ accessToken: tokens.accessToken, refreshToken: tokens.refreshToken })
      },
    }),
    {
      name: 'food-store-auth',
      partialize: (state) => ({
        accessToken: state.accessToken,
        refreshToken: state.refreshToken,
        usuario: state.usuario,
        isAuthenticated: state.isAuthenticated,
      }),
    }
  )
)

// ---------------------------------------------------------------------------
// Atomic selectors
// Usage in components: const isAuth = useAuthStore(selectIsAuthenticated)
// Usage outside React: useAuthStore.getState().accessToken
// ---------------------------------------------------------------------------

export const selectIsAuthenticated = (s: AuthState) => s.isAuthenticated
export const selectAccessToken = (s: AuthState) => s.accessToken
export const selectRefreshToken = (s: AuthState) => s.refreshToken
export const selectUsuario = (s: AuthState) => s.usuario

/**
 * Role-membership selector factory.
 *
 * @example
 * const isAdmin = useAuthStore(selectHasRol('ADMIN'))
 */
export const selectHasRol = (rol: RolCode) => (s: AuthState) =>
  s.usuario?.roles.some((r) => r.codigo === rol) ?? false
