/**
 * Tests — useKitchenOrders hook.
 *
 * Verifica que el hook de TanStack Query:
 * - Fetch data desde el endpoint correcto
 * - Retorna solo pedidos CONFIRMADO + EN_PREPARACION
 * - Usa la queryKey ['cocina', 'pedidos']
 */
import { describe, it, expect, vi, beforeEach } from 'vitest';
import { renderHook, waitFor } from '@testing-library/react';
import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import { useKitchenOrders } from '../hooks/useKitchenOrders';
import * as cocinaApi from '../api/cocinaApi';

vi.mock('../api/cocinaApi', () => ({
  getKitchenOrders: vi.fn(),
}));

const mockGetKitchenOrders = vi.mocked(cocinaApi.getKitchenOrders);

function createWrapper() {
  const queryClient = new QueryClient({
    defaultOptions: {
      queries: { retry: false },
    },
  });
  return function Wrapper({ children }: { children: React.ReactNode }) {
    return (
      <QueryClientProvider client={queryClient}>
        {children}
      </QueryClientProvider>
    );
  };
}

describe('useKitchenOrders', () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  it('fetches data from getKitchenOrders', async () => {
    const mockOrders = [
      {
        id: 1,
        estado: 'CONFIRMADO' as const,
        items: [],
        notas: null,
        cocina_entry_at: '2025-01-01T00:00:00Z',
      },
    ];
    mockGetKitchenOrders.mockResolvedValueOnce(mockOrders);

    const { result } = renderHook(() => useKitchenOrders(), {
      wrapper: createWrapper(),
    });

    expect(result.current.isLoading).toBe(true);

    await waitFor(() => {
      expect(result.current.isSuccess).toBe(true);
    });

    expect(mockGetKitchenOrders).toHaveBeenCalledTimes(1);
    expect(result.current.data).toEqual(mockOrders);
  });

  it('returns CONFIRMADO and EN_PREPARACION orders from the API', async () => {
    const mockOrders = [
      {
        id: 1,
        estado: 'CONFIRMADO' as const,
        items: [],
        notas: null,
        cocina_entry_at: '2025-01-01T00:00:00Z',
      },
      {
        id: 2,
        estado: 'EN_PREPARACION' as const,
        items: [],
        notas: null,
        cocina_entry_at: '2025-01-01T00:05:00Z',
      },
    ];
    mockGetKitchenOrders.mockResolvedValueOnce(mockOrders);

    const { result } = renderHook(() => useKitchenOrders(), {
      wrapper: createWrapper(),
    });

    await waitFor(() => {
      expect(result.current.data).toEqual(mockOrders);
    });

    const estados = result.current.data!.map((o) => o.estado);
    expect(estados).toContain('CONFIRMADO');
    expect(estados).toContain('EN_PREPARACION');
  });

  it('uses the correct queryKey', async () => {
    mockGetKitchenOrders.mockResolvedValueOnce([]);

    const queryClient = new QueryClient({
      defaultOptions: { queries: { retry: false } },
    });

    renderHook(() => useKitchenOrders(), {
      wrapper: ({ children }) => (
        <QueryClientProvider client={queryClient}>
          {children}
        </QueryClientProvider>
      ),
    });

    await waitFor(() => {
      const cache = queryClient.getQueryData(['cocina', 'pedidos']);
      expect(cache).toEqual([]);
    });
  });

  it('respects the enabled option', async () => {
    const { result } = renderHook(
      () => useKitchenOrders({ enabled: false }),
      { wrapper: createWrapper() },
    );

    // Should not fetch when disabled
    expect(mockGetKitchenOrders).not.toHaveBeenCalled();
    expect(result.current.isLoading).toBe(false);
    expect(result.current.isFetching).toBe(false);
  });

  it('does not refetch by default (refetchInterval: false)', async () => {
    mockGetKitchenOrders.mockResolvedValue([]);

    const { result } = renderHook(() => useKitchenOrders(), {
      wrapper: createWrapper(),
    });

    await waitFor(() => {
      expect(result.current.isFetched).toBe(true);
    });

    const callCount = mockGetKitchenOrders.mock.calls.length;
    // After initial fetch, no automatic refetches should occur
    expect(callCount).toBe(1);
  });
});
