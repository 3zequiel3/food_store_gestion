import { beforeEach, describe, expect, it, vi } from 'vitest';
import { useAuthStore } from '../authStore';

const user = {
  id: 1,
  email: 'test@example.com',
  nombre: 'Test',
  apellido: 'User',
  roles: ['CLIENT'],
};

describe('authStore cookie-backed session', () => {
  beforeEach(() => {
    useAuthStore.getState().clearSession();
    localStorage.clear();
  });

  it('stores only user session data, not access or refresh tokens', () => {
    useAuthStore.getState().setSession({ user });

    expect(useAuthStore.getState().isAuthenticated()).toBe(true);
    expect(useAuthStore.getState().hasRole('CLIENT')).toBe(true);

    const raw = localStorage.getItem('food-store-auth');
    expect(raw).toBeTruthy();
    expect(raw).not.toContain('accessToken');
    expect(raw).not.toContain('refreshToken');
    expect(raw).not.toContain('access_token');
    expect(raw).not.toContain('refresh_token');
  });

  it('clears only local user state on logout', () => {
    useAuthStore.getState().setSession({ user });
    useAuthStore.getState().clearSession();

    expect(useAuthStore.getState().user).toBeNull();
    expect(useAuthStore.getState().isAuthenticated()).toBe(false);
  });

  it('migrates old persisted token payloads to user-only state', async () => {
    localStorage.setItem(
      'food-store-auth',
      JSON.stringify({
        state: {
          user,
          accessToken: 'old-access-token',
          refreshToken: 'old-refresh-token',
        },
        version: 1,
      }),
    );

    vi.resetModules();
    const { useAuthStore: freshAuthStore } = await import('../authStore');

    expect(freshAuthStore.getState().user).toEqual(user);

    const raw = localStorage.getItem('food-store-auth');
    expect(raw).toBeTruthy();
    expect(raw).not.toContain('old-access-token');
    expect(raw).not.toContain('old-refresh-token');
    expect(raw).not.toContain('accessToken');
    expect(raw).not.toContain('refreshToken');
  });
});
