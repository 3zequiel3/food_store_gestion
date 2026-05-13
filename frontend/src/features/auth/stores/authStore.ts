import { create } from 'zustand';
import { persist, createJSONStorage } from 'zustand/middleware';
import type { Usuario, SessionPayload } from '../types/auth.types';

interface AuthState {
  accessToken: string | null;
  refreshToken: string | null;
  user: Usuario | null;
}

interface AuthActions {
  /** Persiste tokens + usuario tras login o refresh exitoso */
  setSession(payload: SessionPayload): void;
  /** Limpia la sesión (logout / refresh fallido). NO toca cartStore (D2). */
  clearSession(): void;
  /** Retorna el access token actual — safe de llamar desde código no-React */
  getAccessToken(): string | null;
  /** Retorna el refresh token actual */
  getRefreshToken(): string | null;
  /** True si hay accessToken en el store */
  isAuthenticated(): boolean;
  /** True si user.roles contiene un rol con el código dado */
  hasRole(roleCode: string): boolean;
}

type AuthStore = AuthState & AuthActions;

/**
 * D2 — Único store de autenticación.
 * Zustand con persist en localStorage (storage key: food-store-auth).
 *
 * Diseño:
 * - partialize excluye cualquier campo transitorio futuro de la persistencia.
 * - getState() funciona fuera del contexto React (lo usa el interceptor axios).
 * - clearSession() NO toca useCartStore (RN: el carrito sobrevive al logout).
 */
export const useAuthStore = create<AuthStore>()(
  persist(
    (set, get) => ({
      // Estado inicial
      accessToken: null,
      refreshToken: null,
      user: null,

      // Acciones
      setSession({ accessToken, refreshToken, user }) {
        set({ accessToken, refreshToken, user });
      },

      clearSession() {
        set({ accessToken: null, refreshToken: null, user: null });
      },

      // Getters — implementados como funciones para evitar stale closures
      getAccessToken() {
        return get().accessToken;
      },

      getRefreshToken() {
        return get().refreshToken;
      },

      isAuthenticated() {
        return get().accessToken !== null;
      },

      hasRole(roleCode: string) {
        const user = get().user;
        if (!user) return false;
        return user.roles.includes(roleCode);
      },
    }),
    {
      name: 'food-store-auth',
      storage: createJSONStorage(() => localStorage),
      // partialize: solo persistir los campos de estado, no las funciones
      partialize: (state) => ({
        accessToken: state.accessToken,
        refreshToken: state.refreshToken,
        user: state.user,
      }),
    },
  ),
);
