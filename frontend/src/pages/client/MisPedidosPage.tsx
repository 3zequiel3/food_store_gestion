import { useCallback, useState } from 'react';
import { useSearchParams } from 'react-router-dom';
import { ShoppingBag } from 'lucide-react';
import { useQueryClient } from '@tanstack/react-query';
import { useOrders } from '../../features/orders/hooks/useOrders';
import { useOrderWebSocket, type WsFrame } from '../../features/orders/hooks/useOrderWebSocket';
import { OrderCard } from '../../features/orders/components/OrderCard';
import { OrderCardSkeleton } from '../../features/orders/components/OrderCardSkeleton';
import { OrderDetailModal } from '../../features/orders/components/OrderDetailModal';
import { Pagination } from '../../features/products/components/Pagination';
import type { OrderFilters } from '../../features/orders/types/orders.types';

const LIMIT = 10;

function parseFilters(params: URLSearchParams): OrderFilters {
  return {
    page: Number(params.get('page') ?? '1'),
    limit: LIMIT,
  };
}

export function MisPedidosPage() {
  const queryClient = useQueryClient();
  const [searchParams] = useSearchParams();
  const filters = parseFilters(searchParams);

  const handleWsEvent = useCallback(
    (frame: WsFrame) => {
      if (frame.type === 'order_state_changed' || frame.type === 'connection_resynced') {
        void queryClient.invalidateQueries({ queryKey: ['orders'], refetchType: 'all' });
      }
    },
    [queryClient],
  );

  const { isDegraded } = useOrderWebSocket({
    topic: 'orders:all',
    onEvent: handleWsEvent,
  });

  const { data, isLoading, isError, refetch } = useOrders(filters, isDegraded ? 30_000 : false);

  const [selectedOrderId, setSelectedOrderId] = useState<number | null>(null);

  if (isLoading) {
    return (
      <div className="mx-auto max-w-lg px-4 py-8 flex flex-col gap-6">
        <PageHeader />
        <div className="flex flex-col gap-3">
          {[...Array(4)].map((_, i) => <OrderCardSkeleton key={i} />)}
        </div>
      </div>
    );
  }

  if (isError) {
    return (
      <div className="flex flex-col items-center justify-center gap-4 py-24 text-center">
        <p className="text-sm text-muted-foreground">No se pudieron cargar tus pedidos.</p>
        <button
          type="button"
          onClick={() => refetch()}
          className="rounded-lg border border-border px-4 py-2 text-sm font-medium text-foreground hover:bg-accent transition-colors"
        >
          Reintentar
        </button>
      </div>
    );
  }

  const orders = data?.items ?? [];

  return (
    <div className="mx-auto max-w-lg px-4 py-8 flex flex-col gap-6">
      <PageHeader />

      {orders.length === 0 ? (
        <div className="flex flex-col items-center gap-4 py-16 text-center">
          <div className="flex h-16 w-16 items-center justify-center rounded-full bg-muted">
            <ShoppingBag className="h-8 w-8 text-muted-foreground/40" />
          </div>
          <div>
            <p className="text-sm font-medium text-foreground">No tenés pedidos todavía</p>
            <p className="text-sm text-muted-foreground">
              Tus pedidos aparecerán acá una vez que realices tu primera compra.
            </p>
          </div>
        </div>
      ) : (
        <>
          <ul className="flex flex-col gap-3">
            {orders.map((order) => (
              <li key={order.id}>
                <OrderCard order={order} onClick={setSelectedOrderId} />
              </li>
            ))}
          </ul>

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
        isAdmin={false}
        onClose={() => setSelectedOrderId(null)}
      />
    </div>
  );
}

function PageHeader() {
  return (
    <div className="flex items-center gap-3">
      <div className="flex h-10 w-10 items-center justify-center rounded-full bg-primary/10">
        <ShoppingBag className="h-5 w-5 text-primary" />
      </div>
      <div>
        <h1 className="text-lg font-semibold text-foreground">Mis pedidos</h1>
        <p className="text-sm text-muted-foreground">Historial y seguimiento de tus compras</p>
      </div>
    </div>
  );
}
