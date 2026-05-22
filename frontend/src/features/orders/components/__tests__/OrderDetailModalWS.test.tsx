/**
 * Tasks 4.3 & 4.5 — OrderDetailModal WebSocket consumers.
 *
 * 4.3 (client): subscribes to its own `order:{id}`, auto-updates on
 *               order_state_changed; does NOT react to other orders' events.
 *
 * 4.5 (admin):  subscribes to `orders:all`, auto-updates on any
 *               order_state_changed.
 */

import { describe, it, expect, vi, beforeEach, afterEach } from 'vitest';
import { render, screen, act, waitFor } from '@testing-library/react';
import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import React from 'react';

// ---------------------------------------------------------------------------
// Fake WebSocket
// ---------------------------------------------------------------------------

class FakeWebSocket {
  static lastInstance: FakeWebSocket | null = null;

  readyState = 0;
  onopen: ((ev: Event) => void) | null = null;
  onclose: ((ev: CloseEvent) => void) | null = null;
  onmessage: ((ev: MessageEvent) => void) | null = null;
  onerror: ((ev: Event) => void) | null = null;

  private readonly _url: string;
  sentMessages: string[] = [];

  constructor(url: string) {
    this._url = url;
    FakeWebSocket.lastInstance = this;
  }

  get url() { return this._url; }
  send(data: string) { this.sentMessages.push(data); }
  close() { this.readyState = 3; }

  simulateOpen() { this.readyState = 1; this.onopen?.(new Event('open')); }
  simulateMessage(data: object) {
    this.onmessage?.(new MessageEvent('message', { data: JSON.stringify(data) }));
  }
  simulateClose() { this.readyState = 3; this.onclose?.(new CloseEvent('close')); }
}

// ---------------------------------------------------------------------------
// Mocks
// ---------------------------------------------------------------------------

// Stable order data
const ORDER_42 = {
  id: 42,
  user_id: 10,
  estado_codigo: 'PENDIENTE',
  total: '800.00',
  costo_envio: '0.00',
  forma_pago_codigo: 'EFECTIVO',
  direccion_snapshot: null,
  notas: null,
  creado_en: '2026-01-01T00:00:00Z',
  actualizado_en: null,
  items: [],
  historial: [],
  pagos: [],
};

const ORDER_42_UPDATED = { ...ORDER_42, estado_codigo: 'EN_PREPARACION' };

const mockGetOrderDetail = vi.fn().mockResolvedValue(ORDER_42);

vi.mock('../../services/orders.service', () => ({
  getOrderDetail: (...args: unknown[]) => mockGetOrderDetail(...args),
}));

vi.mock('../../hooks/useAdvanceOrderState', () => ({
  useAdvanceOrderState: () => ({
    mutate: vi.fn(),
    isPending: false,
  }),
}));

vi.mock('../../hooks/useTransitionOrderState', () => ({
  useTransitionOrderState: () => ({
    mutate: vi.fn(),
    isPending: false,
    isError: false,
  }),
}));

vi.mock('../../../auth/stores/authStore', () => ({
  useAuthStore: vi.fn((selector: (s: { user: { id: number; roles: string[] } }) => unknown) =>
    selector({ user: { id: 10, roles: ['CLIENT'] } }),
  ),
}));

vi.mock('../../../auth/services/auth.service', () => ({
  getToken: vi.fn().mockResolvedValue({ access_token: 'ws-token', token_type: 'bearer' }),
}));

// ---------------------------------------------------------------------------
// Setup
// ---------------------------------------------------------------------------

const originalWS = global.WebSocket;

beforeEach(() => {
  vi.useFakeTimers();
  FakeWebSocket.lastInstance = null;
  // @ts-expect-error replace global WS
  global.WebSocket = FakeWebSocket;
  Object.assign(global.WebSocket, { CONNECTING: 0, OPEN: 1, CLOSING: 2, CLOSED: 3 });
  mockGetOrderDetail.mockResolvedValue(ORDER_42);
});

afterEach(() => {
  vi.useRealTimers();
  global.WebSocket = originalWS;
  vi.clearAllMocks();
});

// ---------------------------------------------------------------------------
// Subject
// ---------------------------------------------------------------------------

import { OrderDetailModal } from '../OrderDetailModal';

