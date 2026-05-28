/**
 * Tests — useCocinaWebSocket (Task 6.20).
 *
 * Verifica:
 * - El hook retorna reportIngredientUnavailable
 * - reportIngredientUnavailable envía el mensaje WS correcto
 * - ingredient_availability_restored invoca onAvailabilityRestored
 * - No envía cuando wsRef.current es null
 *
 * Strategy: mock WebSocket at the global level, trigger onopen/onmessage
 * directly on the mock instance after the hook has had time to connect.
 */
import React from 'react';
import { renderHook, act, waitFor } from '@testing-library/react';
import { describe, it, expect, vi, beforeEach, afterEach } from 'vitest';

// --------------------------------------------------------------------------
// Module mocks
// --------------------------------------------------------------------------
vi.mock('../../../lib/ws', () => ({
  buildWebSocketUrl: vi.fn(() => 'ws://test/ws?token=mock'),
}));

vi.mock('../../auth/stores/authStore', () => ({
  useAuthStore: vi.fn((selector: (s: { user: { id: number; nombre: string; apellido: string; roles: string[] } | null }) => unknown) =>
    selector({ user: { id: 1, nombre: 'Test', apellido: 'User', roles: ['COCINA'] } }),
  ),
}));

vi.mock('../../auth/services/auth.service', () => ({
  getToken: vi.fn().mockResolvedValue({ access_token: 'mock-token' }),
}));

const mockInvalidateQueries = vi.fn();
const mockSetQueryData = vi.fn();

vi.mock('@tanstack/react-query', () => ({
  useQueryClient: vi.fn(() => ({
    invalidateQueries: mockInvalidateQueries,
    setQueryData: mockSetQueryData,
  })),
}));

// Import AFTER mocks
import { useCocinaWebSocket } from '../hooks/useCocinaWebSocket';

// --------------------------------------------------------------------------
// WebSocket mock factory
// --------------------------------------------------------------------------
type MockWsInstance = {
  send: ReturnType<typeof vi.fn>;
  close: ReturnType<typeof vi.fn>;
  onopen: (() => void) | null;
  onmessage: ((e: { data: string }) => void) | null;
  onclose: (() => void) | null;
  onerror: (() => void) | null;
  readyState: number;
};

let mockWsSend: ReturnType<typeof vi.fn>;
let lastWsInstance: MockWsInstance;

beforeEach(() => {
  mockWsSend = vi.fn();
  lastWsInstance = {
    send: mockWsSend,
    close: vi.fn(),
    onopen: null,
    onmessage: null,
    onclose: null,
    onerror: null,
    readyState: 1, // OPEN
  };

  // The constructor captures each created instance
  const MockWS = vi.fn(function MockWebSocket() {
    Object.assign(this, lastWsInstance);
    // Keep reference to the actual instance for onopen/onmessage
    lastWsInstance = this as unknown as MockWsInstance;
    return this;
  }) as unknown as typeof WebSocket;

  Object.defineProperty(MockWS, 'OPEN', { value: 1, configurable: true });
  vi.stubGlobal('WebSocket', MockWS);
});

afterEach(() => {
  vi.unstubAllGlobals();
  vi.clearAllMocks();
});

// --------------------------------------------------------------------------
// Helper
// --------------------------------------------------------------------------
const wrapper = ({ children }: { children: React.ReactNode }) => <>{children}</>;

async function renderAndConnect(opts: Parameters<typeof useCocinaWebSocket>[0] = {}) {
  const { result } = renderHook(() => useCocinaWebSocket(opts), { wrapper });

  // Wait for connect() to run (getToken resolves → new WebSocket created)
  await act(async () => {
    await new Promise((r) => setTimeout(r, 10));
  });

  // Trigger onopen on the ws instance the hook actually holds
  act(() => {
    lastWsInstance.onopen?.();
  });

  return { result, ws: lastWsInstance };
}

