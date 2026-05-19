import { useEffect, useState } from 'react';
import { X, Package, Ban, AlertCircle, MapPin, CreditCard, Banknote, FileText, Clock } from 'lucide-react';
import { useOrderDetail } from '../hooks/useOrderDetail';
import { useAdvanceOrderState } from '../hooks/useAdvanceOrderState';
import { OrderTimeline, OrderProgressBar } from './OrderTimeline';
import { OrderStatusBadge } from './OrderStatusBadge';
import { OrderStateActions } from './OrderStateActions';
import { useAuthStore } from '../../auth/stores/authStore';

interface OrderDetailModalProps {
  orderId: number | null;
  isAdmin?: boolean;
  onClose: () => void;
}

function formatCurrency(value: string): string {
  return new Intl.NumberFormat('es-AR', {
    style: 'currency',
    currency: 'ARS',
    minimumFractionDigits: 2,
  }).format(parseFloat(value));
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

const PAGO_STATUS_LABELS: Record<string, string> = {
  approved: 'Aprobado',
  rejected: 'Rechazado',
  pending: 'Pendiente',
  in_process: 'En revisión',
  cancelled: 'Cancelado',
  refunded: 'Reembolsado',
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
    hasClientRole &&
    !isAdmin &&
    order &&
    !CANCELLED_STATES.includes(order.estado_codigo) &&
    order.estado_codigo !== 'PENDIENTE';

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

  const cancelReason = isCancelled
    ? order?.historial.findLast((h) => CANCELLED_STATES.includes(h.estado_nuevo_codigo))?.motivo
    : null;

  return (
    <div
      className="fixed inset-0 z-50 flex items-end sm:items-center justify-center bg-black/60 backdrop-blur-sm p-0 sm:p-4"
      onClick={onClose}
    >
      <div
        className="relative w-full max-w-4xl flex flex-col rounded-t-2xl sm:rounded-2xl bg-background/95 backdrop-blur-2xl border border-glass-border shadow-2xl shadow-black/20 overflow-hidden"
        style={{ maxHeight: 'min(88vh, 700px)' }}
        onClick={(e) => e.stopPropagation()}
      >
        {/* Top accent line */}
        <div className="absolute top-0 inset-x-0 h-px bg-gradient-to-r from-transparent via-primary/50 to-transparent pointer-events-none z-10" />

        {/* ── Header ── */}
        <div className="shrink-0 flex items-center gap-3 px-5 py-4 border-b border-glass-border">
          <div className="flex h-8 w-8 shrink-0 items-center justify-center rounded-lg bg-primary/10 border border-primary/20">
            <Package className="h-4 w-4 text-primary" />
          </div>

          <div className="flex items-center gap-2 flex-wrap flex-1 min-w-0">
            <h2 className="text-sm font-semibold text-foreground">Pedido #{orderId}</h2>
            {order && <OrderStatusBadge estado={order.estado_codigo} />}
          </div>

          <div className="flex items-center gap-4 shrink-0">
            {order && (
              <div className="hidden sm:flex items-center gap-1.5 text-xs text-muted-foreground">
                <Clock className="h-3.5 w-3.5" />
                {formatDate(order.creado_en)}
              </div>
            )}
            {order && (
              <div className="text-right">
                <p className="text-[10px] uppercase tracking-wider text-muted-foreground leading-none mb-0.5">Total</p>
                <p className="text-sm font-bold text-foreground tabular-nums">{formatCurrency(order.total)}</p>
              </div>
            )}
            <button
              type="button"
              onClick={onClose}
              className="rounded-lg p-1.5 text-muted-foreground hover:bg-glass-hover hover:text-foreground transition-colors"
              aria-label="Cerrar"
            >
              <X className="h-4 w-4" />
            </button>
          </div>
        </div>

        {/* ── Progress bar (full width, only for non-cancelled) ── */}
        {order && !isCancelled && (
          <div className="shrink-0 px-8 py-3 border-b border-glass-border bg-glass/20">
            <OrderProgressBar currentEstado={order.estado_codigo} />
          </div>
        )}

        {/* ── Two-column body ── */}
        <div className="flex-1 overflow-hidden grid grid-cols-1 md:grid-cols-[1fr_280px] min-h-0">

          {/* LEFT — order content */}
          <div className="overflow-y-auto p-5 flex flex-col gap-4 md:border-r md:border-glass-border">
            {isLoading && <LeftSkeleton />}
            {isError && (
              <p className="text-sm text-muted-foreground text-center py-10">
                No se pudo cargar el detalle del pedido.
              </p>
            )}

            {order && (
              <>
                {/* Info general */}
                <div className="rounded-xl bg-glass/40 border border-glass-border overflow-hidden">
                  <div className="px-4 py-2.5 border-b border-glass-border">
                    <h3 className="text-[10px] font-semibold uppercase tracking-wider text-muted-foreground">
                      Información general
                    </h3>
                  </div>
                  <div className="grid grid-cols-2 divide-x divide-y divide-glass-border">
                    <InfoCell
                      icon={
                        order.forma_pago_codigo === 'TARJETA' ? (
                          <CreditCard className="h-3.5 w-3.5" />
                        ) : (
                          <Banknote className="h-3.5 w-3.5" />
                        )
                      }
                      label="Forma de pago"
                      value={FORMA_PAGO_LABELS[order.forma_pago_codigo] ?? order.forma_pago_codigo}
                    />
                    <InfoCell
                      icon={<Package className="h-3.5 w-3.5" />}
                      label="Costo de envío"
                      value={formatCurrency(order.costo_envio)}
                    />
                    {order.direccion_snapshot && (
                      <div className="col-span-2">
                        <InfoCell
                          icon={<MapPin className="h-3.5 w-3.5" />}
                          label="Dirección de entrega"
                          value={order.direccion_snapshot}
                        />
                      </div>
                    )}
                    {order.notas && (
                      <div className="col-span-2">
                        <InfoCell
                          icon={<FileText className="h-3.5 w-3.5" />}
                          label="Notas"
                          value={order.notas}
                        />
                      </div>
                    )}
                  </div>
                </div>

                {/* Productos */}
                <div className="flex flex-col gap-2">
                  <h3 className="text-[10px] font-semibold uppercase tracking-wider text-muted-foreground px-1">
                    Productos ({order.items.length})
                  </h3>
                  <ul className="flex flex-col gap-1.5">
                    {order.items.map((item) => (
                      <li
                        key={item.id}
                        className="flex items-center justify-between rounded-xl bg-glass border border-glass-border px-4 py-3 gap-3"
                      >
                        <div className="flex flex-col min-w-0">
                          <span className="text-sm font-medium text-foreground truncate">
                            {item.nombre_snapshot}
                          </span>
                          <span className="text-xs text-muted-foreground mt-0.5">
                            {formatCurrency(item.precio_snapshot)} × {item.cantidad}
                          </span>
                        </div>
                        <span className="text-sm font-semibold text-foreground shrink-0 tabular-nums">
                          {formatCurrency(String(item.cantidad * parseFloat(item.precio_snapshot)))}
                        </span>
                      </li>
                    ))}
                  </ul>
                </div>

                {/* Pagos */}
                {order.pagos.length > 0 && (
                  <div className="flex flex-col gap-2">
                    <h3 className="text-[10px] font-semibold uppercase tracking-wider text-muted-foreground px-1">
                      Pagos
                    </h3>
                    <ul className="flex flex-col gap-1.5">
                      {order.pagos.map((pago) => (
                        <li
                          key={pago.id}
                          className="flex items-center justify-between rounded-xl bg-glass border border-glass-border px-4 py-3 gap-3"
                        >
                          <div className="flex flex-col">
                            <span className="text-sm font-medium text-foreground">
                              {PAGO_STATUS_LABELS[pago.status] ?? pago.status}
                            </span>
                            <span className="text-xs text-muted-foreground">
                              {formatDate(pago.fecha)}
                            </span>
                          </div>
                          <span className="text-sm font-semibold text-foreground tabular-nums">
                            {formatCurrency(pago.monto)}
                          </span>
                        </li>
                      ))}
                    </ul>
                  </div>
                )}
              </>
            )}
          </div>

          {/* RIGHT — state & timeline */}
          <div className="overflow-y-auto p-5 flex flex-col gap-4 bg-glass/10">
            {isLoading && <RightSkeleton />}

            {order && (
              <>
                {/* Admin state actions */}
                {isAdmin && <OrderStateActions order={order} />}

                {/* Client cancel button */}
                {canClientCancel && (
                  <button
                    type="button"
                    onClick={() => setShowCancelModal(true)}
                    className="flex items-center justify-center gap-2 w-full rounded-xl border border-destructive/30 bg-destructive/5 px-4 py-2.5 text-sm font-medium text-destructive hover:bg-destructive/10 transition-colors"
                  >
                    <Ban className="h-4 w-4" />
                    Cancelar pedido
                  </button>
                )}

                {/* Blocked cancel info */}
                {isBlockedFromCancel && (
                  <div className="flex items-start gap-2.5 rounded-xl bg-muted/20 border border-glass-border px-4 py-3">
                    <AlertCircle className="h-4 w-4 text-muted-foreground shrink-0 mt-0.5" />
                    <p className="text-xs text-muted-foreground leading-relaxed">
                      Tu pedido ya está en preparación y no puede ser cancelado.
                    </p>
                  </div>
                )}

                {/* Cancel reason */}
                {isCancelled && (
                  <div className="rounded-xl bg-destructive/10 border border-destructive/20 px-4 py-3.5">
                    <p className="text-[10px] font-semibold uppercase tracking-wider text-destructive/70 mb-1">
                      Motivo de cancelación
                    </p>
                    <p className="text-sm text-destructive">
                      {cancelReason ?? 'Sin motivo especificado'}
                    </p>
                  </div>
                )}

                {/* Timeline history */}
                <div className="flex flex-col gap-2">
                  <h3 className="text-[10px] font-semibold uppercase tracking-wider text-muted-foreground px-1">
                    Historial
                  </h3>
                  <OrderTimeline
                    historial={order.historial}
                    currentEstado={order.estado_codigo}
                    hideProgressBar
                  />
                </div>
              </>
            )}
          </div>
        </div>
      </div>

      {/* Cancel confirmation modal */}
      {showCancelModal && (
        <div
          className="fixed inset-0 z-[60] flex items-center justify-center bg-black/70 backdrop-blur-sm p-4"
          onClick={() => { setShowCancelModal(false); setCancelMotivo(''); }}
        >
          <div
            className="relative w-full max-w-md rounded-2xl bg-background/95 backdrop-blur-2xl border border-glass-border shadow-2xl p-6 overflow-hidden"
            onClick={(e) => e.stopPropagation()}
          >
            <div className="absolute top-0 inset-x-0 h-px bg-gradient-to-r from-transparent via-destructive/60 to-transparent pointer-events-none" />
            <div className="flex items-center gap-3 mb-5">
              <div className="flex h-9 w-9 items-center justify-center rounded-xl bg-destructive/10 border border-destructive/20 shrink-0">
                <Ban className="h-4 w-4 text-destructive" />
              </div>
              <div>
                <h3 className="text-base font-semibold text-foreground">Cancelar pedido</h3>
                <p className="text-xs text-muted-foreground">Esta acción no se puede deshacer</p>
              </div>
            </div>
            <label className="block text-sm font-medium text-foreground mb-1.5">
              Motivo{' '}
              <span className="font-normal text-muted-foreground">(opcional)</span>
            </label>
            <textarea
              value={cancelMotivo}
              onChange={(e) => setCancelMotivo(e.target.value)}
              placeholder="Contanos por qué querés cancelar…"
              rows={3}
              className="w-full rounded-xl border border-glass-border bg-background/50 px-3 py-2.5 text-sm text-foreground placeholder:text-muted-foreground/60 focus:outline-none focus:ring-2 focus:ring-destructive/40 resize-none transition-all"
            />
            <div className="flex gap-2.5 mt-4">
              <button
                type="button"
                onClick={() => { setShowCancelModal(false); setCancelMotivo(''); }}
                disabled={advanceMutation.isPending}
                className="flex-1 rounded-xl border border-glass-border px-4 py-2.5 text-sm font-medium text-foreground hover:bg-glass-hover disabled:opacity-50 transition-colors"
              >
                Volver
              </button>
              <button
                type="button"
                onClick={handleClientCancel}
                disabled={advanceMutation.isPending}
                className="flex-1 rounded-xl bg-destructive px-4 py-2.5 text-sm font-semibold text-white hover:bg-destructive/90 disabled:opacity-50 transition-colors"
              >
                {advanceMutation.isPending ? 'Cancelando…' : 'Confirmar cancelación'}
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}

function InfoCell({
  icon,
  label,
  value,
}: {
  icon: React.ReactNode;
  label: string;
  value: string;
}) {
  return (
    <div className="flex flex-col gap-0.5 px-4 py-3">
      <div className="flex items-center gap-1.5 text-muted-foreground mb-0.5">
        {icon}
        <span className="text-[10px] uppercase tracking-wider font-medium">{label}</span>
      </div>
      <span className="text-sm font-medium text-foreground">{value}</span>
    </div>
  );
}

function LeftSkeleton() {
  return (
    <div className="flex flex-col gap-4">
      <div className="h-24 rounded-xl bg-gradient-to-r from-muted/50 via-muted to-muted/50 animate-shimmer bg-[length:200%_100%]" />
      <div className="h-4 w-24 rounded-md bg-gradient-to-r from-muted/50 via-muted to-muted/50 animate-shimmer bg-[length:200%_100%]" />
      {[...Array(3)].map((_, i) => (
        <div key={i} className="h-14 rounded-xl bg-gradient-to-r from-muted/50 via-muted to-muted/50 animate-shimmer bg-[length:200%_100%]" />
      ))}
    </div>
  );
}

function RightSkeleton() {
  return (
    <div className="flex flex-col gap-3">
      <div className="h-20 rounded-xl bg-gradient-to-r from-muted/50 via-muted to-muted/50 animate-shimmer bg-[length:200%_100%]" />
      {[...Array(4)].map((_, i) => (
        <div key={i} className="h-10 rounded-lg bg-gradient-to-r from-muted/50 via-muted to-muted/50 animate-shimmer bg-[length:200%_100%]" />
      ))}
    </div>
  );
}
