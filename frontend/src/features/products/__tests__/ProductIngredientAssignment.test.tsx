/**
 * Task 3.5 — P2.7: the product-ingredient assignment request must NOT include
 * a per-association `es_removible` field. The `es_removible` flag lives on the
 * `Ingrediente` entity and is read from there by all consumers.
 */

import { describe, it, expect, vi, beforeEach } from 'vitest';
import * as adminService from '../../products/services/admin-products.service';

// We spy on the underlying apiClient.post to capture exactly what payload is
// sent, without making a real HTTP request.
vi.mock('../../../api/client', () => ({
  apiClient: {
    post: vi.fn().mockResolvedValue({
      data: { ingrediente_id: 1, producto_id: 99 },
    }),
    delete: vi.fn().mockResolvedValue({ data: null }),
  },
}));

vi.mock('../../../lib/constants/endpoints', () => ({
  ENDPOINTS: {
    productos: {
      ingredientes: (id: number) => `/productos/${id}/ingredientes`,
      ingredienteDelete: (pid: number, iid: number) =>
        `/productos/${pid}/ingredientes/${iid}`,
    },
  },
}));

import { apiClient } from '../../../api/client';

beforeEach(() => {
  vi.clearAllMocks();
});

describe('addProductIngredient — P2.7: no per-association es_removible', () => {
  it('sends only ingrediente_id in the request body (no es_removible field)', async () => {
    // addProductIngredient signature after P2.7 drops the esRemovible parameter.
    await adminService.addProductIngredient(99, 1);

    expect(apiClient.post).toHaveBeenCalledOnce();
    const [, payload] = (apiClient.post as ReturnType<typeof vi.fn>).mock.calls[0];

    // Must contain ingrediente_id
    expect(payload).toHaveProperty('ingrediente_id', 1);

    // Must NOT contain es_removible — that flag lives on the Ingrediente entity
    expect(payload).not.toHaveProperty('es_removible');
  });

  it('still calls the correct endpoint', async () => {
    await adminService.addProductIngredient(99, 1);

    const [url] = (apiClient.post as ReturnType<typeof vi.fn>).mock.calls[0];
    expect(url).toBe('/productos/99/ingredientes');
  });
});