// --------------------------------------------------------------------------
// Tests
// --------------------------------------------------------------------------
describe('useCocinaWebSocket — cook trigger (Task 6.20)', () => {
  it('returns a reportIngredientUnavailable function', async () => {
    const { result } = await renderAndConnect();
    expect(typeof result.current.reportIngredientUnavailable).toBe('function');
  });

  it('sends kitchen.ingredient_unavailable WS message with correct payload', async () => {
    const { result, ws } = await renderAndConnect();

    // Ensure the ws instance has send mock attached
    act(() => {
      result.current.reportIngredientUnavailable(42, 10);
    });

    // Check send was called on the instance the hook holds
    expect(ws.send).toHaveBeenCalledOnce();
    const sent = JSON.parse((ws.send.mock.calls[0][0]) as string);
    expect(sent).toEqual({
      v: 1,
      type: 'kitchen.ingredient_unavailable',
      payload: { order_id: 42, ingredient_id: 10 },
    });
  });

  it('does not send when wsRef is null (disconnected)', async () => {
    // Don't trigger onopen — wsRef.current stays null (the ws closes before we call report)
    const { result } = renderHook(() => useCocinaWebSocket(), { wrapper });

    await act(async () => {
      await new Promise((r) => setTimeout(r, 10));
    });

    // Simulate immediate close before onopen
    act(() => {
      lastWsInstance.onclose?.();
    });

    // Clear any sends that might have happened during the close-reconnect cycle
    lastWsInstance.send.mockClear();

    // Now try to report — wsRef.current is null after close
    act(() => {
      result.current.reportIngredientUnavailable(1, 2);
    });

    expect(lastWsInstance.send).not.toHaveBeenCalled();
  });

  it('calls onAvailabilityRestored when ingredient_availability_restored arrives', async () => {
    const onAvailabilityRestored = vi.fn();
    const { ws } = await renderAndConnect({ onAvailabilityRestored });

    act(() => {
      lastWsInstance.onmessage?.({
        data: JSON.stringify({
          v: 1,
          type: 'ingredient_availability_restored',
          payload: { ingrediente_id: 10, ingrediente_nombre: 'Lechuga' },
        }),
      });
    });

    expect(onAvailabilityRestored).toHaveBeenCalledWith({
      ingrediente_id: 10,
      ingrediente_nombre: 'Lechuga',
    });

    void ws; // referenced above via lastWsInstance
  });

  it('invalidates the kitchen orders query on order_state_changed', async () => {
    await renderAndConnect();
    // Clear the invalidation that happens on ws.onopen (initial refresh).
    mockInvalidateQueries.mockClear();

    act(() => {
      lastWsInstance.onmessage?.({
        data: JSON.stringify({
          v: 1,
          type: 'order_state_changed',
          topic: 'kitchen:all',
          payload: { order_id: 42, estado: 'EN_PREPARACION' },
        }),
      });
    });

    expect(mockInvalidateQueries).toHaveBeenCalledWith({
      queryKey: ['cocina', 'pedidos'],
      refetchType: 'all',
    });
  });

  it('ignores unknown event types without crashing', async () => {
    await renderAndConnect();
    mockInvalidateQueries.mockClear();

    act(() => {
      lastWsInstance.onmessage?.({
        data: JSON.stringify({
          v: 1,
          type: 'something_we_dont_handle',
          payload: {},
        }),
      });
    });

    expect(mockInvalidateQueries).not.toHaveBeenCalled();
  });
});

// ---------------------------------------------------------------------------
// Task 4.1 — connection_resynced handler
// ---------------------------------------------------------------------------
describe('useCocinaWebSocket — connection_resynced (Task 4.1)', () => {
  it('calls invalidateQueries with ["cocina","pedidos"] when connection_resynced arrives', async () => {
    await renderAndConnect();
    // Clear the initial invalidation that fires on ws.onopen
    mockInvalidateQueries.mockClear();

    act(() => {
      lastWsInstance.onmessage?.({
        data: JSON.stringify({
          v: 1,
          type: 'connection_resynced',
          topic: 'kitchen:all',
          payload: { topic: 'kitchen:all', server_ts: '2026-05-28T00:00:00Z' },
        }),
      });
    });

    expect(mockInvalidateQueries).toHaveBeenCalledWith({
      queryKey: ['cocina', 'pedidos'],
      refetchType: 'all',
    });
  });
});
