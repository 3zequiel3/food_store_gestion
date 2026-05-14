import { describe, expect, it, vi, beforeEach, afterEach } from 'vitest';
import { transicionarEstado } from '../orders.service';
import { apiClient } from '../../../../api/client';

vi.mock('../../../../api/client', () => ({
  apiClient: {
    post: vi.fn(),
  },
}));

const mockPost = vi.mocked(apiClient.post);

describe('orders.service — transicionarEstado', () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  afterEach(() => {
    vi.restoreAllMocks();
  });

  it('POSTs to /pedidos/:id/transicionar with correct body', async () => {
    mockPost.mockResolvedValueOnce({
      data: {
        pedido_id: 1,
        estado_anterior: 'PENDIENTE',
        estado_nuevo: 'CONFIRMADO',
        historial: [],
      },
    } as any);

    const result = await transicionarEstado(1, 'CONFIRMADO');

    expect(mockPost).toHaveBeenCalledWith('/pedidos/1/transicionar', {
      estado_codigo_destino: 'CONFIRMADO',
    });
    expect(result.estado_nuevo).toBe('CONFIRMADO');
  });

  it('includes motivo when provided', async () => {
    mockPost.mockResolvedValueOnce({
      data: {
        pedido_id: 1,
        estado_anterior: 'PENDIENTE',
        estado_nuevo: 'CANCELADO',
        historial: [],
      },
    } as any);

    await transicionarEstado(1, 'CANCELADO', 'Cliente arrepentido');

    expect(mockPost).toHaveBeenCalledWith('/pedidos/1/transicionar', {
      estado_codigo_destino: 'CANCELADO',
      motivo: 'Cliente arrepentido',
    });
  });

  it('returns the transition response with historial', async () => {
    const historialEntry = {
      id: 1,
      estado_anterior: 'PENDIENTE',
      estado_nuevo: 'CONFIRMADO',
      actor: 'admin',
      motivo: null,
      creado_en: '2025-01-01T00:00:00Z',
    };
    mockPost.mockResolvedValueOnce({
      data: {
        pedido_id: 1,
        estado_anterior: 'PENDIENTE',
        estado_nuevo: 'CONFIRMADO',
        historial: [historialEntry],
      },
    } as any);

    const result = await transicionarEstado(1, 'CONFIRMADO');

    expect(result.historial).toHaveLength(1);
    expect(result.historial[0].actor).toBe('admin');
  });
});
