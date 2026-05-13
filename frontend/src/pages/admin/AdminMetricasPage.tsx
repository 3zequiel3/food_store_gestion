import { useSearchParams } from 'react-router-dom';
import { BarChart2 } from 'lucide-react';
import { useResumen } from '../../features/admin-metrics/hooks/useResumen';
import { KPICard } from '../../features/admin-metrics/components/KPICard';
import { DateRangeFilter } from '../../features/admin-metrics/components/DateRangeFilter';
import { VentasChart } from '../../features/admin-metrics/components/VentasChart';
import { TopProductosChart } from '../../features/admin-metrics/components/TopProductosChart';
import { PedidosPorEstadoChart } from '../../features/admin-metrics/components/PedidosPorEstadoChart';

function formatCurrency(value: string) {
  return `$${parseFloat(value).toLocaleString('es-AR', { minimumFractionDigits: 2, maximumFractionDigits: 2 })}`;
}

export function AdminMetricasPage() {
  const [searchParams] = useSearchParams();
  const filter = {
    desde: searchParams.get('desde') ?? undefined,
    hasta: searchParams.get('hasta') ?? undefined,
  };

  const { data: resumen, isLoading: resumenLoading } = useResumen(filter);

  return (
    <div className="p-6 max-w-7xl mx-auto">
      <div className="flex items-center gap-3 mb-6">
        <BarChart2 className="h-6 w-6 text-muted-foreground" />
        <h1 className="text-2xl font-bold text-foreground">Métricas</h1>
      </div>

      <DateRangeFilter />

      {/* KPI Cards */}
      <div className="grid grid-cols-2 lg:grid-cols-4 gap-4 mb-6">
        <KPICard
          label="Total ventas"
          value={resumen ? formatCurrency(resumen.total_ventas) : '—'}
          isLoading={resumenLoading}
        />
        <KPICard
          label="Total pedidos"
          value={resumen?.total_pedidos ?? '—'}
          isLoading={resumenLoading}
        />
        <KPICard
          label="Ticket promedio"
          value={resumen ? formatCurrency(resumen.ticket_promedio) : '—'}
          isLoading={resumenLoading}
        />
        <KPICard
          label="Usuarios activos"
          value={resumen?.total_usuarios ?? '—'}
          isLoading={resumenLoading}
        />
      </div>

      {/* Charts */}
      <div className="space-y-6">
        <VentasChart filter={filter} />
        <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
          <TopProductosChart filter={filter} />
          <PedidosPorEstadoChart filter={filter} />
        </div>
      </div>
    </div>
  );
}
