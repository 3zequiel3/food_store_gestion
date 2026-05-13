import {
  BarChart, Bar, XAxis, YAxis, CartesianGrid, Tooltip, ResponsiveContainer,
} from 'recharts';
import type { MetricsDateFilter } from '../types/admin-metrics.types';
import { useTopProductos } from '../hooks/useTopProductos';

interface TopProductosChartProps {
  filter: MetricsDateFilter;
}

export function TopProductosChart({ filter }: TopProductosChartProps) {
  const { data, isLoading } = useTopProductos(filter, 10);

  const chartData = data?.productos.map((p) => ({
    nombre: p.nombre.length > 20 ? p.nombre.slice(0, 20) + '…' : p.nombre,
    cantidad: p.cantidad_total,
  })) ?? [];

  return (
    <div className="bg-card border border-border rounded-lg p-5">
      <h3 className="font-semibold text-foreground mb-4">Top 10 productos</h3>

      {isLoading && <div className="h-64 bg-muted rounded animate-pulse" />}

      {!isLoading && chartData.length === 0 && (
        <div className="h-64 flex items-center justify-center text-sm text-muted-foreground">
          Sin ventas en el periodo
        </div>
      )}

      {!isLoading && chartData.length > 0 && (
        <ResponsiveContainer width="100%" height={260}>
          <BarChart
            layout="vertical"
            data={chartData}
            margin={{ top: 4, right: 16, left: 8, bottom: 4 }}
          >
            <CartesianGrid strokeDasharray="3 3" className="stroke-border" />
            <XAxis type="number" tick={{ fontSize: 11 }} />
            <YAxis type="category" dataKey="nombre" width={120} tick={{ fontSize: 11 }} />
            <Tooltip formatter={(value: number) => [value, 'Unidades']} />
            <Bar dataKey="cantidad" fill="hsl(var(--primary))" radius={[0, 4, 4, 0]} />
          </BarChart>
        </ResponsiveContainer>
      )}
    </div>
  );
}
