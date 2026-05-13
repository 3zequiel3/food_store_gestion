import { useEffect } from 'react';
import { X, Package } from 'lucide-react';
import { useOrderDetail } from '../hooks/useOrderDetail';
import { OrderTimeline } from './OrderTimeline';
import { OrderStatusBadge } from './OrderStatusBadge';
import { OrderStateActions } from './OrderStateActions';

interface OrderDetailModalProps {
  orderId: number | null;
  isAdmin?: boolean;
  onClose: () => void;
}

function formatCurrency(value: string): string {
  return `$${parseFloat(value).toLocaleString('es-AR', { minimumFractionDigits: 2 })}`;
}

function formatDate(iso: string): string {
  return new Date(iso).toLocaleString('es-AR', {
    day: '2-digit',
    month: '2-digit',
    year: 'numeric',
    hour: '2-digit',
    minute: '2-digit',
  });
}

const FORMA_PAGO_LABELS: Record<string, string> = {
  EFECTIVO: 'Efectivo',
  MERCADOPAGO: 'MercadoPago',
};

export function OrderDetailModal({ orderId, isAdmin = false, onClose }: OrderDetailModalProps) {
  const { data: order, isLoading, isError } = useOrderDetail(orderId);

  useEffect(() => {
    function handleKeyDown(e: KeyboardEvent) {
      if (e.key === 'Escape') onClose();
    }
    document.addEventListener('keydown', handleKeyDown);
    return () => document.removeEventListener('keydown', handleKeyDown);
  }, [onClose]);

  if (orderId === null) return null;

  return (
    <div
      className="fixed inset-0 z-50 flex items-center justify-center bg-black/60 p-4"
      onClick={onClose}
    >
      <div
        className="relative w-full max-w-2xl max-h-[90vh] overflow-y-auto rounded-xl bg-card border border-border shadow-xl"
        onClick={(e) => e.stopPropagation()}
      >
        <div className="sticky top-0 z-10 flex items-center justify-between border-b border-border bg-card px-6 py-4">
          <div className="flex items-center gap-3">
            <Package className="h-5 w-5 text-primary" />
            <h2 className="text-base font-semibold text-foreground">
              Pedido #{orderId}
            </h2>
            {order && <OrderStatusBadge estado={order.estado_codigo} />}
          </div>
          <button
            type="button"
            onClick={onClose}
            className="rounded-md p-1.5 text-muted-foreground hover:bg-accent hover:text-foreground transition-colors"
            aria-label="Cerrar"
          >
            <X className="h-4 w-4" />
          </button>
        </div>

        <div className="px-6 py-4 flex flex-col gap-6">
          {isLoading && <ModalSkeleton />}

          {isError && (
            <p className="text-sm text-muted-foreground text-center py-8">
              No se pudo cargar el detalle del pedido.
            </p>
          )}

          {order && (
            <>
              {isAdmin && (
                <OrderStateActions order={order} />
              )}

              <section className="flex flex-col gap-2">
                <h3 className="text-xs font-semibold uppercase tracking-wider text-muted-foreground">
                  Información general
                </h3>
                <dl className="grid grid-cols-2 gap-x-4 gap-y-2 text-sm">
                  <div>
                    <dt className="text-muted-foreground">Fecha</dt>
                    <dd className="text-foreground">{formatDate(order.creado_en)}</dd>
                  </div>
                  <div>
                    <dt className="text-muted-foreground">Forma de pago</dt>
                    <dd className="text-foreground">
                      {FORMA_PAGO_LABELS[order.forma_pago_codigo] ?? order.forma_pago_codigo}
                    </dd>
                  </div>
                  <div>
                    <dt className="text-muted-foreground">Total</dt>
                    <dd className="text-foreground font-semibold">{formatCurrency(order.total)}</dd>
                  </div>
                  <div>
                    <dt className="text-muted-foreground">Envío</dt>
                    <dd className="text-foreground">{formatCurrency(order.costo_envio)}</dd>
                  </div>
                  {order.direccion_snapshot && (
                    <div className="col-span-2">
                      <dt className="text-muted-foreground">Dirección de entrega</dt>
                      <dd className="text-foreground">{order.direccion_snapshot}</dd>
                    </div>
                  )}
                  {order.notas && (
                    <div className="col-span-2">
                      <dt className="text-muted-foreground">Notas</dt>
                      <dd className="text-foreground">{order.notas}</dd>
                    </div>
                  )}
                </dl>
              </section>

              <section className="flex flex-col gap-2">
                <h3 className="text-xs font-semibold uppercase tracking-wider text-muted-foreground">
                  Ítems ({order.items.length})
                </h3>
                <ul className="flex flex-col gap-2">
                  {order.items.map((item) => (
                    <li
                      key={item.id}
                      className="flex items-center justify-between rounded-lg bg-muted/50 px-3 py-2 text-sm"
                    >
                      <div className="flex flex-col">
                        <span className="font-medium text-foreground">{item.nombre_snapshot}</span>
                        <span className="text-xs text-muted-foreground">
                          {item.cantidad} × {formatCurrency(item.precio_snapshot)}
                        </span>
                      </div>
                      <span className="font-semibold text-foreground">
                        {formatCurrency(
                          String(item.cantidad * parseFloat(item.precio_snapshot)),
                        )}
                      </span>
                    </li>
                  ))}
                </ul>
              </section>

              {order.pagos.length > 0 && (
                <section className="flex flex-col gap-2">
                  <h3 className="text-xs font-semibold uppercase tracking-wider text-muted-foreground">
                    Pagos
                  </h3>
                  <ul className="flex flex-col gap-2">
                    {order.pagos.map((pago) => (
                      <li
                        key={pago.id}
                        className="flex items-center justify-between rounded-lg bg-muted/50 px-3 py-2 text-sm"
                      >
                        <div className="flex flex-col">
                          <span className="text-foreground capitalize">{pago.status}</span>
                          <span className="text-xs text-muted-foreground">
                            {formatDate(pago.fecha)}
                          </span>
                        </div>
                        <span className="font-semibold text-foreground">
                          {formatCurrency(pago.monto)}
                        </span>
                      </li>
                    ))}
                  </ul>
                </section>
              )}

              <section className="flex flex-col gap-2">
                <h3 className="text-xs font-semibold uppercase tracking-wider text-muted-foreground">
                  Historial de estados
                </h3>
                <OrderTimeline historial={order.historial} />
              </section>
            </>
          )}
        </div>
      </div>
    </div>
  );
}

function ModalSkeleton() {
  return (
    <div className="animate-pulse flex flex-col gap-4">
      <div className="h-4 w-48 rounded bg-muted" />
      <div className="grid grid-cols-2 gap-3">
        {[...Array(4)].map((_, i) => (
          <div key={i} className="h-10 rounded bg-muted" />
        ))}
      </div>
      <div className="h-4 w-32 rounded bg-muted" />
      {[...Array(3)].map((_, i) => (
        <div key={i} className="h-12 rounded bg-muted" />
      ))}
    </div>
  );
}
