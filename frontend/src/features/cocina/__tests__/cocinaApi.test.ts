/**
 * Tests — cocinaApi module.
 *
 * Verifica que las funciones de la API de cocina llamen a los endpoints correctos
 * con los payloads esperados.
 */
import { describe, it, expect, vi, beforeEach, afterEach } from 'vitest';
import { getKitchenOrders, transitionKitchenOrder } from '../api/cocinaApi';
import { apiClient } from '../../../api/client';

vi.mock('../../../api/client', () => ({
  apiClient: {
    get: vi.fn(),
    post: vi.fn(),
  },
}));

const mockGet = vi.mocked(apiClient.get);
const mockPost = vi.mocked(apiClient.post);

describe('cocinaApi', () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  afterEach(() => {
    vi.restoreAllMocks();
  });

  describe('getKitchenOrders', () => {
    it('calls GET /cocina/pedidos and returns the data array', async () => {
      const mockOrders = [
        {
          id: 1,
          estado: 'CONFIRMADO' as const,
          items: [],
          notas: null,
          cocina_entry_at: '2025-01-01T00:00:00Z',
        },
      ];
      mockGet.mockResolvedValueOnce({ data: mockOrders } as any);

      const result = await getKitchenOrders();

      expect(mockGet).toHaveBeenCalledWith('/cocina/pedidos');
      expect(result).toEqual(mockOrders);
    });

    it('returns an empty array when backend returns no orders', async () => {
      mockGet.mockResolvedValueOnce({ data: [] } as any);

      const result = await getKitchenOrders();

      expect(result).toEqual([]);
    });
  });

  describe('transitionKitchenOrder', () => {
    it('calls POST /pedidos/{id}/transicionar with correct body', async () => {
      mockPost.mockResolvedValueOnce({
        data: {
          pedido_id: 1,
          estado_anterior: 'CONFIRMADO',
          estado_nuevo: 'EN_PREPARACION',
        },
      } as any);

      const result = await transitionKitchenOrder(1, 'EN_PREPARACION');

      expect(mockPost).toHaveBeenCalledWith('/pedidos/1/transicionar', {
        estado_codigo_destino: 'EN_PREPARACION',
      });
      expect(result.estado_nuevo).toBe('EN_PREPARACION');
    });

    it('transitions to TERMINADO correctly', async () => {
      mockPost.mockResolvedValueOnce({
        data: {
          pedido_id: 5,
          estado_anterior: 'EN_PREPARACION',
          estado_nuevo: 'TERMINADO',
        },
      } as any);

      const result = await transitionKitchenOrder(5, 'TERMINADO');

      expect(mockPost).toHaveBeenCalledWith('/pedidos/5/transicionar', {
        estado_codigo_destino: 'TERMINADO',
      });
      expect(result.estado_nuevo).toBe('TERMINADO');
    });
  });
});
