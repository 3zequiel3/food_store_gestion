import { create } from 'zustand';
import { persist, createJSONStorage } from 'zustand/middleware';
import type { SessionPayload, Usuario } from '../types/auth.types';

interface AuthState {
  user: Usuario | null;
}

interface AuthActions {
  /** Persiste únicamente datos no sensibles del usuario. */
  setSession(payload: SessionPayload): void;
  /** Limpia la sesión local. NO toca cartStore. */
  clearSession(): void;
  /** True si hay usuario cargado localmente. */
  isAuthenticated(): boolean;
  /** True si user.roles contiene un rol con el código dado. */
  hasRole(roleCode: string): boolean;
}

type AuthStore = AuthState & AuthActions;

/**
 * Store de autenticación cookie-backed.
 * Los tokens viven en cookies HttpOnly administradas por backend, nunca en JS.
 */
export const useAuthStore = create<AuthStore>()(
  persist(
    (set, get) => ({
      user: null,

      setSession({ user }) {
        set({ user });
      },

      clearSession() {
        set({ user: null });
      },

      isAuthenticated() {
        return get().user !== null;
      },

      hasRole(roleCode: string) {
        const user = get().user;
        if (!user) return false;
        return user.roles.includes(roleCode);
      },
    }),
    {
      name: 'food-store-auth',
      version: 2,
      storage: createJSONStorage(() => localStorage),
      migrate: (persistedState) => {
        const state = persistedState as { user?: Usuario | null };
        return { user: state.user ?? null };
      },
      partialize: (state) => ({ user: state.user }),
    },
  ),
);
