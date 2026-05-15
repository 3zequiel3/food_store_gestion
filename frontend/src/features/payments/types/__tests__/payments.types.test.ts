import { describe, expect, it } from 'vitest';
import type {
  PaymentCreateRequest,
  PaymentResponse,
  TransicionarRequest,
  TransicionarResponse,
} from '../payments.types';

describe('payment types shape', () => {
  it('PaymentCreateRequest has required fields', () => {
    const req: PaymentCreateRequest = {
      pedido_id: 1,
      card_token: 'tok_test_123',
      payment_method_id: 'visa',
      installments: 1,
      idempotency_key: crypto.randomUUID(),
      identification_type: 'DNI',
      identification_number: '12345678',
    };
    expect(req.pedido_id).toBe(1);
    expect(req.card_token).toBe('tok_test_123');
    expect(req.payment_method_id).toBe('visa');
    expect(req.identification_type).toBe('DNI');
    expect(req.identification_number).toBe('12345678');
    expect(req.installments).toBe(1);
    expect(req.idempotency_key).toMatch(
      /^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$/i,
    );
  });

  it('PaymentResponse has required fields', () => {
    const res: PaymentResponse = {
      mp_status: 'approved',
      mp_id: 'mp_123',
      status_detail: 'accredited',
      order_id: 42,
    };
    expect(res.mp_status).toBe('approved');
    expect(res.mp_id).toBe('mp_123');
    expect(res.status_detail).toBe('accredited');
    expect(res.order_id).toBe(42);
  });

  it('PaymentResponse allows null mp_id and status_detail', () => {
    const res: PaymentResponse = {
      mp_status: 'rejected',
      mp_id: null,
      status_detail: null,
    };
    expect(res.mp_id).toBeNull();
    expect(res.status_detail).toBeNull();
  });

  it('TransicionarRequest has required fields', () => {
    const req: TransicionarRequest = {
      estado_codigo_destino: 'CONFIRMADO',
    };
    expect(req.estado_codigo_destino).toBe('CONFIRMADO');
    expect(req.motivo).toBeUndefined();
  });

  it('TransicionarRequest accepts optional motivo', () => {
    const req: TransicionarRequest = {
      estado_codigo_destino: 'CANCELADO',
      motivo: 'Cliente cambió de opinión',
    };
    expect(req.motivo).toBe('Cliente cambió de opinión');
  });

  it('TransicionarResponse has required fields', () => {
    const res: TransicionarResponse = {
      pedido_id: 1,
      estado_anterior: 'PENDIENTE',
      estado_nuevo: 'CONFIRMADO',
      historial: [
        {
          id: 1,
          estado_anterior: null,
          estado_nuevo: 'PENDIENTE',
          actor: null,
          motivo: null,
          creado_en: '2025-01-01T00:00:00Z',
        },
        {
          id: 2,
          estado_anterior: 'PENDIENTE',
          estado_nuevo: 'CONFIRMADO',
          actor: 'admin',
          motivo: null,
          creado_en: '2025-01-01T00:01:00Z',
        },
      ],
    };
    expect(res.pedido_id).toBe(1);
    expect(res.estado_anterior).toBe('PENDIENTE');
    expect(res.estado_nuevo).toBe('CONFIRMADO');
    expect(res.historial).toHaveLength(2);
    expect(res.historial[1].actor).toBe('admin');
  });
});
