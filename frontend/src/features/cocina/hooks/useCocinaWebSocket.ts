import { useCallback, useEffect, useRef, useState } from 'react';
import { useQueryClient } from '@tanstack/react-query';
import { useAuthStore } from '../../auth/stores/authStore';
import { getToken } from '../../auth/services/auth.service';
import type { CocinaWebSocketEvent, CocinaPedidoResponse } from '../types/cocina.types';

const RECONNECT_DELAY_MS = 5_000; // 5s between reconnect attempts

/**
 * Hook de WebSocket para el KDS de cocina.
 *
 * - Obtiene access token vía GET /auth/token (las cookies son HttpOnly)
 * - Conecta a WS /api/v1/cocina/ws?token=<accessToken>
 * - On connect: invalida la query de pedidos para refrescar desde el REST endpoint
 * - On event: aplica cambios directamente al cache de TanStack Query
 * - On disconnect: programa reconexión automática cada 5s
 *
 * La resiliencia (polling de fallback + indicador de conexión) se maneja
 * en el componente padre que consume `isConnected`.
 */
export function useCocinaWebSocket() {
  const [isConnected, setIsConnected] = useState(false);
  const wsRef = useRef<WebSocket | null>(null);
  const reconnectTimerRef = useRef<ReturnType<typeof setTimeout> | null>(null);
  const queryClient = useQueryClient();
  const user = useAuthStore((s) => s.user);

  const invalidateAndRefresh = useCallback(() => {
    queryClient.invalidateQueries({ queryKey: ['cocina', 'pedidos'] });
  }, [queryClient]);

  const handleEvent = useCallback(
    (event: CocinaWebSocketEvent) => {
      queryClient.setQueryData<CocinaPedidoResponse[]>(
        ['cocina', 'pedidos'],
        (prev) => {
          if (!prev) return prev;
          const { type, payload } = event;

          switch (type) {
            case 'pedido_confirmado':
              return [payload, ...prev.filter((o) => o.id !== payload.id)];

            case 'pedido_en_preparacion':
              return prev.map((o) =>
                o.id === payload.id ? { ...o, estado: payload.estado } : o,
              );

            case 'pedido_terminado':
            case 'pedido_cancelado':
              return prev.filter((o) => o.id !== payload.id);

            default:
              return prev;
          }
        },
      );
    },
    [queryClient],
  );

  const connect = useCallback(async () => {
    if (!user) return;

    try {
      const { access_token } = await getToken();

      const protocol = window.location.protocol === 'https:' ? 'wss:' : 'ws:';
      const host = window.location.host;
      const wsUrl = `${protocol}//${host}/api/v1/cocina/ws?token=${encodeURIComponent(access_token)}`;

      const ws = new WebSocket(wsUrl);
      wsRef.current = ws;

      ws.onopen = () => {
        setIsConnected(true);
        invalidateAndRefresh();
      };

      ws.onmessage = (msg) => {
        try {
          const data = JSON.parse(msg.data) as CocinaWebSocketEvent;
          handleEvent(data);
        } catch {
          // Ignore malformed messages
        }
      };

      ws.onclose = () => {
        setIsConnected(false);
        wsRef.current = null;
        reconnectTimerRef.current = setTimeout(() => void connect(), RECONNECT_DELAY_MS);
      };

      ws.onerror = () => {
        setIsConnected(false);
      };
    } catch {
      // Token fetch failed — retry connection after delay
      setIsConnected(false);
      reconnectTimerRef.current = setTimeout(() => void connect(), RECONNECT_DELAY_MS);
    }
  }, [user, invalidateAndRefresh, handleEvent]);

  useEffect(() => {
    if (!user) return;

    void connect();

    return () => {
      if (reconnectTimerRef.current) {
        clearTimeout(reconnectTimerRef.current);
        reconnectTimerRef.current = null;
      }
      if (wsRef.current) {
        wsRef.current.close();
        wsRef.current = null;
      }
    };
  }, [user, connect]);

  return { isConnected };
}
