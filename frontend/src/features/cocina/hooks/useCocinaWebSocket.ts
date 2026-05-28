import { useCallback, useEffect, useRef, useState } from "react";
import { useQueryClient } from "@tanstack/react-query";
import { useAuthStore } from "../../auth/stores/authStore";
import { getToken } from "../../auth/services/auth.service";
import { buildWebSocketUrl } from "../../../lib/ws";

const RECONNECT_DELAY_MS = 5_000; // 5s between reconnect attempts
const HEARTBEAT_TIMEOUT_MS = 45_000; // force reconnect if no message for 45s
const HEARTBEAT_CHECK_MS = 15_000; // check every 15s

/** Payload for the ingredient_availability_restored outbound event. */
export interface AvailabilityRestoredPayload {
  ingrediente_id: number;
  ingrediente_nombre?: string;
}

interface UseCocinaWebSocketOptions {
  /** Called when the backend emits ingredient_availability_restored to kitchen:all. */
  onAvailabilityRestored?: (payload: AvailabilityRestoredPayload) => void;
}

/**
 * Hook de WebSocket para el KDS de cocina.
 *
 * - Obtiene access token vía GET /auth/token (las cookies son HttpOnly)
 * - Conecta a WS /ws?token=<accessToken> (shared realtime module)
 * - On connect: invalida la query de pedidos para refrescar desde el REST endpoint
 * - On event: aplica cambios directamente al cache de TanStack Query
 * - On disconnect: programa reconexión automática cada 5s
 *
 * Expone:
 *   - isConnected: estado de la conexión
 *   - reportIngredientUnavailable(orderId, ingredientId): envía
 *     kitchen.ingredient_unavailable al backend (P0.1 cook trigger).
 *     Solo funciona cuando la conexión está abierta.
 */
export function useCocinaWebSocket(options: UseCocinaWebSocketOptions = {}) {
  const { onAvailabilityRestored } = options;

  const [isConnected, setIsConnected] = useState(false);
  const wsRef = useRef<WebSocket | null>(null);
  const reconnectTimerRef = useRef<ReturnType<typeof setTimeout> | null>(null);
  const queryClient = useQueryClient();
  const user = useAuthStore((s) => s.user);

  // Keep latest callback in a ref so the stable handleEvent closure can see it
  const onAvailabilityRestoredRef = useRef(onAvailabilityRestored);
  useEffect(() => {
    onAvailabilityRestoredRef.current = onAvailabilityRestored;
  }, [onAvailabilityRestored]);

  // Tracks the timestamp of the last received message (any frame).
  // Used by the heartbeat check interval to detect stale connections.
  const lastMessageAtRef = useRef<number>(Date.now());

  const invalidateAndRefresh = useCallback(() => {
    queryClient.invalidateQueries({ queryKey: ["cocina", "pedidos"], refetchType: "all" });
  }, [queryClient]);

  const handleEvent = useCallback(
    (event: { type: string; payload: unknown }) => {
      if (event.type === "ingredient_availability_restored") {
        onAvailabilityRestoredRef.current?.(
          event.payload as AvailabilityRestoredPayload,
        );
        // Refresh the board so any card blocked by this ingredient unblocks.
        // The Ingrediente.activo flag in the cocina payload drives the
        // "blocked" UI; we need to re-fetch to pick up the new value.
        invalidateAndRefresh();
        return;
      }

      if (event.type === "order_state_changed") {
        invalidateAndRefresh();
        return;
      }

      // Decision 2 (design.md): server emits connection_resynced after every
      // successful subscribe (auto or explicit). Trigger a deterministic refetch
      // to close any reconnect-race gap. The onopen → invalidateAndRefresh() above
      // stays as a belt-and-braces fallback for the very first connection.
      if (event.type === "connection_resynced") {
        invalidateAndRefresh();
        return;
      }
    },
    [invalidateAndRefresh],
  );

  const connect = useCallback(async () => {
    if (!user) return;

    try {
      const { access_token } = await getToken();

      const ws = new WebSocket(buildWebSocketUrl(access_token));
      wsRef.current = ws;

      ws.onopen = () => {
        lastMessageAtRef.current = Date.now();
        setIsConnected(true);
        invalidateAndRefresh();
      };

      ws.onmessage = (msg) => {
        lastMessageAtRef.current = Date.now();
        try {
          const data = JSON.parse(msg.data) as {
            type: string;
            payload: unknown;
          };
          // Heartbeat frames are protocol-level — no handler needed.
          if (data.type === "heartbeat") return;
          handleEvent(data);
        } catch {
          // Ignore malformed messages
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
      // Token fetch failed — retry connection after delay
      setIsConnected(false);
      reconnectTimerRef.current = setTimeout(
        () => void connect(),
        RECONNECT_DELAY_MS,
      );
    }
  }, [user, invalidateAndRefresh, handleEvent]);

  useEffect(() => {
    if (!user) return;

    void connect();

    // Periodically check if the connection has gone silent.
    // If no message was received within HEARTBEAT_TIMEOUT_MS, force close
    // so the onclose handler triggers a fresh reconnect.
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
  }, [user, connect]);

  /**
   * Send kitchen.ingredient_unavailable to the backend via the open WS connection.
   *
   * Returns true when the frame was actually sent, false when the connection
   * was not OPEN. Callers use the return value to drive UX feedback (toast).
   */
  const reportIngredientUnavailable = useCallback(
    (orderId: number, ingredientId: number): boolean => {
      const ws = wsRef.current;
      // Use numeric 1 (OPEN) directly — avoids issues in test envs where
      // the stubbed WebSocket constructor may not carry the static OPEN constant.
      if (!ws || ws.readyState !== 1) return false;

      const msg = JSON.stringify({
        v: 1,
        type: "kitchen.ingredient_unavailable",
        payload: { order_id: orderId, ingredient_id: ingredientId },
      });
      ws.send(msg);
      return true;
    },
    [],
  );

  return { isConnected, reportIngredientUnavailable };
}
