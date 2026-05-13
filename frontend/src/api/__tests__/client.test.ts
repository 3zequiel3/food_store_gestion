import { describe, expect, it } from 'vitest';
import type { AxiosAdapter } from 'axios';
import { apiClient } from '../client';
import { useAuthStore } from '../../features/auth/stores/authStore';

describe('apiClient cookie auth behavior', () => {
  it('uses credentials and does not inject Authorization headers from authStore', async () => {
    useAuthStore.getState().setSession({
      user: {
        id: 1,
        email: 'test@example.com',
        nombre: 'Test',
        apellido: 'User',
        roles: ['CLIENT'],
      },
    });

    let authorization: unknown;
    const previousAdapter = apiClient.defaults.adapter;
    const adapter: AxiosAdapter = async (config) => {
      authorization = config.headers?.Authorization;
      return {
        data: { ok: true },
        status: 200,
        statusText: 'OK',
        headers: {},
        config,
      };
    };

    apiClient.defaults.adapter = adapter;
    try {
      await apiClient.get('/auth/me');
    } finally {
      apiClient.defaults.adapter = previousAdapter;
      useAuthStore.getState().clearSession();
    }

    expect(apiClient.defaults.withCredentials).toBe(true);
    expect(authorization).toBeUndefined();
  });
});
