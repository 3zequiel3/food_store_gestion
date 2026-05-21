import { WifiOff } from 'lucide-react';

interface ConnectionStatusProps {
  isConnected: boolean;
}

/**
 * Indicador de conexión WebSocket.
 *
 * Se muestra solo cuando está desconectado.
 * Muestra "Sin conexión en vivo — actualizando cada 30s" con un dot amarillo.
 */
export function ConnectionStatus({ isConnected }: ConnectionStatusProps) {
  if (isConnected) return null;

  return (
    <div className="flex items-center gap-2 px-3 py-2 rounded-lg bg-warning/10 border border-warning/30 text-warning text-sm">
      <WifiOff className="h-4 w-4" />
      <span>Sin conexión en vivo — actualizando cada 30s</span>
      <span className="relative flex h-2.5 w-2.5">
        <span className="absolute inline-flex h-full w-full rounded-full bg-warning opacity-75 animate-ping" />
        <span className="relative inline-flex h-2.5 w-2.5 rounded-full bg-warning" />
      </span>
    </div>
  );
}