function renderModal(orderId: number, isAdmin = false) {
  const qc = new QueryClient({ defaultOptions: { queries: { retry: false } } });
  return render(
    <QueryClientProvider client={qc}>
      <OrderDetailModal orderId={orderId} isAdmin={isAdmin} onClose={vi.fn()} />
    </QueryClientProvider>,
  );
}

// ---------------------------------------------------------------------------
// Task 4.3 — CLIENT consumer
// ---------------------------------------------------------------------------

describe('OrderDetailModal (client view) — WS subscription (task 4.3)', () => {
  it('subscribes to order:{id} on the shared WS', async () => {
    renderModal(42, false);

    await act(async () => { await vi.runAllTicks(); });
    expect(FakeWebSocket.lastInstance).not.toBeNull();

    act(() => { FakeWebSocket.lastInstance!.simulateOpen(); });

    const subscribeMsgs = FakeWebSocket.lastInstance!.sentMessages
      .map((m) => JSON.parse(m))
      .filter((f) => f.type === 'subscribe');

    expect(subscribeMsgs).toHaveLength(1);
    expect(subscribeMsgs[0]).toMatchObject({ v: 1, type: 'subscribe', topic: 'order:42' });
  });

  it('refetches order detail when order_state_changed arrives for the same order', async () => {
    renderModal(42, false);

    await act(async () => { await vi.runAllTicks(); });
    await act(async () => { FakeWebSocket.lastInstance!.simulateOpen(); });

    const callsBefore = mockGetOrderDetail.mock.calls.length;

    // Simulate a state change for order 42
    await act(async () => {
      FakeWebSocket.lastInstance!.simulateMessage({
        v: 1,
        type: 'order_state_changed',
        topic: 'order:42',
        payload: { pedido_id: 42, estado_nuevo: 'EN_PREPARACION' },
        ts: '2026-01-01T00:00:00Z',
      });
      await vi.runAllTicks();
    });

    // getOrderDetail should have been called again (refetch triggered by WS event)
    expect(mockGetOrderDetail.mock.calls.length).toBeGreaterThan(callsBefore);
  });

  it('does NOT refetch when order_state_changed is for a different order', async () => {
    renderModal(42, false);

    await act(async () => { await vi.runAllTicks(); });
    act(() => { FakeWebSocket.lastInstance!.simulateOpen(); });

    const callsAfterConnect = mockGetOrderDetail.mock.calls.length;

    await act(async () => {
      // Event for order 99 — should be filtered out by useOrderWebSocket topic matching
      FakeWebSocket.lastInstance!.simulateMessage({
        v: 1,
        type: 'order_state_changed',
        topic: 'order:99',
        payload: { pedido_id: 99, estado_nuevo: 'TERMINADO' },
        ts: '2026-01-01T00:00:00Z',
      });
    });

    // getOrderDetail call count should not increase
    expect(mockGetOrderDetail).toHaveBeenCalledTimes(callsAfterConnect);
  });
});

// ---------------------------------------------------------------------------
// Task 4.5 — ADMIN consumer
// ---------------------------------------------------------------------------

describe('OrderDetailModal (admin view) — WS subscription (task 4.5)', () => {
  it('subscribes to orders:all when isAdmin=true', async () => {
    renderModal(42, true);

    await act(async () => { await vi.runAllTicks(); });
    act(() => { FakeWebSocket.lastInstance!.simulateOpen(); });

    const subscribeMsgs = FakeWebSocket.lastInstance!.sentMessages
      .map((m) => JSON.parse(m))
      .filter((f) => f.type === 'subscribe');

    expect(subscribeMsgs).toHaveLength(1);
    expect(subscribeMsgs[0]).toMatchObject({ v: 1, type: 'subscribe', topic: 'orders:all' });
  });

  it('refetches on any order_state_changed arriving on orders:all', async () => {
    renderModal(42, true);

    await act(async () => { await vi.runAllTicks(); });
    await act(async () => { FakeWebSocket.lastInstance!.simulateOpen(); });

    const callsBefore = mockGetOrderDetail.mock.calls.length;

    await act(async () => {
      FakeWebSocket.lastInstance!.simulateMessage({
        v: 1,
        type: 'order_state_changed',
        topic: 'orders:all',
        payload: { pedido_id: 7, estado_nuevo: 'TERMINADO' },
        ts: '2026-01-01T00:00:00Z',
      });
      await vi.runAllTicks();
    });

    expect(mockGetOrderDetail.mock.calls.length).toBeGreaterThan(callsBefore);
  });
});
