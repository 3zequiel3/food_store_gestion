import { PieChart, Pie, Cell, Tooltip, Legend, ResponsiveContainer } from 'recharts';
import type { MetricsDateFilter } from '../types/admin-metrics.types';
import { usePedidosPorEstado } from '../hooks/usePedidosPorEstado';

interface PedidosPorEstadoChartProps {
  filter: MetricsDateFilter;
}

const STATE_COLORS: Record<string, string> = {
  PENDIENTE: '#eab308',
  CONFIRMADO: '#3b82f6',
  EN_PREPARACION: '#f97316',
  EN_CAMINO: '#6366f1',
  ENTREGADO: '#22c55e',
  CANCELADO: '#ef4444',
};

const FALLBACK_COLORS = ['#8b5cf6', '#06b6d4', '#84cc16', '#f59e0b'];

export function PedidosPorEstadoChart({ filter }: PedidosPorEstadoChartProps) {
  const { data, isLoading } = usePedidosPorEstado(filter);

  const chartData = (data?.distribucion ?? [])
    .filter((d) => d.cantidad > 0)
    .map((d) => ({ name: d.estado_codigo, value: d.cantidad }));

  return (
    <div className="bg-card border border-border rounded-lg p-5">
      <h3 className="font-semibold text-foreground mb-4">Pedidos por estado</h3>

      {isLoading && <div className="h-64 bg-muted rounded animate-pulse" />}

      {!isLoading && chartData.length === 0 && (
        <div className="h-64 flex items-center justify-center text-sm text-muted-foreground">
          Sin pedidos en el periodo
        </div>
      )}

      {!isLoading && chartData.length > 0 && (
        <ResponsiveContainer width="100%" height={260}>
          <PieChart>
            <Pie
              data={chartData}
              dataKey="value"
              nameKey="name"
              cx="50%"
              cy="45%"
              outerRadius={90}
              label={({ name, percent }) => `${name} ${(percent * 100).toFixed(0)}%`}
              labelLine={false}
            >
              {chartData.map((entry, index) => (
                <Cell
                  key={entry.name}
                  fill={STATE_COLORS[entry.name] ?? FALLBACK_COLORS[index % FALLBACK_COLORS.length]}
                />
              ))}
            </Pie>
            <Tooltip formatter={(value: number) => [value, 'Pedidos']} />
            <Legend />
          </PieChart>
        </ResponsiveContainer>
      )}
    </div>
  );
}
