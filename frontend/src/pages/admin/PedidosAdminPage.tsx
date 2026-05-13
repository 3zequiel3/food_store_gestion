import { useState } from 'react';
import { useSearchParams } from 'react-router-dom';
import { ClipboardList } from 'lucide-react';
import { useOrders } from '../../features/orders/hooks/useOrders';
import { OrderRow } from '../../features/orders/components/OrderRow';
import { OrderFilters } from '../../features/orders/components/OrderFilters';
import { OrderDetailModal } from '../../features/orders/components/OrderDetailModal';
import { Pagination } from '../../features/products/components/Pagination';
import type { EstadoCodigo, OrderFilters as OrderFiltersType } from '../../features/orders/types/orders.types';

const LIMIT = 20;

function parseFilters(params: URLSearchParams): OrderFiltersType {
  const filters: OrderFiltersType = {
    page: Number(params.get('page') ?? '1'),
    limit: LIMIT,
  };

  const estado = params.get('estado');
  if (estado) filters.estado = estado as EstadoCodigo;

  const desde = params.get('desde');
  if (desde) filters.desde = desde;

  const hasta = params.get('hasta');
  if (hasta) filters.hasta = hasta;

  const q = params.get('q');
  if (q) filters.q = q;

  return filters;
}

export function PedidosAdminPage() {
  const [searchParams] = useSearchParams();
  const filters = parseFilters(searchParams);

  const { data, isLoading, isError, refetch } = useOrders(filters);

  const [selectedOrderId, setSelectedOrderId] = useState<number | null>(null);

  return (
    <div className="mx-auto max-w-6xl px-4 py-8 flex flex-col gap-6">
      <div className="flex items-center gap-3">
        <div className="flex h-10 w-10 items-center justify-center rounded-full bg-primary/10">
          <ClipboardList className="h-5 w-5 text-primary" />
        </div>
        <div>
          <h1 className="text-lg font-semibold text-foreground">Pedidos</h1>
          <p className="text-sm text-muted-foreground">Gestión y transición de estados</p>
        </div>
      </div>

      <OrderFilters />

      {isError && (
        <div className="flex flex-col items-center gap-3 py-12 text-center">
          <p className="text-sm text-muted-foreground">No se pudieron cargar los pedidos.</p>
          <button
            type="button"
            onClick={() => refetch()}
            className="rounded-lg border border-border px-4 py-2 text-sm font-medium text-foreground hover:bg-accent transition-colors"
          >
            Reintentar
          </button>
        </div>
      )}

      {isLoading && <TableSkeleton />}

      {!isLoading && !isError && (
        <>
          {!data || data.items.length === 0 ? (
            <div className="flex flex-col items-center gap-3 py-16 text-center">
              <div className="flex h-14 w-14 items-center justify-center rounded-full bg-muted">
                <ClipboardList className="h-7 w-7 text-muted-foreground/40" />
              </div>
              <p className="text-sm text-muted-foreground">No hay pedidos que coincidan con los filtros.</p>
            </div>
          ) : (
            <div className="rounded-xl border border-border overflow-hidden">
              <div className="overflow-x-auto">
                <table className="w-full text-left">
                  <thead className="bg-muted/50 text-xs font-semibold uppercase tracking-wider text-muted-foreground">
                    <tr>
                      <th className="px-4 py-3">#</th>
                      <th className="px-4 py-3">Estado</th>
                      <th className="px-4 py-3">Total</th>
                      <th className="px-4 py-3">Fecha</th>
                      <th className="px-4 py-3 text-right">Ítems</th>
                      <th className="px-4 py-3 text-right">Acciones</th>
                    </tr>
                  </thead>
                  <tbody>
                    {data.items.map((order) => (
                      <OrderRow
                        key={order.id}
                        order={order}
                        onViewDetail={setSelectedOrderId}
                      />
                    ))}
                  </tbody>
                </table>
              </div>
            </div>
          )}

          {data && (
            <Pagination
              total={data.total}
              currentPage={data.page}
              limit={data.limit}
            />
          )}
        </>
      )}

      <OrderDetailModal
        orderId={selectedOrderId}
        isAdmin={true}
        onClose={() => setSelectedOrderId(null)}
      />
    </div>
  );
}

function TableSkeleton() {
  return (
    <div className="animate-pulse rounded-xl border border-border overflow-hidden">
      <div className="h-10 bg-muted/50" />
      {[...Array(6)].map((_, i) => (
        <div key={i} className="flex gap-4 border-t border-border px-4 py-3">
          <div className="h-4 w-10 rounded bg-muted" />
          <div className="h-5 w-24 rounded-full bg-muted" />
          <div className="h-4 w-20 rounded bg-muted" />
          <div className="h-4 w-28 rounded bg-muted" />
          <div className="ml-auto h-4 w-16 rounded bg-muted" />
        </div>
      ))}
    </div>
  );
}
