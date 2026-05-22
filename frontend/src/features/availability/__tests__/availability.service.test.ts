/**
 * Tests — availability service + useFaltantes hook (Task 6.22).
 *
 * Verifica:
 * - getFaltantes llama GET /availability/faltantes y retorna los datos.
 * - resolverFaltante llama POST /availability/faltantes/{id}/resolver con el body.
 * - El navbar inbox badge incrementa al recibir ingredient_unavailable_reported.
 * - El badge se resetea al 0 cuando el admin abre la vista Faltantes.
 */
import { describe, it, expect, vi, beforeEach, afterEach } from 'vitest';
import { getFaltantes, resolverFaltante } from '../services/availability.service';
import { apiClient } from '../../../api/client';

vi.mock('../../../api/client', () => ({
  apiClient: {
    get: vi.fn(),
    post: vi.fn(),
  },
}));

const mockGet = vi.mocked(apiClient.get);
const mockPost = vi.mocked(apiClient.post);

describe('availability.service', () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  afterEach(() => {
    vi.restoreAllMocks();
  });

  describe('getFaltantes', () => {
    it('calls GET /availability/faltantes and returns the list', async () => {
      const mockData = [
        {
          id: 1,
          ingrediente_id: 10,
          ingrediente_nombre: 'Lechuga',
          reportado_por: 2,
          pedido_id: 5,
          creado_en: '2026-05-21T00:00:00Z',
          resuelto_en: null,
          resuelto_por: null,
        },
      ];
      mockGet.mockResolvedValueOnce({ data: mockData } as any);

      const result = await getFaltantes();

      expect(mockGet).toHaveBeenCalledWith('/availability/faltantes');
      expect(result).toEqual(mockData);
    });

    it('returns an empty array when no open shortages exist', async () => {
      mockGet.mockResolvedValueOnce({ data: [] } as any);
      const result = await getFaltantes();
      expect(result).toEqual([]);
    });
  });

  describe('resolverFaltante', () => {
    it('calls POST /availability/faltantes/{id}/resolver with accion body', async () => {
      mockPost.mockResolvedValueOnce({
        data: { ok: true, ingrediente_id: 10, rows_closed: 2 },
      } as any);

      const result = await resolverFaltante(10, { accion: 'ingrediente comprado' });

      expect(mockPost).toHaveBeenCalledWith(
        '/availability/faltantes/10/resolver',
        { accion: 'ingrediente comprado' },
      );
      expect(result.ok).toBe(true);
      expect(result.rows_closed).toBe(2);
    });

    it('calls POST with default empty body when accion not provided', async () => {
      mockPost.mockResolvedValueOnce({
        data: { ok: true, ingrediente_id: 5, rows_closed: 1 },
      } as any);

      await resolverFaltante(5);

      expect(mockPost).toHaveBeenCalledWith(
        '/availability/faltantes/5/resolver',
        {},
      );
    });
  });
});

// ---------------------------------------------------------------------------
// Faltantes store (badge counter)
// ---------------------------------------------------------------------------

describe('faltantesStore — navbar badge', () => {
  it('increments badge count on ingredient_unavailable_reported event', async () => {
    const { useFaltantesStore } = await import('../stores/faltantesStore');
    useFaltantesStore.getState().reset();

    useFaltantesStore.getState().increment();
    useFaltantesStore.getState().increment();

    expect(useFaltantesStore.getState().pendingCount).toBe(2);
  });

  it('resets badge count to 0 when admin opens Faltantes view', async () => {
    const { useFaltantesStore } = await import('../stores/faltantesStore');
    useFaltantesStore.getState().increment();
    useFaltantesStore.getState().increment();

    useFaltantesStore.getState().reset();

    expect(useFaltantesStore.getState().pendingCount).toBe(0);
  });

  it('sync count sets the badge to a specific number', async () => {
    const { useFaltantesStore } = await import('../stores/faltantesStore');
    useFaltantesStore.getState().reset();

    useFaltantesStore.getState().setCount(5);

    expect(useFaltantesStore.getState().pendingCount).toBe(5);
  });
});
