/**
 * FaltantesBadge — Admin navbar inbox indicator.
 *
 * Connects to the orders:all WS topic (already subscribed by useOrderWebSocket
 * consumers) to listen for ingredient_unavailable_reported events.
 * Increments the Zustand badge counter on each such event.
 *
 * Renders a bell icon with a numeric badge when pendingCount > 0.
 * Clicking navigates to /admin/faltantes and resets the badge.
 *
 * Only mounts for ADMIN role (checked by the parent TopNavbar).
 */
import { useCallback } from 'react';
import { Link } from 'react-router-dom';
import { Bell } from 'lucide-react';
import { useOrderWebSocket, type WsFrame } from '../../orders/hooks/useOrderWebSocket';
import { useFaltantesStore } from '../stores/faltantesStore';

export function FaltantesBadge() {
  const increment = useFaltantesStore((s) => s.increment);
  const pendingCount = useFaltantesStore((s) => s.pendingCount);

  const handleEvent = useCallback(
    (frame: WsFrame) => {
      if (frame.type === 'ingredient_unavailable_reported') {
        increment();
      }
    },
    [increment],
  );

  // Subscribe to the admin orders:all topic
  useOrderWebSocket({
    topic: 'orders:all',
    onEvent: handleEvent,
  });

  return (
    <Link
      to="/admin/faltantes"
      className="relative flex h-10 w-10 items-center justify-center rounded-lg text-muted-foreground hover:bg-glass-hover hover:text-primary transition-all duration-150"
      aria-label={
        pendingCount > 0
          ? `Faltantes: ${pendingCount} reporte${pendingCount > 1 ? 's' : ''} pendiente${pendingCount > 1 ? 's' : ''}`
          : 'Faltantes de ingredientes'
      }
      title="Ingredientes faltantes"
    >
      <Bell className="h-5 w-5" />
      {pendingCount > 0 && (
        <span
          className="absolute -right-0.5 -top-0.5 flex h-4.5 w-4.5 items-center justify-center rounded-full bg-destructive text-[10px] font-bold text-destructive-foreground shadow-sm"
          aria-hidden="true"
        >
          {pendingCount > 9 ? '9+' : pendingCount}
        </span>
      )}
    </Link>
  );
}
