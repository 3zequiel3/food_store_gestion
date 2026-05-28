import { useCallback, useEffect, useState } from 'react';
import { AlertTriangle, CheckCircle2, Loader2 } from 'lucide-react';
import { useQueryClient } from '@tanstack/react-query';
import { useFaltantes, useResolverFaltante, FALTANTES_QUERY_KEY } from '../../features/availability/hooks/useFaltantes';
import { useFaltantesStore } from '../../features/availability/stores/faltantesStore';
import { useAuthStore } from '../../features/auth/stores/authStore';
import { useOrderWebSocket, type WsFrame } from '../../features/orders/hooks/useOrderWebSocket';

/**
 * Admin "Faltantes" view — lists open ingredient shortages and allows resolving them.
 *
 * P0.1 (admin): displays all rows where resuelto_en IS NULL.
 * Admin resolves with a single "Resolver" button + an adjacent audit label selector.
 * The accion field is informational/audit-only (backend accepts both values unchanged).
 * On open: resets the navbar badge counter.
 *
 * Decision 4 (design.md): replaced the two separate CTAs with one button + <select>.
 * Default selector value: "solucionado". Other option: "comprado".
 *
 * Route: /admin/faltantes (within the Comidas section of the sidebar).
 */
export function AdminFaltantesPage() {
  const queryClient = useQueryClient();
  const { mutate: resolver, isPending: isResolving } = useResolverFaltante();
  const resetBadge = useFaltantesStore((s) => s.reset);

  // WS event handler — must be declared before useOrderWebSocket below
  const handleWsEvent = useCallback(
    (frame: WsFrame) => {
      if (
        frame.type === 'ingredient_unavailable_reported' ||
        frame.type === 'ingredient_availability_restored' ||
        frame.type === 'connection_resynced'
      ) {
        void queryClient.invalidateQueries({ queryKey: FALTANTES_QUERY_KEY, refetchType: 'all' });
      }
    },
    [queryClient],
  );

  const { isDegraded } = useOrderWebSocket({
    topic: 'orders:all',
    onEvent: handleWsEvent,
  });

  const { data: faltantes = [], isLoading, isError, refetch } = useFaltantes(
    true,
    isDegraded ? 30_000 : false,
  );

  // Per-row selector state: maps ingrediente_id → selected accion label.
  // Default: "solucionado" (Decision 4 — design.md).
  const [accionMap, setAccionMap] = useState<Record<number, string>>({});

  const getAccion = (ingredienteId: number): string =>
    accionMap[ingredienteId] ?? 'solucionado';

  const setAccion = (ingredienteId: number, value: string) => {
    setAccionMap((prev) => ({ ...prev, [ingredienteId]: value }));
  };

  // Solo staff operativo (ADMIN / PEDIDOS / STOCK) resuelve faltantes.
  const canResolve = useAuthStore(
    (s) => s.hasRole('ADMIN') || s.hasRole('PEDIDOS') || s.hasRole('STOCK'),
  );

  // Reset badge when the view is opened
  useEffect(() => {
    resetBadge();
  }, [resetBadge]);

  return (
    <div className="min-h-screen bg-gray-50 p-4 md:p-6">
      <div className="max-w-4xl mx-auto">
        <div className="flex items-center justify-between mb-6">
          <div className="flex items-center gap-3">
            <div className="w-10 h-10 bg-red-100 rounded-xl flex items-center justify-center">
              <AlertTriangle className="w-5 h-5 text-red-600" />
            </div>
            <div>
              <h1 className="text-xl font-bold text-gray-800">Ingredientes faltantes</h1>
              <p className="text-sm text-gray-500">
                {faltantes.length === 0
                  ? 'Sin reportes pendientes'
                  : `${faltantes.length} reporte${faltantes.length > 1 ? 's' : ''} pendiente${faltantes.length > 1 ? 's' : ''}`}
              </p>
            </div>
          </div>
        </div>

        <div className="bg-white rounded-2xl border border-gray-200 shadow-sm overflow-hidden">
          {isLoading ? (
            <div className="flex items-center justify-center py-16">
              <Loader2 className="w-6 h-6 animate-spin text-red-500" />
            </div>
          ) : isError ? (
            <div className="py-12 text-center">
              <p className="text-sm text-red-500 mb-3">Error al cargar los faltantes</p>
              <button
                type="button"
                onClick={() => void refetch()}
                className="text-sm text-gray-500 underline"
              >
                Reintentar
              </button>
            </div>
          ) : faltantes.length === 0 ? (
            <div className="py-16 text-center">
              <CheckCircle2 className="w-12 h-12 text-green-400 mx-auto mb-3" />
              <p className="text-sm font-medium text-gray-600">Todo en orden</p>
              <p className="text-xs text-gray-400 mt-1">No hay ingredientes reportados como faltantes</p>
            </div>
          ) : (
            <table className="w-full">
              <thead className="bg-gray-50 border-b border-gray-100">
                <tr>
                  <th className="px-4 py-3 text-left text-xs font-semibold text-gray-500 uppercase tracking-wide">
                    Ingrediente
                  </th>
                  <th className="px-4 py-3 text-left text-xs font-semibold text-gray-500 uppercase tracking-wide">
                    Pedido
                  </th>
                  <th className="px-4 py-3 text-left text-xs font-semibold text-gray-500 uppercase tracking-wide">
                    Reportado
                  </th>
                  {canResolve && (
                    <th className="px-4 py-3 text-left text-xs font-semibold text-gray-500 uppercase tracking-wide">
                      Resolver
                    </th>
                  )}
                </tr>
              </thead>
              <tbody className="divide-y divide-gray-100">
                {faltantes.map((item) => (
                  <tr key={item.id} className="hover:bg-gray-50 transition-colors">
                    <td className="px-4 py-3">
                      <div className="flex items-center gap-2">
                        <div className="w-2 h-2 rounded-full bg-red-400 flex-shrink-0" />
                        <span className="text-sm font-medium text-gray-800">
                          {item.ingrediente_nombre ?? `Ingrediente #${item.ingrediente_id}`}
                        </span>
                      </div>
                    </td>
                    <td className="px-4 py-3">
                      <span className="text-sm text-gray-600">
                        Pedido #{item.pedido_id}
                      </span>
                    </td>
                    <td className="px-4 py-3">
                      <span className="text-xs text-gray-400">
                        {new Date(item.creado_en).toLocaleDateString('es-AR', {
                          day: '2-digit',
                          month: '2-digit',
                          hour: '2-digit',
                          minute: '2-digit',
                        })}
                      </span>
                    </td>
                    {canResolve && (
                      <td className="px-4 py-3">
                        {/*
                          Decision 4 (design.md): ONE "Resolver" button + adjacent
                          <select> for the audit label. Default: "solucionado".
                          The accion field is informational only — the backend endpoint
                          and schema are unchanged (AvailabilityResolveRequest.accion).
                        */}
                        <div className="flex items-center gap-2">
                          <select
                            value={getAccion(item.ingrediente_id)}
                            onChange={(e) => setAccion(item.ingrediente_id, e.target.value)}
                            disabled={isResolving}
                            className="text-xs border border-gray-200 rounded-lg px-2 py-1.5 bg-white text-gray-700 focus:outline-none focus:ring-2 focus:ring-green-300 disabled:opacity-50"
                            aria-label="Tipo de resolución"
                          >
                            <option value="solucionado">solucionado</option>
                            <option value="comprado">comprado</option>
                          </select>
                          <button
                            type="button"
                            disabled={isResolving}
                            onClick={() =>
                              resolver({
                                ingredienteId: item.ingrediente_id,
                                accion: getAccion(item.ingrediente_id),
                              })
                            }
                            className="flex items-center gap-1.5 px-3 py-1.5 bg-green-50 hover:bg-green-100 text-green-700 text-xs font-medium rounded-lg transition-colors disabled:opacity-50"
                          >
                            <CheckCircle2 className="w-3 h-3" />
                            Resolver
                          </button>
                        </div>
                      </td>
                    )}
                  </tr>
                ))}
              </tbody>
            </table>
          )}
        </div>
      </div>
    </div>
  );
}
