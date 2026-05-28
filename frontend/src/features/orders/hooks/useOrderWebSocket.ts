/**
 * useOrderWebSocket — Task 4.2 (P1.5 shared transport)
 *
 * Shared frontend WebSocket client/hook for realtime order updates.
 *
 * Design:
 * - Connects to the shared `/ws?token=<JWT>` endpoint (the new module, NOT the
 *   deprecated /api/v1/cocina/ws that the old KDS hook used).
 * - After handshake, sends `{v:1,type:"subscribe",topic}` to join the topic.
 * - Calls `onEvent` only for frames whose `topic` field matches the subscribed
 *   topic — isolating CLIENT consumers to their own `order:{id}`.
 * - Auto-reconnects with 5s delay on close.
 * - Exposes `isDegraded` (true when not connected) so callers can enable
 *   polling fallback at the 30s interval standard for this project.
 * - Token is fetched via GET /auth/token (HttpOnly-cookie session, same pattern
 *   as `useCocinaWebSocket`).
 */

import { useCallback, useEffect, useRef, useState } from 'react';
import { getToken } from '../../auth/services/auth.service';
import { useAuthStore } from '../../auth/stores/authStore';
import { buildWebSocketUrl } from '../../../lib/ws';

// ---------------------------------------------------------------------------
// Types — mirrors the backend versioned wire format (contracts.py DomainEvent)
// ---------------------------------------------------------------------------

export interface WsFrame {
  v: number;
  type: string;
  topic: string;
  payload: Record<string, unknown>;
  ts: string;
}

export interface UseOrderWebSocketOptions {
  /**
   * Topic to subscribe to after the handshake.
   * - CLIENT consumers: "order:{id}" (their own order)
   * - ADMIN/PEDIDOS consumers: "orders:all"
   */
  topic: string;

  /**
   * Called for every frame received on the subscribed topic.
   * Frames on other topics are silently ignored.
   */
  onEvent: (frame: WsFrame) => void;

  /** Disable the hook (skips connection). Useful for conditional rendering. */
  enabled?: boolean;
}

export interface UseOrderWebSocketReturn {
  /** True once the WebSocket handshake + subscribe ack is complete. */
  isConnected: boolean;
  /**
   * True when not connected — callers should enable their polling fallback.
   * Polling interval: 30s (project-wide standard).
   */
  isDegraded: boolean;
}

const RECONNECT_DELAY_MS = 5_000;
const HEARTBEAT_TIMEOUT_MS = 45_000;
const HEARTBEAT_CHECK_MS = 15_000;

// ---------------------------------------------------------------------------
// Hook
// ---------------------------------------------------------------------------

export function useOrderWebSocket({
  topic,
  onEvent,
  enabled = true,
}: UseOrderWebSocketOptions): UseOrderWebSocketReturn {
  const [isConnected, setIsConnected] = useState(false);
  const wsRef = useRef<WebSocket | null>(null);
  const reconnectTimerRef = useRef<ReturnType<typeof setTimeout> | null>(null);
  const user = useAuthStore((s) => s.user);

  // Stable ref to onEvent so the connect closure doesn't go stale.
  const onEventRef = useRef(onEvent);
  onEventRef.current = onEvent;

  const topicRef = useRef(topic);
  topicRef.current = topic;

  const lastMessageAtRef = useRef<number>(Date.now());

  const connect = useCallback(async () => {
    if (!user || !enabled) return;

    // Clear any pending reconnect so we don't double-connect.
    if (reconnectTimerRef.current) {
      clearTimeout(reconnectTimerRef.current);
      reconnectTimerRef.current = null;
    }

    try {
      const { access_token } = await getToken();

      const ws = new WebSocket(buildWebSocketUrl(access_token));
      wsRef.current = ws;

      ws.onopen = () => {
        lastMessageAtRef.current = Date.now();
        setIsConnected(true);
        // Subscribe to the requested topic.
        ws.send(
          JSON.stringify({ v: 1, type: 'subscribe', topic: topicRef.current }),
        );
      };

      ws.onmessage = (msg) => {
        lastMessageAtRef.current = Date.now();
        try {
          const frame = JSON.parse(msg.data) as WsFrame;
          // Heartbeat frames are protocol-level — no handler needed.
          if (frame.type === 'heartbeat') return;
          // Only forward events that belong to our subscribed topic.
          if (frame.topic === topicRef.current) {
            onEventRef.current(frame);
          }
        } catch {
          // Ignore malformed frames.
        }
      };

      ws.onclose = () => {
        setIsConnected(false);
        wsRef.current = null;
        reconnectTimerRef.current = setTimeout(
          () => void connect(),
          RECONNECT_DELAY_MS,
        );
      };

      ws.onerror = () => {
        setIsConnected(false);
      };
    } catch {
      // Token fetch failed — retry after delay.
      setIsConnected(false);
      reconnectTimerRef.current = setTimeout(
        () => void connect(),
        RECONNECT_DELAY_MS,
      );
    }
  }, [user, enabled]);

  useEffect(() => {
    if (!user || !enabled) return;

    void connect();

    // Periodically check if the connection has gone silent.
    const heartbeatCheck = setInterval(() => {
      const ws = wsRef.current;
      if (!ws || ws.readyState !== 1) return;
      const elapsed = Date.now() - lastMessageAtRef.current;
      if (elapsed > HEARTBEAT_TIMEOUT_MS) {
        ws.close();
      }
    }, HEARTBEAT_CHECK_MS);

    return () => {
      clearInterval(heartbeatCheck);
      if (reconnectTimerRef.current) {
        clearTimeout(reconnectTimerRef.current);
        reconnectTimerRef.current = null;
      }
      if (wsRef.current) {
        wsRef.current.close();
        wsRef.current = null;
      }
    };
  }, [user, enabled, connect]);

  return {
    isConnected,
    isDegraded: !isConnected,
  };
}
