import { describe, expect, it, vi, beforeEach, afterEach } from 'vitest';
import * as paymentsService from '../payments.service';
import { apiClient } from '../../../../api/client';

vi.mock('../../../../api/client', () => ({
  apiClient: {
    post: vi.fn(),
    get: vi.fn(),
  },
}));

const mockPost = vi.mocked(apiClient.post);
const mockGet = vi.mocked(apiClient.get);

describe('payments.service', () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  afterEach(() => {
    vi.restoreAllMocks();
  });

  describe('createInlinePayment', () => {
    it('POSTs to /pagos/ with the correct payload', async () => {
      const payload = {
        pedido_id: 1,
        card_token: 'tok_test',
        payment_method_id: 'visa',
        installments: 1,
        idempotency_key: 'uuid-123',
        identification_type: 'DNI',
        identification_number: '12345678',
      };
      mockPost.mockResolvedValueOnce({
        data: { mp_status: 'approved', mp_id: 'mp_1', status_detail: 'accredited', order_id: 1 },
      } as any);

      const result = await paymentsService.createInlinePayment(payload);

      expect(mockPost).toHaveBeenCalledWith('/pagos/', payload);
      expect(result.mp_status).toBe('approved');
      expect(result.order_id).toBe(1);
    });
  });

  describe('getInlinePaymentStatus', () => {
    it('GETs /pagos/pedido/:id', async () => {
      mockGet.mockResolvedValueOnce({
        data: { mp_status: 'pending', mp_id: null, status_detail: null },
      } as any);

      const result = await paymentsService.getInlinePaymentStatus(42);

      expect(mockGet).toHaveBeenCalledWith('/pagos/pedido/42');
      expect(result.mp_status).toBe('pending');
    });
  });
});
