/**
 * Task 4.1 — shared WS client/hook tests.
 *
 * Contract:
 * - Subscribes to a topic after handshake ({v:1,type:"subscribe",topic:"order:42"})
 * - Calls onEvent when an order_state_changed frame arrives for that topic
 * - Does NOT call onEvent for frames targeting a different topic
 * - Falls back to polling (30s interval) when isConnected is false
 * - Reads /ws/health to detect degraded mode
 */

import { describe, it, expect, vi, beforeEach, afterEach } from 'vitest';
import { renderHook, act, waitFor } from '@testing-library/react';
import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import React from 'react';

// ---------------------------------------------------------------------------
// Fake WebSocket
// ---------------------------------------------------------------------------

class FakeWebSocket {
  static lastInstance: FakeWebSocket | null = null;

  readyState = WebSocket.CONNECTING;
  onopen: ((ev: Event) => void) | null = null;
  onclose: ((ev: CloseEvent) => void) | null = null;
  onmessage: ((ev: MessageEvent) => void) | null = null;
  onerror: ((ev: Event) => void) | null = null;

  sentMessages: string[] = [];
  private _url: string;

  constructor(url: string) {
    this._url = url;
    FakeWebSocket.lastInstance = this;
  }

  get url() { return this._url; }

  send(data: string) {
    this.sentMessages.push(data);
  }

  close() {
    this.readyState = WebSocket.CLOSED;
  }

  // Test helpers — simulate server-side events
  simulateOpen() {
    this.readyState = WebSocket.OPEN;
    this.onopen?.(new Event('open'));
  }

  simulateMessage(data: object) {
    this.onmessage?.(new MessageEvent('message', { data: JSON.stringify(data) }));
  }

  simulateClose() {
    this.readyState = WebSocket.CLOSED;
    this.onclose?.(new CloseEvent('close'));
  }
}

// ---------------------------------------------------------------------------
// Mocks
// ---------------------------------------------------------------------------

vi.mock('../../../auth/services/auth.service', () => ({
  getToken: vi.fn().mockResolvedValue({ access_token: 'test-jwt-token', token_type: 'bearer' }),
}));

vi.mock('../../../auth/stores/authStore', () => ({
  useAuthStore: vi.fn((selector: (s: { user: { id: number } | null }) => unknown) =>
    selector({ user: { id: 1 } }),
  ),
}));

vi.mock('../../../../api/client', () => ({
  apiClient: {
    get: vi.fn().mockResolvedValue({ data: { status: 'ok', drain_alive: true, connection_count: 1 } }),
  },
}));

vi.mock('../../../api/client', () => ({
  apiClient: {
    get: vi.fn().mockResolvedValue({ data: { status: 'ok', drain_alive: true, connection_count: 1 } }),
  },
}));

// ---------------------------------------------------------------------------
// Setup
// ---------------------------------------------------------------------------

const originalWebSocket = global.WebSocket;

beforeEach(() => {
  vi.useFakeTimers();
  FakeWebSocket.lastInstance = null;
  // @ts-expect-error replace global WS
  global.WebSocket = FakeWebSocket;
  Object.assign(global.WebSocket, {
    CONNECTING: 0,
    OPEN: 1,
    CLOSING: 2,
    CLOSED: 3,
  });
});

afterEach(() => {
  vi.useRealTimers();
  global.WebSocket = originalWebSocket;
  vi.clearAllMocks();
});

// ---------------------------------------------------------------------------
// Import subject AFTER mocks are set
// ---------------------------------------------------------------------------

import { useOrderWebSocket } from '../useOrderWebSocket';

function wrapper({ children }: { children: React.ReactNode }) {
  const qc = new QueryClient({ defaultOptions: { queries: { retry: false } } });
  return <QueryClientProvider client={qc}>{children}</QueryClientProvider>;
}

// ---------------------------------------------------------------------------
// Tests
// ---------------------------------------------------------------------------

describe('useOrderWebSocket — connection lifecycle', () => {
  it('connects to /ws?token=<jwt>', async () => {
    const onEvent = vi.fn();
    renderHook(
      () => useOrderWebSocket({ topic: 'order:42', onEvent }),
      { wrapper },
    );

    await act(async () => {
      await vi.runAllTicks();
    });

    expect(FakeWebSocket.lastInstance).not.toBeNull();
    const url = FakeWebSocket.lastInstance!.url;
    expect(url).toMatch(/\/ws\?token=/);
    expect(url).toContain('test-jwt-token');
  });

  it('sends a subscribe frame after handshake', async () => {
    const onEvent = vi.fn();
    renderHook(
      () => useOrderWebSocket({ topic: 'order:42', onEvent }),
      { wrapper },
    );

    await act(async () => {
      await vi.runAllTicks();
    });

    const ws = FakeWebSocket.lastInstance!;
    act(() => { ws.simulateOpen(); });

    expect(ws.sentMessages).toHaveLength(1);
    const subscribeFrame = JSON.parse(ws.sentMessages[0]);
    expect(subscribeFrame).toMatchObject({ v: 1, type: 'subscribe', topic: 'order:42' });
  });

  it('reports isConnected true after open', async () => {
    const onEvent = vi.fn();
    const { result } = renderHook(
      () => useOrderWebSocket({ topic: 'order:42', onEvent }),
      { wrapper },
    );

    await act(async () => { await vi.runAllTicks(); });
    act(() => { FakeWebSocket.lastInstance!.simulateOpen(); });

    expect(result.current.isConnected).toBe(true);
  });

  it('reports isConnected false after close', async () => {
    const onEvent = vi.fn();
    const { result } = renderHook(
      () => useOrderWebSocket({ topic: 'order:42', onEvent }),
      { wrapper },
    );

    await act(async () => { await vi.runAllTicks(); });
    act(() => { FakeWebSocket.lastInstance!.simulateOpen(); });
    act(() => { FakeWebSocket.lastInstance!.simulateClose(); });

    expect(result.current.isConnected).toBe(false);
  });
});

