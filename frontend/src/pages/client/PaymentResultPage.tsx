import { useNavigate, useSearchParams } from 'react-router-dom';
import { CheckCircle, Clock, XCircle, HelpCircle, Package, RotateCcw } from 'lucide-react';

type CollectionStatus = 'approved' | 'pending' | 'in_process' | 'rejected' | 'cancelled' | string;

interface ResultConfig {
  icon: React.ReactNode;
  title: string;
  description: string;
  primaryLabel: string;
  primaryPath: string;
  secondaryLabel?: string;
  secondaryPath?: string;
}

function getResultConfig(status: CollectionStatus | null): ResultConfig {
  switch (status) {
    case 'approved':
      return {
        icon: <CheckCircle className="h-16 w-16 text-green-500 mx-auto" />,
        title: '¡Pago aprobado!',
        description: 'Tu pago fue procesado correctamente. El local ya recibió tu pedido.',
        primaryLabel: 'Ver mis pedidos',
        primaryPath: '/cliente/pedidos',
      };
    case 'pending':
    case 'in_process':
      return {
        icon: <Clock className="h-16 w-16 text-yellow-500 mx-auto" />,
        title: 'Pago en proceso',
        description: 'Tu pago está siendo procesado. Te notificaremos cuando se confirme.',
        primaryLabel: 'Ver mis pedidos',
        primaryPath: '/cliente/pedidos',
      };
    case 'rejected':
    case 'cancelled':
      return {
        icon: <XCircle className="h-16 w-16 text-destructive mx-auto" />,
        title: 'Pago rechazado',
        description: 'El pago no pudo procesarse. Podés intentarlo de nuevo desde tu pedido.',
        primaryLabel: 'Ver mis pedidos',
        primaryPath: '/cliente/pedidos',
        secondaryLabel: 'Ir al catálogo',
        secondaryPath: '/cliente/catalogo',
      };
    default:
      return {
        icon: <HelpCircle className="h-16 w-16 text-muted-foreground mx-auto" />,
        title: 'Resultado desconocido',
        description: 'No pudimos determinar el estado del pago. Revisá tus pedidos para ver el estado actualizado.',
        primaryLabel: 'Ver mis pedidos',
        primaryPath: '/cliente/pedidos',
      };
  }
}

export function PaymentResultPage() {
  const [searchParams] = useSearchParams();
  const navigate = useNavigate();
  const collectionStatus = searchParams.get('collection_status');

  const config = getResultConfig(collectionStatus);

  return (
    <div className="max-w-md mx-auto py-16 px-4 text-center space-y-6">
      {config.icon}

      <div>
        <h1 className="text-2xl font-bold text-foreground mb-2">{config.title}</h1>
        <p className="text-muted-foreground text-sm">{config.description}</p>
      </div>

      <div className="flex flex-col sm:flex-row gap-3 justify-center">
        <button
          onClick={() => navigate(config.primaryPath)}
          className="inline-flex items-center justify-center gap-2 px-4 py-2 bg-primary text-primary-foreground rounded-lg hover:bg-primary/90 transition-colors font-semibold"
        >
          <Package className="h-4 w-4" />
          {config.primaryLabel}
        </button>

        {config.secondaryLabel && config.secondaryPath && (
          <button
            onClick={() => navigate(config.secondaryPath!)}
            className="inline-flex items-center justify-center gap-2 px-4 py-2 border border-border bg-card text-foreground rounded-lg hover:bg-accent transition-colors"
          >
            <RotateCcw className="h-4 w-4" />
            {config.secondaryLabel}
          </button>
        )}
      </div>
    </div>
  );
}
