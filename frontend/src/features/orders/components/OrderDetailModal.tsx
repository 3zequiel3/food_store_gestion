import { useEffect, useState } from 'react';
import { X, Package, Ban, AlertCircle } from 'lucide-react';
import { useOrderDetail } from '../hooks/useOrderDetail';
import { useAdvanceOrderState } from '../hooks/useAdvanceOrderState';
import { OrderTimeline } from './OrderTimeline';
import { OrderStatusBadge } from './OrderStatusBadge';
import { OrderStateActions } from './OrderStateActions';
import { useAuthStore } from '../../auth/stores/authStore';

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
  TARJETA: 'Tarjeta',
};

const CANCELLED_STATES = ['CANCELADO_ADMIN', 'CANCELADO_CLIENTE', 'CANCELADO'];

export function OrderDetailModal({ orderId, isAdmin = false, onClose }: OrderDetailModalProps) {
  const { data: order, isLoading, isError, refetch } = useOrderDetail(orderId);
  const advanceMutation = useAdvanceOrderState();
  const hasClientRole = useAuthStore((s) => s.user?.roles.includes('CLIENT') ?? false);

  const [showCancelModal, setShowCancelModal] = useState(false);
  const [cancelMotivo, setCancelMotivo] = useState('');

  useEffect(() => {
    function handleKeyDown(e: KeyboardEvent) {
      if (e.key === 'Escape') {
        if (showCancelModal) {
          setShowCancelModal(false);
          setCancelMotivo('');
        } else {
          onClose();
        }
      }
    }
    document.addEventListener('keydown', handleKeyDown);
    return () => document.removeEventListener('keydown', handleKeyDown);
  }, [onClose, showCancelModal]);

  if (orderId === null) return null;

  const isCancelled = order ? CANCELLED_STATES.includes(order.estado_codigo) : false;
  const canClientCancel =
    hasClientRole && !isAdmin && order?.estado_codigo === 'PENDIENTE' && !isCancelled;
  const isBlockedFromCancel =
    hasClientRole && !isAdmin && order && !CANCELLED_STATES.includes(order.estado_codigo) && order.estado_codigo !== 'PENDIENTE';

  function handleClientCancel() {
    if (!order) return;
    advanceMutation.mutate(
      { id: order.id, nuevo_estado: 'CANCELADO', motivo: cancelMotivo.trim() || undefined },
      {
        onSuccess: () => {
          setShowCancelModal(false);
          setCancelMotivo('');
          refetch();
        },
      },
    );
  }

  // Get cancel reason from last history entry
  const cancelReason = isCancelled
    ? order?.historial.findLast((h) => CANCELLED_STATES.includes(h.estado_nuevo_codigo))?.motivo
    : null;

  return (
    <div
      className="fixed inset-0 z-50 flex items-center justify-center bg-black/60 backdrop-blur-sm p-4"
      onClick={onClose}
    >
      <div
        className="relative w-full max-w-2xl max-h-[90vh] overflow-y-auto rounded-xl bg-white border border-gray-200 shadow-xl"
        onClick={(e) => e.stopPropagation()}
      >
        <div className="sticky top-0 z-10 flex items-center justify-between border-b border-gray-200 bg-white px-6 py-4">
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
            className="rounded-md p-1.5 text-muted-foreground hover:bg-gray-100 hover:text-foreground transition-colors"
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
              {/* Admin state actions */}
              {isAdmin && (
                <OrderStateActions order={order} />
              )}

              {/* Client cancel button */}
              {canClientCancel && (
                <div className="flex flex-col gap-2">
                  <button
                    type="button"
                    onClick={() => setShowCancelModal(true)}
                    className="flex items-center justify-center gap-2 w-full rounded-lg border border-destructive/50 px-4 py-2.5 text-sm font-semibold text-destructive hover:bg-destructive/10 transition-colors"
                  >
                    <Ban className="h-4 w-4" />
                    Cancelar pedido
                  </button>
                </div>
              )}

              {/* Blocked cancel tooltip */}
              {isBlockedFromCancel && (
                <div className="flex items-start gap-2 rounded-lg bg-muted/50 border border-border px-3 py-2.5">
                  <AlertCircle className="h-4 w-4 text-muted-foreground shrink-0 mt-0.5" />
                  <p className="text-xs text-muted-foreground">
                    Tu pedido ya está en preparación y no puede ser cancelado.
                    Contactanos si necesitás ayuda.
                  </p>
                </div>
              )}

              {/* Cancel reason display */}
              {isCancelled && cancelReason && (
                <div className="rounded-lg bg-destructive/10 border border-destructive/30 px-4 py-3">
                  <p className="text-sm font-medium text-destructive mb-1">Motivo de cancelación</p>
                  <p className="text-sm text-destructive/80">{cancelReason}</p>
                </div>
              )}
              {isCancelled && !cancelReason && (
                <div className="rounded-lg bg-destructive/10 border border-destructive/30 px-4 py-3">
                  <p className="text-sm text-destructive/80">Sin motivo especificado</p>
                </div>
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
                      className="flex items-center justify-between rounded-lg bg-gray-50 border border-gray-200 px-3 py-2 text-sm"
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
                        className="flex items-center justify-between rounded-lg bg-gray-50 border border-gray-200 px-3 py-2 text-sm"
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
                <OrderTimeline historial={order.historial} currentEstado={order.estado_codigo} />
              </section>
            </>
          )}
        </div>
      </div>

      {/* Cancel confirmation modal */}
      {showCancelModal && (
        <div
          className="fixed inset-0 z-[60] flex items-center justify-center bg-black/60 backdrop-blur-sm p-4"
          onClick={() => { setShowCancelModal(false); setCancelMotivo(''); }}
        >
          <div
            className="relative w-full max-w-md rounded-xl bg-white border border-gray-200 shadow-xl p-6"
            onClick={(e) => e.stopPropagation()}
          >
            <h3 className="text-lg font-semibold text-foreground mb-2">Cancelar pedido</h3>
            <p className="text-sm text-muted-foreground mb-4">
              ¿Estás seguro de que querés cancelar este pedido? Esta acción no se puede deshacer.
            </p>
            <label className="block text-sm font-medium text-foreground mb-1">
              Motivo (opcional)
            </label>
            <textarea
              value={cancelMotivo}
              onChange={(e) => setCancelMotivo(e.target.value)}
              placeholder="Contanos por qué querés cancelar…"
              rows={3}
              className="w-full rounded-lg border border-gray-300 px-3 py-2 text-sm text-foreground placeholder:text-muted-foreground focus:outline-none focus:ring-2 focus:ring-primary resize-none"
            />
            <div className="flex gap-3 mt-4">
              <button
                type="button"
                onClick={() => { setShowCancelModal(false); setCancelMotivo(''); }}
                disabled={advanceMutation.isPending}
                className="flex-1 rounded-lg border border-gray-300 px-4 py-2 text-sm font-medium text-foreground hover:bg-gray-50 disabled:opacity-50 transition-colors"
              >
                Volver
              </button>
              <button
                type="button"
                onClick={handleClientCancel}
                disabled={advanceMutation.isPending}
                className="flex-1 rounded-lg bg-destructive px-4 py-2 text-sm font-semibold text-white hover:bg-destructive/90 disabled:opacity-50 transition-colors"
              >
                {advanceMutation.isPending ? 'Procesando…' : 'Confirmar cancelación'}
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}

function ModalSkeleton() {
  return (
    <div className="flex flex-col gap-4">
      <div className="h-4 w-48 rounded-md bg-gradient-to-r from-muted/50 via-muted to-muted/50 animate-shimmer bg-[length:200%_100%]" />
      <div className="grid grid-cols-2 gap-3">
        {[...Array(4)].map((_, i) => (
          <div key={i} className="h-10 rounded-lg bg-gradient-to-r from-muted/50 via-muted to-muted/50 animate-shimmer bg-[length:200%_100%]" />
        ))}
      </div>
      <div className="h-4 w-32 rounded-md bg-gradient-to-r from-muted/50 via-muted to-muted/50 animate-shimmer bg-[length:200%_100%]" />
      {[...Array(3)].map((_, i) => (
        <div key={i} className="h-12 rounded-lg bg-gradient-to-r from-muted/50 via-muted to-muted/50 animate-shimmer bg-[length:200%_100%]" />
      ))}
    </div>
  );
}