describe('useOrderWebSocket — event handling', () => {
  it('calls onEvent for order_state_changed on the subscribed topic', async () => {
    const onEvent = vi.fn();
    renderHook(
      () => useOrderWebSocket({ topic: 'order:42', onEvent }),
      { wrapper },
    );

    await act(async () => { await vi.runAllTicks(); });
    const ws = FakeWebSocket.lastInstance!;
    act(() => { ws.simulateOpen(); });

    act(() => {
      ws.simulateMessage({
        v: 1,
        type: 'order_state_changed',
        topic: 'order:42',
        payload: { pedido_id: 42, estado_nuevo: 'EN_PREPARACION' },
        ts: '2026-01-01T00:00:00Z',
      });
    });

    expect(onEvent).toHaveBeenCalledOnce();
    expect(onEvent.mock.calls[0][0]).toMatchObject({
      type: 'order_state_changed',
      payload: { pedido_id: 42, estado_nuevo: 'EN_PREPARACION' },
    });
  });

  it('does NOT call onEvent for events on a different topic', async () => {
    const onEvent = vi.fn();
    renderHook(
      () => useOrderWebSocket({ topic: 'order:42', onEvent }),
      { wrapper },
    );

    await act(async () => { await vi.runAllTicks(); });
    const ws = FakeWebSocket.lastInstance!;
    act(() => { ws.simulateOpen(); });

    act(() => {
      ws.simulateMessage({
        v: 1,
        type: 'order_state_changed',
        topic: 'order:99', // different order
        payload: { pedido_id: 99, estado_nuevo: 'TERMINADO' },
        ts: '2026-01-01T00:00:00Z',
      });
    });

    expect(onEvent).not.toHaveBeenCalled();
  });

  it('handles orders:all topic — forwards all order events regardless of order id', async () => {
    const onEvent = vi.fn();
    renderHook(
      () => useOrderWebSocket({ topic: 'orders:all', onEvent }),
      { wrapper },
    );

    await act(async () => { await vi.runAllTicks(); });
    const ws = FakeWebSocket.lastInstance!;
    act(() => { ws.simulateOpen(); });

    act(() => {
      ws.simulateMessage({
        v: 1,
        type: 'order_state_changed',
        topic: 'orders:all',
        payload: { pedido_id: 7, estado_nuevo: 'CONFIRMADO' },
        ts: '2026-01-01T00:00:00Z',
      });
    });

    expect(onEvent).toHaveBeenCalledOnce();
  });
});

// ---------------------------------------------------------------------------
// Task 4.4 — connection_resynced forwarded to onEvent
// ---------------------------------------------------------------------------

describe('useOrderWebSocket — connection_resynced (Task 4.4)', () => {
  it('forwards connection_resynced frame to onEvent when topic matches', async () => {
    /**
     * The hook filters frames by topic. A connection_resynced frame emitted
     * for 'orders:all' must be forwarded to the onEvent callback so that
     * AdminFaltantesPage can trigger invalidateQueries.
     *
     * FAILS if the hook drops connection_resynced frames or doesn't call onEvent.
     * (Currently the hook forwards ALL frames whose topic matches — so this
     * may pass already, but the test is needed to prevent future regression.)
     */
    const onEvent = vi.fn();
    renderHook(
      () => useOrderWebSocket({ topic: 'orders:all', onEvent }),
      { wrapper },
    );

    await act(async () => { await vi.runAllTicks(); });
    const ws = FakeWebSocket.lastInstance!;
    act(() => { ws.simulateOpen(); });

    act(() => {
      ws.simulateMessage({
        v: 1,
        type: 'connection_resynced',
        topic: 'orders:all',
        payload: { topic: 'orders:all', server_ts: '2026-05-28T00:00:00Z' },
        ts: '2026-05-28T00:00:00Z',
      });
    });

    expect(onEvent).toHaveBeenCalledOnce();
    expect(onEvent.mock.calls[0][0]).toMatchObject({
      type: 'connection_resynced',
      topic: 'orders:all',
    });
  });
});

describe('useOrderWebSocket — degraded mode / polling fallback', () => {
  it('isDegraded is true when not connected', async () => {
    const onEvent = vi.fn();
    const { result } = renderHook(
      () => useOrderWebSocket({ topic: 'order:42', onEvent }),
      { wrapper },
    );

    await act(async () => { await vi.runAllTicks(); });
    // WS open hasn't fired — still connecting → degraded
    expect(result.current.isConnected).toBe(false);
    expect(result.current.isDegraded).toBe(true);
  });

  it('isDegraded is false when connected', async () => {
    const onEvent = vi.fn();
    const { result } = renderHook(
      () => useOrderWebSocket({ topic: 'order:42', onEvent }),
      { wrapper },
    );

    await act(async () => { await vi.runAllTicks(); });
    await act(async () => { FakeWebSocket.lastInstance!.simulateOpen(); });

    expect(result.current.isDegraded).toBe(false);
  });
});
